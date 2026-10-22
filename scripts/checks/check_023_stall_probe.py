#!/usr/bin/env python3
"""CPU check for the level-stall trigger. Not a score.

The 023 screen counted four batches with no gameplay_changed. That counter
stays in the historical report under experiments/023-stall-probe-cpu/. This
script checks the replacement: 64 executed actions on one unfinished level.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from arc3_research.experiment_config import validate_config
from arc3_research.stall_probe import (
    PROBE_ACTIONS, STALL_ACTIONS, StallProbePatch, StallTracker, game_id_from_state_path,
)


def step(level, *, n=1, completed=False, game_over=False):
    return {
        "executed": True, "level": level, "executed_actions": ["ACTION1"] * n,
        "level_completed": completed, "game_over": game_over,
        "done": False, "run_complete": False, "gameplay_changed": True,
    }


def main() -> None:
    historical = json.loads((ROOT / "experiments/023-stall-probe.json").read_text())
    validate_config(historical)
    wide = json.loads((ROOT / "experiments/023-stall-probe.json").read_text())
    wide["games"] = wide["games"] + ["ft09-0d8bbf25"]
    try:
        validate_config(wide)
    except ValueError:
        pass
    else:
        raise RuntimeError("stall probe accepted a game outside its two screens")
    pair = json.loads((ROOT / "experiments/024-level-stall.json").read_text())
    validate_config(pair)
    leaked = json.loads((ROOT / "experiments/024-level-stall.json").read_text())
    leaked["games"] = ["tt03-63be02fb", "sv02-63be02fb"]
    try:
        validate_config(leaked)
    except ValueError:
        pass
    else:
        raise RuntimeError("024 accepted a game outside the recorded failure pair")

    quiet = StallTracker()
    for _ in range(STALL_ACTIONS - 1):
        if quiet.observe("ih01-v1", [step(1)]) is not None:
            raise RuntimeError("triggered before 64 actions")
    note = quiet.observe("ih01-v1", [step(1, game_over=False)])
    if not note or note["actions_on_level"] != STALL_ACTIONS:
        raise RuntimeError(f"64th action did not trigger: {note}")
    if quiet.observe("ih01-v1", [step(1)]) is not None:
        raise RuntimeError("same level triggered twice")

    deaths = StallTracker()
    deaths.observe("ih01-v1", [step(1, n=40, game_over=True)])
    deaths.observe("ih01-v1", [step(1, n=1)])  # RESET stays on the level
    if deaths.observe("ih01-v1", [step(1, n=22)]) is not None:
        raise RuntimeError("a lost life cleared the level count")
    if deaths.observe("ih01-v1", [step(1)]) is None:
        raise RuntimeError("actions after RESET did not reach 64")

    levels = StallTracker()
    levels.observe("tt03-63be02fb", [step(1, n=29, completed=True)])
    if levels.streak.get(("tt03-63be02fb", "level:1")):
        raise RuntimeError("a completed level kept its stall count")
    if levels.observe("tt03-63be02fb", [step(2, n=STALL_ACTIONS - 1)]) is not None:
        raise RuntimeError("the next level triggered early")
    if levels.observe("tt03-63be02fb", [step(2)]) is None:
        raise RuntimeError("the unfinished next level did not trigger at 64")

    batched = StallTracker()
    first = batched.observe("tt03-63be02fb", [step(2, n=40), step(2, n=30)])
    if not first or first["actions_on_level"] != 70:
        raise RuntimeError(f"a batch was not counted per action: {first}")
    if batched.following.get(("tt03-63be02fb", "level:2")) != PROBE_ACTIONS:
        raise RuntimeError("actions already executed in the triggering call consumed the window")
    batched.observe("tt03-63be02fb", [step(2, n=2)])
    if batched.following.get(("tt03-63be02fb", "level:2")) != 1:
        raise RuntimeError("following actions were not counted one by one")
    batched.observe("tt03-63be02fb", [step(2, n=4)])
    if batched.following:
        raise RuntimeError("the window stayed open after three following actions")

    if game_id_from_state_path("/tmp/run/artifacts/ih01-v1_tool_runtime_state.json") != "ih01-v1":
        raise RuntimeError("game id was not read from the runtime state name")

    class Result:
        def __init__(self, content, step_executed=False, made_progress=False):
            self.content = content
            self.step_executed = step_executed
            self.made_progress = made_progress

    def handler(actions, stale_after=None):
        return {"action_result": step(1), "state": {}}

    class Mod:
        class ToolAgent:
            def _run_python_tool(self, state_path, arguments):
                Mod.run_sandboxed_python(action_handler=handler)
                return Result(json.dumps({"returncode": 0}), step_executed=True)

        @staticmethod
        def run_sandboxed_python(*args, **kwargs):
            kwargs["action_handler"]([{"action": "RIGHT"}], stale_after=None)
            return {"ok": True}

    patch = StallProbePatch(Mod)
    patch.install()
    try:
        result = None
        for _ in range(STALL_ACTIONS):
            result = Mod.ToolAgent._run_python_tool(
                None, Path("/tmp/run/artifacts/ih01-v1_tool_runtime_state.json"), {})
        payload = json.loads(result.content)
        if not payload.get("stall_probe", {}).get("triggered"):
            raise RuntimeError(f"wrapper did not surface the trigger: {payload}")
        plain = Mod.ToolAgent._run_python_tool(
            None, Path("/tmp/run/artifacts/ih01-v1_tool_runtime_state.json"), {})
        if "stall_probe" in json.loads(plain.content):
            raise RuntimeError("a later call on the same level appended another probe")
    finally:
        patch.uninstall()
    if Mod.ToolAgent._run_python_tool is not patch._original_tool:
        raise RuntimeError("uninstall did not restore the tool method")

    out = ROOT / "experiments/024-level-stall-cpu"
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "passed", "stall_actions": STALL_ACTIONS, "probe_actions": PROBE_ACTIONS,
              "count": "executed_actions_on_level", "pixel_change_resets_count": False}
    (out / "unit-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
