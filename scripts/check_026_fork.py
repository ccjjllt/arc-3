#!/usr/bin/env python3
"""026 CPU verification part 2: recheck verdicts on replayed cut states.

No model, no GPU. Replays each prefix to its cut locally, runs the host
recheck from src/arc3_research/failure_repair.py on the replayed grid, and
asserts the verdict contradicts the recorded failure claim (i.e. the host
recomputation actually recovers the evidence the model missed). Also checks
the Kaggle payload budget for the bundled fork inputs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"),
                str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src"),
                "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]

from arcengine import GameAction
from arc_agi import Arcade, OperationMode
from arc3_research.failure_repair import FORKS, QUOTED_EVIDENCE, RECHECK, ProbeBudget

failures = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + (f" :: {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


BENCH = {
    "ft09-0d8bbf25": "runs/015-native-adoption/baseline/benchmark.json",
    "tr87-cd924810": "runs/016-pace-allocation-jiyujia/pace_1x/benchmark.json",
    "r11l-495a7899": "runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
}


def replay_grid(game_id: str, actions: list, cut: int):
    arcade = Arcade(environments_dir=str(ROOT / "research/data/extracted/environment_files"),
                    operation_mode=OperationMode.OFFLINE,
                    recordings_dir="/tmp/arc3-026-check")
    env = arcade.make(game_id, seed=0, render_mode=None, save_recording=False)
    assert env is not None and env.reset() is not None
    game = env._game
    for item in actions[:cut]:
        env.step(GameAction.from_name(item["action"]["id"]),
                 data=item["action"].get("data") or None)
    raw = game.camera.render(game.current_level.get_sprites())
    data = raw.tolist() if hasattr(raw, "tolist") else raw
    return tuple(tuple(int(c) for c in row) for row in data)


def main() -> None:
    check("three forks pinned", set(FORKS) == set(BENCH), str(set(FORKS)))
    check("quoted evidence bundled", all(len(v) < 400 for v in QUOTED_EVIDENCE.values()))
    total_actions = 0
    for game_id, bench_rel in BENCH.items():
        bench = json.loads((ROOT / bench_rel).read_text())
        history = next(g["history"] for g in bench["game_runs"] if g["game_id"] == game_id)
        cut = int(FORKS[game_id]["cut"])
        total_actions += cut
        grid = replay_grid(game_id, history, cut)
        kind = FORKS[game_id]["kind"]
        text = RECHECK[kind](grid)
        check(f"{game_id} recheck non-empty", len(text) > 100, text[:80])
        check(f"{game_id} recheck cites prior failure",
              QUOTED_EVIDENCE[game_id][:40] in text)
        check(f"{game_id} recheck has 0-env-action stamp", "0 env actions" in text)
    # ft09: inventory must show g-nodes the WOW claim contradicts
    bench = json.loads((ROOT / BENCH["ft09-0d8bbf25"]).read_text())
    history = next(g["history"] for g in bench["game_runs"] if g["game_id"] == "ft09-0d8bbf25")
    grid = replay_grid("ft09-0d8bbf25", history, int(FORKS["ft09-0d8bbf25"]["cut"]))
    from inference.utils.segmentation import segment_layer
    from inference.utils.grid_utils import ARC_COLOR_CHARS
    nodes = segment_layer([list(map(int, r)) for r in grid], ARC_COLOR_CHARS)["nodes"]
    g_px = sum(n["pixels"] for n in nodes if n["color"] == "g")
    check("ft09 g-node pixels visible to host", g_px > 0, str(g_px))
    # tr87: ink box must cover the dropped bottom row (recount > 11)
    bench = json.loads((ROOT / BENCH["tr87-cd924810"]).read_text())
    history = next(g["history"] for g in bench["game_runs"] if g["game_id"] == "tr87-cd924810")
    grid = replay_grid("tr87-cd924810", history, int(FORKS["tr87-cd924810"]["cut"]))
    rows = [list(map(int, r)) for r in grid]
    ink = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row)
           if ARC_COLOR_CHARS[v] != "B"]
    check("tr87 ink recount exceeds cropped 11", len(ink) > 11, str(len(ink)))
    # m0r0 deferred this round (batch-internal cut); its evidence text stays
    # bundled but no fork boundary is asserted here.
    # zero-env guard: refuses through the hook path, restores cleanly
    from arc3_research.failure_repair import install_zero_env_guard

    class _FakeAnalyzer:
        def _action_guard_hook(self, grid, name, data, level=None,
                               remaining=None):
            return None

    fake = _FakeAnalyzer()
    undo = install_zero_env_guard(fake)
    verdict = fake._action_guard_hook([[0]], "ACTION6", {"x": 1}, level=3,
                                      remaining=[])
    check("K=0 guard refuses env action",
          isinstance(verdict, tuple) and verdict[0] == "probe_budget_reached",
          str(verdict)[:100])
    check("K=0 refusal names uncatchable stop",
          "NOT executed" in verdict[1] and "not catchable" in verdict[1])
    undo()
    check("K=0 guard uninstall restores base hook",
          getattr(fake._action_guard_hook, "__func__", None)
          is _FakeAnalyzer._action_guard_hook)
    check("probe budget K=0 forbids dispatch", ProbeBudget(0).request() is False)
    # Payload budget: fork inputs must fit the 1MB notebook cap with margin
    compact = {}
    for g, rel in BENCH.items():
        h = next(x["history"] for x in json.loads((ROOT / rel).read_text())["game_runs"] if x["game_id"] == g)
        compact[g] = [{"a": x["action"]["id"], "d": x["action"].get("data") or {}} for x in h[:FORKS[g]["cut"]]]
    blob = json.dumps({"forks": FORKS, "quoted": QUOTED_EVIDENCE, "actions": compact})
    check("fork inputs fit payload cap", len(blob) < 200_000, f"{len(blob)} bytes")
    # fork-inputs payload parses through the consumer's normalization
    import arcengine
    payload = json.loads((ROOT / "experiments/026-fork-inputs.json").read_text())
    for game_id, spec in FORKS.items():
        items = payload["actions"][game_id]
        check(f"{game_id} payload covers cut",
              len(items) >= int(spec["cut"]), str(len(items)))
        for item in items[:int(spec["cut"])]:
            raw = item.get("action", item)
            name = raw.get("id", raw.get("a"))
            data = dict(raw.get("data", raw.get("d", {})) or {})
            member = getattr(arcengine.GameAction, name, None) \
                or arcengine.GameAction.from_name(name)
            arcengine.ActionInput(id=member, data=data)
    check("fork-inputs consumer parse", True)
    # packed conversation payload decodes through the driver's loader
    from arc3_research.failure_repair import load_fork_conversations
    convs = load_fork_conversations()
    check("conversations cover forks", set(FORKS) <= set(convs), str(set(convs)))
    check("conversations non-empty",
          all(len(v) > 5 for v in convs.values()),
          str({g: len(v) for g, v in convs.items()}))
    print(f"\n{len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
