#!/usr/bin/env python3
"""Manually exercise 034 through the frozen ToolAgent and real Python child.

The public-frame world and completion responses are scripted. This verifies
native wiring, action consumption and accounting, not model adoption, ARC game
performance or a leaderboard score. No network, model server or GPU is used.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "research/runtime-bundle/src/ARC3-Inference"
USAGE = {"prompt_tokens": 11, "completion_tokens": 37, "total_tokens": 48}
PAUSED_BATCH = '''old_plan = ["LEFT", "LEFT", "LEFT"]
action(old_plan)
print("OLD_SUFFIX_EXECUTED")
'''
PAUSED_SINGLES = '''old_plan = ["RIGHT", "LEFT", "LEFT"]
def move_one(name):
    action(name)
move_one(old_plan[0])
move_one(old_plan[1])
move_one(old_plan[2])
print("OLD_SUFFIX_EXECUTED")
'''


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def program(marker: str, background: str, *, moves=2, unknown_after=None,
            side_effect=False, wrong_evidence=False, replace_sentinel=False) -> str:
    """Controlled response recomputes its input, goal and plan from live ASCII."""
    prefix = 'def sentinel():\n    return "candidate"\n\n' if replace_sentinel else ""
    insertion = '    execute = action\n    execute("RIGHT")\n' if side_effect else ""
    uncertain = (f'    if frame.step >= {unknown_after}:\n'
                 '        raise ValueError("scripted unavailable observation")\n'
                 if unknown_after is not None else "")
    evidence_color = repr(background if wrong_evidence else marker)
    return prefix + f'''def locate(frame):
    rows = frame.ascii.splitlines()
    for row, line in enumerate(rows):
        if {marker!r} in line:
            return row, line.index({marker!r}), len(line)
    raise ValueError("visible marker absent")

def plan_program(frame):
{insertion}    row, col, width = locate(frame)
    target = min(col + {moves}, width - 1)
    return {{"goal": {{"start_col": col, "target_col": target, "observed_step": frame.step}},
            "actions": [{{"action": "RIGHT"}} for _ in range(target - col)],
            "evidence_pixels": [[row, col, {evidence_color}]],
            "replaces": ["old_plan"],
            "reason": "Read the current marker and recompute its target and action count"}}

def predict(frame, action):
{uncertain}    row, col, width = locate(frame)
    delta = 1 if action["action"] == "RIGHT" else -1
    next_col = max(0, min(width - 1, col + delta))
    return {{"scope": "visible marker source and destination pixels",
            "expected_pixels": [[row, col, {background!r}], [row, next_col, {marker!r}]]}}
'''


class World:
    """A tiny synthetic public observation/action API; no ARC implementation."""

    def __init__(self, path, runtime_state, *, mode="normal"):
        self.path = path
        self.runtime_state = runtime_state
        self.mode = mode
        self.row, self.col, self.width, self.height = 2, 1, 10, 5
        self.step, self.level = 0, 1
        self.calls = []
        self.history = []
        self.flush()

    def frame(self):
        grid = [[0] * self.width for _ in range(self.height)]
        grid[self.row][self.col] = 2
        return self.runtime_state.Frame(tuple(tuple(r) for r in grid), self.step, self.level)

    def flush(self):
        self.runtime_state.write_runtime_state(
            self.path, current_frame=self.frame(), history=self.history)

    def timing_payload(self):
        return {"time_remaining_seconds": 1000.0}

    def step_env(self, request):
        if request.get("query"):
            raise AssertionError("No animation query is needed for this CPU check")
        actions = copy.deepcopy(request["actions"])
        before = {"step": self.step, "col": self.col, "level": self.level}
        self.calls.append({"actions": actions, "before": before})
        boundary = False
        for action in actions:
            name = action["action"]
            delta = 1 if name == "RIGHT" else -1 if name == "LEFT" else 0
            if self.mode == "mismatch_first" and self.step == 0:
                delta = -delta
            self.col = max(0, min(self.width - 1, self.col + delta))
            self.step += 1
            if self.mode == "boundary_first" and self.step == 1:
                self.level += 1
                self.col = 1
                boundary = True
            entry_result = {"executed": True, "level_completed": boundary,
                            "game_over": False, "gameplay_changed": True}
            self.history.append(self.runtime_state.HistoryEntry(name, self.frame(), entry_result))
            if boundary:
                break
        self.flush()
        count = self.step - before["step"]
        self.calls[-1]["after"] = {"step": self.step, "col": self.col, "level": self.level}
        return {"executed": bool(count), "executed_count": count,
                "requested_count": len(actions), "stopped_early": count < len(actions),
                "executed_actions": [a["action"] for a in actions[:count]],
                "action_num": self.step, "level": self.level,
                "state": "NOT_FINISHED", "valid_actions": ["RIGHT", "LEFT"],
                "board_changed": True, "gameplay_changed": True,
                "level_completed": boundary, "game_over": False,
                "done": False, "run_complete": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--scenario", action="append", default=[],
                        help="Run only a named scenario; repeat to select several.")
    args = parser.parse_args()
    out = (args.output_dir or ROOT / "experiments/034-cpu-check").resolve()
    if (out / "report.json").exists():
        if args.output_dir is not None:
            parser.error("Output already contains a report; select a fresh directory.")
        out = out / datetime.now(timezone.utc).strftime("rerun-%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(out / "matplotlib"))
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path[:0] = [str(ROOT / "src"), str(RUNTIME),
                    "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]
    report = {"status": "running", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "network_attempts": 0, "gpu_calls": 0,
              "real_model_calls": 0, "real_game_actions": 0, "native_sandbox_calls": 0,
              "output_dir": str(out), "scenarios": [], "limits": [
                  "Scripted completion responses and synthetic public frames; no ARC score.",
                  "The real frozen ToolAgent._run_python_tool and child sandbox are exercised.",
                  "Synthetic token usage checks bookkeeping only; it is not inference cost."]}

    def deny_network(event, _arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("034 CPU check prohibits network access")
    sys.addaudithook(deny_network)

    spec = importlib.util.spec_from_file_location("arc3_check018", ROOT / "scripts/check_018_grounding.py")
    check018 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check018)
    os.environ.update(check018.baseline_environment())
    os.environ.pop("ARC3_SYSTEM_PROMPT_PREFIX", None)
    from inference.agent import tool_agent, python_tool_sandbox, runtime_state
    from inference.utils.grid_utils import ARC_COLOR_CHARS
    from arc3_research.executable_plan import install_executable_plan
    from arc3_research.program_repair import _payload

    original_sandbox = tool_agent.run_sandboxed_python
    original_python = tool_agent.ToolAgent._run_python_tool
    original_bootstrap = python_tool_sandbox._SANDBOX_BOOTSTRAP

    def counted_sandbox(**kwargs):
        report["native_sandbox_calls"] += 1
        return original_sandbox(**kwargs)
    tool_agent.run_sandboxed_python = counted_sandbox
    good = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0])
    invalid = "def plan_program(frame):\n    return {}\ndef predict(frame, action):\n    return {}\n"
    scenarios = [
        {"name": "ordinary_batch_bootstrap", "snippet": PAUSED_BATCH, "responses": [good],
         "actions": ["RIGHT", "RIGHT"], "calls": 1, "start_col": 1},
        {"name": "single_helpers_pause_second", "snippet": PAUSED_SINGLES, "responses": [good],
         "actions": ["RIGHT", "RIGHT", "RIGHT"], "calls": 1, "start_col": 2},
        {"name": "mismatch_repairs_then_acts", "snippet": PAUSED_BATCH, "mode": "mismatch_first",
         "responses": [good, good], "actions": ["RIGHT", "RIGHT", "RIGHT"], "calls": 2,
         "required_status": "mismatch"},
        {"name": "unknown_stops_suffix", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], unknown_after=1), invalid],
         "actions": ["RIGHT"], "calls": 2, "required_status": "unknown"},
        {"name": "zero_action_validation", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], side_effect=True)],
         "actions": [], "calls": 1, "rejected": True, "rollback": True},
        {"name": "invalid_evidence_rolls_back_functions", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], wrong_evidence=True,
                               replace_sentinel=True)],
         "actions": [], "calls": 1, "rejected": True, "rollback": True},
        {"name": "level_boundary_stops_plan", "snippet": PAUSED_BATCH, "mode": "boundary_first",
         "responses": [good], "actions": ["RIGHT"], "calls": 1,
         "required_status": "boundary", "inactive": True},
        {"name": "validation_preserves_repeat_guard", "responses": [],
         "actions": [], "calls": 0, "evaluate_only": True},
        {"name": "initial_prediction_rejected_rolls_back", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], unknown_after=0,
                               replace_sentinel=True)],
         "actions": [], "calls": 1, "rejected": True, "rollback": True},
    ]
    if args.scenario:
        unknown = set(args.scenario) - {s["name"] for s in scenarios}
        if unknown:
            parser.error("Unknown scenarios: " + ", ".join(sorted(unknown)))
        scenarios = [s for s in scenarios if s["name"] in args.scenario]
    try:
        for scenario in scenarios:
            started = time.monotonic()
            case_dir = out / scenario["name"]
            case_dir.mkdir(exist_ok=True)
            state_path = case_dir / "tool_runtime_state.json"
            event_path = state_path.with_name(state_path.stem + "_executable-plan.jsonl")
            if event_path.exists():
                event_path.unlink()  # This run owns only its 034 output directory.
            world = World(state_path, runtime_state, mode=scenario.get("mode", "normal"))
            agent = tool_agent.ToolAgent(model="cpu-no-model", provider="vllm",
                                        base_url="http://cpu.invalid/v1", api_key="cpu-placeholder")
            agent._ensure_session(state_path)
            agent._current_valid_actions = ["RIGHT", "LEFT"]
            agent._step_env_callback = world.step_env
            seed = agent._run_python_tool(state_path, {"code": 'def sentinel():\n    return "original"\nresult = sentinel()'})
            if _payload(seed.content).get("result") != "original":
                raise AssertionError("Native retained-function setup failed")
            retained_before = copy.deepcopy(agent._kept_functions)
            responses = []

            def completion(actor, messages, tools, *, timeout, max_tokens):
                index = len(responses)
                responses.append({"index": index, "observed_step": world.step,
                                  "observed_col": world.col, "timeout": timeout,
                                  "max_tokens": max_tokens, "usage": USAGE,
                                  "last_message": messages[-1]})
                if index >= len(scenario["responses"]):
                    raise AssertionError("Unexpected extra scripted completion request")
                message = {"role": "assistant", "content": "", "tool_calls": [
                    {"id": f"cpu-{index}", "type": "function", "function": {
                        "name": "python", "arguments": json.dumps({"code": scenario["responses"][index]})}}]}
                return tool_agent._ChatCompletionResult(message=message, usage=dict(USAGE),
                                                        finish_reason="tool_calls", served_by="scripted-cpu")

            patch = install_executable_plan(completion=completion, min_remaining_seconds=0)
            case = {"name": scenario["name"], "status": "running"}
            try:
                state = patch.state(agent, state_path)
                if scenario.get("evaluate_only"):
                    guard_object = agent._repeat_state_seen
                    guard_object.add("034-existing-repeat-state")
                    expected_guard = set(guard_object)
                    value = patch.evaluate(agent, state, 'result = {"computed": 6 * 7}')
                    payload = {"evaluation": value}
                    step_executed, made_progress = False, False
                    assert value == {"computed": 42}
                    assert agent._repeat_state_seen is guard_object
                    assert agent._repeat_state_seen == expected_guard
                    case["same_repeat_guard_object_and_contents"] = True
                else:
                    result = agent._run_python_tool(state_path, {"code": scenario["snippet"]})
                    payload = _payload(result.content)
                    step_executed, made_progress = result.step_executed, result.made_progress
                actions = [a["action"] for call in world.calls for a in call["actions"]]
                statuses = [e.get("status") for e in state.events]
                case.update(actions=actions, action_calls=world.calls, scripted_completions=responses,
                            tool_output=payload, step_executed=step_executed,
                            made_progress=made_progress, events=state.events,
                            patch=patch.snapshot(), retained_functions=agent._kept_functions,
                            final_frame={"step": world.step, "col": world.col, "level": world.level},
                            recorded_tokens={"generated": agent.generated_tokens, "total": agent.total_tokens})
                assert actions == scenario["actions"], (scenario["name"], actions)
                assert len(responses) == scenario["calls"], (scenario["name"], len(responses))
                assert agent.generated_tokens == len(responses) * USAGE["completion_tokens"]
                assert agent.total_tokens == len(responses) * USAGE["total_tokens"]
                assert "OLD_SUFFIX_EXECUTED" not in str(payload.get("stdout", ""))
                if scenario.get("required_status"):
                    assert scenario["required_status"] in statuses, statuses
                if scenario.get("rejected"):
                    assert payload["executable_plan"]["status"] == "rejected", payload
                if scenario.get("rollback"):
                    assert agent._kept_functions == retained_before, "Candidate function escaped rollback"
                if scenario.get("inactive"):
                    assert state.program is None and not state.repair_used
                if "start_col" in scenario:
                    assert payload["executable_plan"]["goal"]["start_col"] == scenario["start_col"]
                    assert responses[0]["observed_col"] == scenario["start_col"]
                if scenario["name"] == "single_helpers_pause_second":
                    trigger = next(e for e in state.events if e.get("kind") == "bootstrap")
                    assert trigger["already_executed_in_snippet"] == 1
                if scenario["name"] == "mismatch_repairs_then_acts":
                    assert responses[1]["observed_step"] == 1
                    assert responses[1]["observed_col"] == 0
                    assert payload["executable_plan"]["followup_repair"]["actual_actions"] == 2
                case["status"] = "passed"
            except Exception as exc:
                case.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            finally:
                patch.uninstall()
                case["elapsed_seconds"] = time.monotonic() - started
                save(case_dir / "result.json", case)
                report["scenarios"].append({k: case.get(k) for k in
                    ("name", "status", "actions", "error", "elapsed_seconds", "recorded_tokens")})
                save(out / "report.json", report)
        assert report["network_attempts"] == 0
        assert tool_agent.ToolAgent._run_python_tool is original_python
        assert python_tool_sandbox._SANDBOX_BOOTSTRAP == original_bootstrap
        failures = [s["name"] for s in report["scenarios"] if s["status"] != "passed"]
        assert not failures, "Native CPU scenarios failed: " + ", ".join(failures)
        report["status"] = "passed"
        report["scripted_completion_calls"] = sum(s["recorded_tokens"]["generated"] // 37
                                                   for s in report["scenarios"])
    except Exception as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        tool_agent.run_sandboxed_python = original_sandbox
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in [Path(__file__), ROOT / "src/arc3_research/executable_plan.py",
                                             ROOT / "src/arc3_research/executable_plan_contract.py"]}
        save(out / "report.json", report)
    print(json.dumps({"status": report["status"], "scenarios": len(report["scenarios"]),
                      "report_path": str(out / "report.json"),
                      "native_sandbox_calls": report["native_sandbox_calls"],
                      "scripted_completion_calls": report["scripted_completion_calls"],
                      "network_attempts": report["network_attempts"]}))


if __name__ == "__main__":
    main()
