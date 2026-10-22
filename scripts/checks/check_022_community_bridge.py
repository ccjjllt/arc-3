#!/usr/bin/env python3
"""CPU bridge check: development games only, public observations, no model.

Loads two development packages through the same offline Arcade entry the
research runner uses. Frozen and reserve ids are rejected before make().
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("/tmp/arc3-community-02152bc48068")
GAMES = ("tt03-63be02fb", "pt01-63be02fb")


def main() -> None:
    sys.path[:0] = [str(ROOT / "src"), str(Path("/private/tmp/arc3-018-sdk")),
                    str(Path("/private/tmp/arc3-018-check-deps"))]
    os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    from arc3_research.community import CommunityEnvironment, development_ids, load_allowlist
    from arc3_research.experiment_config import validate_config

    allow = load_allowlist()
    dev = development_ids()
    if len(dev) != 12 or set(dev) & set(allow["frozen"]):
        raise RuntimeError("development allowlist is not the frozen 12")
    for banned in ("sv02-63be02fb", "dv01-63be02fb"):
        if banned in dev:
            raise RuntimeError("frozen or reserve id entered development")
    config = json.loads((ROOT / "experiments/022-community-dev.json").read_text())
    validate_config(config)
    leaked = json.loads((ROOT / "experiments/022-community-dev.json").read_text())
    leaked["games"] = list(allow["frozen"][:12]) if False else dev[:-1] + [allow["frozen"][0]]
    try:
        validate_config(leaked)
    except ValueError:
        pass
    else:
        raise RuntimeError("config accepted a frozen community id")

    out = ROOT / "experiments/022-community-cpu"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for game_id in GAMES:
        env = CommunityEnvironment(SOURCE, game_id, seed=200019, recordings_dir=out / "recordings" / game_id)
        obs = env.reset()
        payload = obs.to_solver()
        if set(payload) != {"frames", "available_actions", "state", "levels_completed"}:
            raise RuntimeError(f"{game_id} observation leaked a non-public field")
        action_id = next(a for a in (1, 5, 7, 2, 3, 4, 6) if a in obs.available_actions)
        data = None
        if action_id == 6:
            frame = obs.frames[-1]
            data = {"x": len(frame[0]) // 2, "y": len(frame) // 2}
        after = env.step(action_id, data=data)
        rows.append({"game_id": game_id, "action_id": action_id,
                     "before_state": obs.state, "after_state": after.state,
                     "levels_completed": after.levels_completed,
                     "frame_shape": [len(after.frames[-1]), len(after.frames[-1][0])]})
    report = {"status": "passed", "games": rows, "development_count": len(dev),
              "model_calls": 0, "frozen_used": False,
              "limits": ["Engine reset and one legal action. Not an agent solve and not an official score."]}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
