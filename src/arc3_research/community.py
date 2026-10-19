"""Normal offline ARC API adapter with no registry hints in solver observations.

Game implementations are imported by the SDK only. This module does not inspect
source, level data, private sprites, solutions, or metadata descriptions.
Keeping this API narrow is not an OS sandbox: solver processes must separately
be denied access to the collector's source and registry directories.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time


@dataclass(frozen=True)
class PublicObservation:
    frames: list
    available_actions: list[int]
    state: str
    levels_completed: int

    def to_solver(self):
        """Only observed pixels and the public interaction protocol."""
        return asdict(self)


def load_allowlist(path=None):
    """Frozen 12/12/16 split. Development is the only set a model run may touch."""
    path = Path(path) if path else Path(__file__).resolve().parents[2] / "experiments/020-community/solver-allowlists.json"
    data = json.loads(path.read_text())
    for key in ("development", "reserve", "frozen"):
        if not isinstance(data.get(key), list) or len(data[key]) not in (12, 16):
            raise ValueError("Community allowlist is missing a split")
    if set(data["development"]) & set(data["frozen"]) or set(data["development"]) & set(data["reserve"]):
        raise ValueError("Community allowlist splits overlap")
    return data


def development_ids(path=None):
    return list(load_allowlist(path)["development"])


def public_observation(raw):
    if raw is None:
        raise RuntimeError("Normal API returned no observation")
    frames = [frame.tolist() if hasattr(frame, "tolist") else frame for frame in raw.frame]
    if not frames:
        raise ValueError("Empty frame list")
    for frame in frames:
        if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
            raise ValueError("Nonrectangular/empty public frame")
        if any(type(v) is not int or not 0 <= v <= 15 for row in frame for v in row):
            raise ValueError("Public frame is not the expected integer palette 0..15")
    actions = sorted({int(getattr(a, "value", a)) for a in raw.available_actions})
    if any(a not in range(1, 8) for a in actions):
        raise ValueError("Unexpected public action ID")
    state = str(getattr(raw.state, "name", raw.state))
    levels = int(raw.levels_completed)
    if levels < 0:
        raise ValueError("Negative completed-level count")
    return PublicObservation(frames, actions, state, levels)


class CommunityEnvironment:
    def __init__(self, source_root, game_id, *, seed=200019, recordings_dir):
        from arc_agi import Arcade, OperationMode
        self._root = Path(source_root).resolve()
        # Some community packages use shared rendering helpers under scripts/.
        # Runtime import is allowed; no source analysis or hint extraction occurs.
        sys.path.insert(0, str(self._root))
        self._arcade = Arcade(environments_dir=str(self._root / "environment_files"),
                              operation_mode=OperationMode.OFFLINE,
                              recordings_dir=str(recordings_dir))
        self._environment = self._arcade.make(game_id, seed=seed, render_mode=None,
                                             save_recording=False)
        if self._environment is None:
            raise RuntimeError("SDK could not load the selected package")
        self._last = None

    def reset(self):
        self._last = public_observation(self._environment.reset())
        return self._last

    def step(self, action_id, data=None):
        from arcengine import GameAction
        if self._last is None or action_id not in self._last.available_actions:
            raise ValueError("Action must come from the current public available_actions")
        if action_id == 6:
            frame = self._last.frames[-1]
            if (not isinstance(data, dict) or set(data) != {"x", "y"}
                    or type(data["x"]) is not int or type(data["y"]) is not int
                    or not 0 <= data["x"] < len(frame[0]) or not 0 <= data["y"] < len(frame)):
                raise ValueError("ACTION6 needs in-frame integer x/y coordinates")
        elif data:
            raise ValueError("Unexpected payload for non-click action")
        # GameAction is not an IntEnum in the pinned SDK; use named members.
        self._last = public_observation(self._environment.step(
            getattr(GameAction, f"ACTION{action_id}"), data=data))
        return self._last


def _summary(observation):
    pixels = json.dumps(observation.frames, separators=(",", ":")).encode()
    return {"frame_count": len(observation.frames),
            "frame_shapes": [[len(f), len(f[0])] for f in observation.frames],
            "frame_sha256": hashlib.sha256(pixels).hexdigest(),
            "available_actions": observation.available_actions,
            "state": observation.state, "levels_completed": observation.levels_completed}


def smoke_game(source_root, game_id, output, *, seed=200019, max_actions=3):
    """One reset, at most three protocol-legal actions, and one further reset.

    Frame contents are not published in this compatibility report. Actions have
    a fixed ID order and center click; no planner, goal inspection or solution.
    """
    start = time.monotonic()
    result = {"schema_version": 1, "game_id": game_id, "seed": seed,
              "passed": False, "api_steps": [], "max_actions": max_actions,
              "scope": "CPU API compatibility only; not solvability, difficulty or model evaluation.",
              "source_code_inspected": False, "solver_calls": 0}
    try:
        env = CommunityEnvironment(source_root, game_id, seed=seed,
                                   recordings_dir=Path(output).parent / "recordings")
        obs = env.reset()
        result["initial"] = _summary(obs)
        used = set()
        for _ in range(max_actions):
            if obs.state in {"WIN", "GAME_OVER", "LOSE", "LOST"}:
                break
            order = [6, 1, 5, 7, 2, 3, 4]
            choices = [a for a in order if a in obs.available_actions and a not in used]
            if not choices:
                choices = [a for a in order if a in obs.available_actions]
            if not choices:
                raise ValueError("Nonterminal observation has no legal actions")
            action = choices[0]
            used.add(action)
            frame = obs.frames[-1]
            data = {"x": len(frame[0]) // 2, "y": len(frame) // 2} if action == 6 else None
            before = _summary(obs)
            obs = env.step(action, data)
            after = _summary(obs)
            result["api_steps"].append({"action": action, "data": data,
                "frame_changed": before["frame_sha256"] != after["frame_sha256"],
                "observation": after})
        result["reset_again"] = _summary(env.reset())
        result["same_reset_pixels"] = result["initial"]["frame_sha256"] == result["reset_again"]["frame_sha256"]
        result["passed"] = True
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    result["elapsed_seconds"] = time.monotonic() - start
    result["python"] = sys.version
    result["dependencies"] = {}
    for name in ["arc-agi", "arcengine", "numpy", "pydantic"]:
        try:
            result["dependencies"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["dependencies"][name] = None
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=200019)
    args = parser.parse_args()
    result = smoke_game(args.source_root, args.game_id, args.output, seed=args.seed)
    print(json.dumps({"game_id": args.game_id, "passed": result["passed"],
                      "error": result.get("error")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
