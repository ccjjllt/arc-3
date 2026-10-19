#!/usr/bin/env python3
"""CPU check for the one-shot stall trigger. Not a score."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arc3_research.experiment_config import validate_config
from arc3_research.stall_probe import StallProbePatch, StallTracker, game_id_from_state_path


def batch(level, *, changed=False, executed=True, completed=False):
    return {"executed": executed, "level": level, "gameplay_changed": changed,
            "level_completed": completed, "game_over": False, "done": False, "run_complete": False}


def main() -> None:
    config = json.loads((ROOT / "experiments/023-stall-probe.json").read_text())
    validate_config(config)
    wide = json.loads((ROOT / "experiments/023-stall-probe.json").read_text())
    wide["games"] = wide["games"] + ["ft09-0d8bbf25"]
    try:
        validate_config(wide)
    except ValueError:
        pass
    else:
        raise RuntimeError("023 accepted more than 3 games")

    tracker = StallTracker()
    for _ in range(3):
        if tracker.observe("m0r0", [batch(1)]) is not None:
            raise RuntimeError("triggered before four quiet batches")
    note = tracker.observe("m0r0", [batch(1)])
    if not note or note["no_progress_batches"] != 4:
        raise RuntimeError(f"fourth batch did not trigger: {note}")
    if tracker.observe("m0r0", [batch(1)]) is not None:
        raise RuntimeError("same level triggered twice")
    for _ in range(2):
        tracker.observe("m0r0", [batch(1)])
    if tracker.following:
        raise RuntimeError("window stayed open after three following actions")
    again = StallTracker()
    again.observe("m0r0", [batch(1, changed=True)])
    again.observe("m0r0", [batch(2)])
    if again.streak.get(("m0r0", "level:2")) != 1:
        raise RuntimeError("a new level did not get its own streak")
    if game_id_from_state_path("/tmp/run/artifacts/m0r0-492f87ba_tool_runtime_state.json") != "m0r0-492f87ba":
        raise RuntimeError("game id was not read from the runtime state name")

    class Result:
        def __init__(self, content, step_executed=False, made_progress=False):
            self.content = content
            self.step_executed = step_executed
            self.made_progress = made_progress

    def handler(actions, stale_after=None):
        return {"action_result": batch(1), "state": {}}

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
        for _ in range(4):
            result = Mod.ToolAgent._run_python_tool(
                None, Path("/tmp/run/artifacts/m0r0_tool_runtime_state.json"), {})
        payload = json.loads(result.content)
        if not payload.get("stall_probe", {}).get("triggered"):
            raise RuntimeError(f"wrapper did not surface the trigger: {payload}")
    finally:
        patch.uninstall()
    if Mod.ToolAgent._run_python_tool is not patch._original_tool:
        raise RuntimeError("uninstall did not restore the tool method")
    out = ROOT / "experiments/023-stall-probe-cpu"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({"status": "passed", "trigger_batches": 4,
                                                 "probe_actions": 3}, indent=2) + "\n")
    print(json.dumps({"status": "passed"}))


if __name__ == "__main__":
    main()
