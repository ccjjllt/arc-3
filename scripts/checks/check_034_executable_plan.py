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


ROOT = Path(__file__).resolve().parents[2]
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
            side_effect=False, wrong_evidence=False, replace_sentinel=False,
            local_status=None, plan_error_after=None) -> str:
    """Controlled response recomputes its input, goal and plan from live ASCII."""
    prefix = 'def sentinel():\n    return "candidate"\n\n' if replace_sentinel else ""
    insertion = '    execute = action\n    execute("RIGHT")\n' if side_effect else ""
    if plan_error_after is not None:
        insertion += f'    if frame.step >= {plan_error_after}:\n        raise ValueError("scripted recomputation failure")\n'
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
    target = min({moves + 1}, width - 1)
    status = {local_status!r} or ("completed" if col >= target else "ready")
    return {{"status": status,
            "goal": {{"start_col": col, "target_col": target, "observed_step": frame.step,
                       "transition_count": len(frame.recent_transitions)}},
            "actions": [{{"action": "RIGHT"}} for _ in range(min(3, max(0, target - col)))] if status == "ready" else [],
            "evidence_pixels": [[row, col, {evidence_color}]],
            "replaces": ["old_plan"],
            "reason": "Read the current marker and recompute its target and action count"}}

def predict(frame, action):
{uncertain}    row, col, width = locate(frame)
    delta = 1 if action["action"] == "RIGHT" else -1
    next_col = max(0, min(width - 1, col + delta))
    return {{"mode": "change", "action": action,
            "object_pixels": [[row, col, {marker!r}]],
            "target_pixels": [[row, next_col, {background!r}]],
            "precondition": "Adjacent destination is empty and a RIGHT/LEFT move translates the marker one column",
            "scope": "visible marker source and destination pixels",
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
    parser.add_argument("--auxiliary-reasoning-mode", choices=("off", "low"), default="off",
                        help="Branch-only mode; the default retains the v9 off behavior.")
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
              "injected_native_transport_faults": 0,
              "auxiliary_reasoning_mode": args.auxiliary_reasoning_mode,
              "output_dir": str(out), "scenarios": [], "limits": [
                  "Scripted completion responses and synthetic public frames; no ARC score.",
                  "The real frozen ToolAgent._run_python_tool and child sandbox are exercised.",
                  "One scenario injects a native transport error before child launch to verify it is not treated as a model-code error.",
                  "Synthetic token usage checks bookkeeping only; it is not inference cost.",
                  "The synthetic world reports 1000 seconds remaining; this does not verify real 450-second game deadlines."]}

    def deny_network(event, _arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("034 CPU check prohibits network access")
    sys.addaudithook(deny_network)

    spec = importlib.util.spec_from_file_location("arc3_check018", ROOT / "scripts/checks/check_018_grounding.py")
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

    transport_fault = {"pending": None}

    def counted_sandbox(**kwargs):
        if (transport_fault["pending"] and
                kwargs.get("code", "").rstrip().endswith("result = plan_program(current_frame)")):
            error, transport_fault["pending"] = transport_fault["pending"], None
            report["injected_native_transport_faults"] += 1
            return {"error": error, "stdout": "", "action_results": []}
        report["native_sandbox_calls"] += 1
        return original_sandbox(**kwargs)
    tool_agent.run_sandboxed_python = counted_sandbox
    good = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0])
    invalid = "def plan_program(frame):\n    return {}\ndef predict(frame, action):\n    return {}\n"
    top_level_constant = "CELL_H = 8\n" + good
    syntax_invalid = "def plan_program(frame):\n    return (\n"
    # Formatting alone is not a resource failure: v7 rejected a complete
    # 129-line revision despite its small byte/AST footprint. Conversely, a
    # long single comment must still hit the actual delivery byte boundary.
    many_lines = good + "\ndef unused_formatting_helper():\n" + "    pass\n" * 100
    oversized = good + "\n#" + "x" * (12001 - len(good.encode("utf-8")) - 2)
    assert sum(bool(line.strip()) for line in many_lines.splitlines()) > 120
    assert len(many_lines.encode("utf-8")) < 12000
    assert len(oversized.encode("utf-8")) == 12001
    literal_defaults = good.replace("def locate(frame):", "def locate(frame, offset=0):").replace(
        f"line.index({ARC_COLOR_CHARS[2]!r})", f"line.index({ARC_COLOR_CHARS[2]!r}) + offset")
    computed_default = literal_defaults.replace("offset=0", "offset=len([])")
    mutable_default = literal_defaults.replace("offset=0", "offset=[]")
    multiple_contract_errors = "CELL_H = 8\n" + good.replace(
        "def locate(frame):", "def locate(frame: object, offset=[]):")
    # Use actual failing operations in the native child, rather than replacing
    # the evaluator with a mock. The second one mirrors v6's tuple/float bug.
    plan_type_error = good.replace("def plan_program(frame):\n",
        "def plan_program(frame):\n    coordinate = (1, 2)\n    coordinate = coordinate + 0.5\n")
    predict_type_error = good.replace("def predict(frame, action):\n",
        "def predict(frame, action):\n    coordinate = (1, 2)\n    coordinate = coordinate + 0.5\n")
    declared_unknown = good.replace("def predict(frame, action):\n",
        'def predict(frame, action):\n    return {"mode": "unknown", "reason": "insufficient observed dynamics"}\n')
    invalid_with_sentinel = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0],
        wrong_evidence=True, replace_sentinel=True)
    unavailable_with_sentinel = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0],
        unknown_after=0, replace_sentinel=True)
    evidence_text = '"evidence_pixels": [[row, col, ' + repr(ARC_COLOR_CHARS[2]) + ']]'
    empty_abstain = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], local_status="abstain").replace(
        evidence_text, '"evidence_pixels": []').replace('"replaces": ["old_plan"]', '"replaces": []')
    empty_completed = program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], local_status="completed").replace(
        evidence_text, '"evidence_pixels": []')
    duplicate_wrong_evidence = good.replace(evidence_text,
        '"evidence_pixels": [[row, col, ' + repr(ARC_COLOR_CHARS[0])
        + '], [row, col, ' + repr(ARC_COLOR_CHARS[0]) + ']]')
    duplicate_wrong_plan = {
        "status": "ready", "goal": {"start_col": 1, "target_col": 3, "observed_step": 0,
                                      "transition_count": 0},
        "actions": [{"action": "RIGHT"}, {"action": "RIGHT"}],
        "evidence_pixels": [[2, 1, ARC_COLOR_CHARS[0]], [2, 1, ARC_COLOR_CHARS[0]]],
        "replaces": ["old_plan"],
        "reason": "Read the current marker and recompute its target and action count"}
    explicit_ascii_api = good.replace("def plan_program(frame):\n",
        'def plan_program(frame):\n    if type(frame.ascii) is not str:\n'
        '        raise TypeError("FrameView.ascii must be str")\n')
    scenarios = [
        {"name": "ordinary_batch_bootstrap", "snippet": PAUSED_BATCH, "responses": [good],
         "actions": ["RIGHT", "RIGHT"], "calls": 1, "start_col": 1},
        {"name": "single_helpers_pause_second", "snippet": PAUSED_SINGLES, "responses": [good],
         "actions": ["RIGHT", "RIGHT"], "calls": 1, "start_col": 2},
        {"name": "mismatch_repairs_then_acts", "snippet": PAUSED_BATCH, "mode": "mismatch_first",
         "responses": [good, good], "actions": ["RIGHT", "RIGHT", "RIGHT", "RIGHT"], "calls": 2,
         "required_status": "mismatch"},
        {"name": "unknown_stops_suffix", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], unknown_after=1), invalid],
         "actions": ["RIGHT"], "calls": 1, "required_status": "unknown"},
        {"name": "zero_action_validation", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], side_effect=True)],
         "actions": [], "calls": 1, "rejected": True, "rollback": True},
        {"name": "invalid_evidence_rolls_back_functions", "snippet": PAUSED_BATCH,
         "responses": [invalid_with_sentinel, invalid_with_sentinel],
         "actions": [], "calls": 2, "rejected": True, "rollback": True,
         "feedback_stage": "plan_validation", "feedback_code": invalid_with_sentinel},
        {"name": "level_boundary_stops_plan", "snippet": PAUSED_BATCH, "mode": "boundary_first",
         "responses": [good], "actions": ["RIGHT"], "calls": 1,
         "required_status": "boundary", "inactive": True},
        {"name": "validation_preserves_repeat_guard", "responses": [],
         "actions": [], "calls": 0, "evaluate_only": True},
        {"name": "initial_prediction_rejected_rolls_back", "snippet": PAUSED_BATCH,
         "responses": [unavailable_with_sentinel, unavailable_with_sentinel],
         "actions": [], "calls": 2, "rejected": True, "rollback": True,
         "feedback_stage": "initial_prediction", "feedback_code": unavailable_with_sentinel},
        {"name": "completed_local_goal_no_action", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], local_status="completed")],
         "actions": [], "calls": 1, "local_status": "local_completed", "inactive": True},
        {"name": "abstain_no_action", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], local_status="abstain")],
         "actions": [], "calls": 1, "local_status": "abstained", "inactive": True},
        {"name": "abstain_empty_evidence_and_bindings_does_not_use_repair", "snippet": PAUSED_BATCH,
         "responses": [empty_abstain], "actions": [], "calls": 1,
         "local_status": "abstained", "inactive": True, "empty_abstain": True},
        {"name": "completed_empty_evidence_still_rejected", "snippet": PAUSED_BATCH,
         "responses": [empty_completed, empty_completed], "actions": [], "calls": 2,
         "rejected": True, "rollback": True, "feedback_stage": "plan_validation",
         "feedback_code": empty_completed, "feedback_plan_minimum": 1},
        {"name": "ready_multiple_plan_errors_share_one_feedback_then_execute", "snippet": PAUSED_BATCH,
         "responses": [duplicate_wrong_evidence, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "plan_validation", "feedback_code": duplicate_wrong_evidence,
         "feedback_success": True, "feedback_plan_minimum": 2,
         "returned_plan": duplicate_wrong_plan},
        {"name": "short_contract_total_action_limit", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], moves=8)],
         "actions": ["RIGHT", "RIGHT", "RIGHT"], "calls": 1, "inactive": True},
        {"name": "ordinary_action_after_contract", "snippet": PAUSED_BATCH, "responses": [good],
         "after_code": 'result = action("LEFT")',
         "actions": ["RIGHT", "RIGHT", "LEFT"], "calls": 1, "inactive": True},
        {"name": "recomputation_failure_keeps_action_accounting", "snippet": PAUSED_BATCH,
         "responses": [program(ARC_COLOR_CHARS[2], ARC_COLOR_CHARS[0], plan_error_after=1)],
         "actions": ["RIGHT"], "calls": 1, "inactive": True},
        {"name": "top_level_constant_feedback_delivers_short_program", "snippet": PAUSED_BATCH,
         "responses": [top_level_constant, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": top_level_constant,
         "feedback_success": True},
        {"name": "oversized_feedback_delivers_short_program", "snippet": PAUSED_BATCH,
         "responses": [oversized, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": oversized,
         "feedback_success": True},
        {"name": "over_120_lines_runs_without_format_gate", "snippet": PAUSED_BATCH,
         "responses": [many_lines], "actions": ["RIGHT", "RIGHT"], "calls": 1},
        {"name": "literal_helper_default_runs_in_native_child", "snippet": PAUSED_BATCH,
         "responses": [literal_defaults], "actions": ["RIGHT", "RIGHT"], "calls": 1},
        {"name": "ascii_str_splitlines_uses_actual_native_api", "snippet": PAUSED_BATCH,
         "responses": [explicit_ascii_api], "actions": ["RIGHT", "RIGHT"], "calls": 1,
         "ascii_api_prompt": True},
        {"name": "computed_default_feedback_delivers_program", "snippet": PAUSED_BATCH,
         "responses": [computed_default, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": computed_default,
         "feedback_success": True, "feedback_error": "default"},
        {"name": "mutable_default_feedback_delivers_program", "snippet": PAUSED_BATCH,
         "responses": [mutable_default, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": mutable_default,
         "feedback_success": True, "feedback_error": "default"},
        {"name": "multiple_static_errors_share_single_feedback", "snippet": PAUSED_BATCH,
         "responses": [multiple_contract_errors, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": multiple_contract_errors,
         "feedback_success": True, "feedback_diagnostic_minimum": 3},
        {"name": "syntax_invalid_feedback_preserves_failed_source", "snippet": PAUSED_BATCH,
         "responses": [syntax_invalid, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "extract", "feedback_code": syntax_invalid,
         "feedback_success": True},
        {"name": "plan_type_error_feedback_delivers_short_program", "snippet": PAUSED_BATCH,
         "responses": [plan_type_error, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "plan_validation", "feedback_code": plan_type_error,
         "feedback_success": True, "feedback_error": "tuple"},
        {"name": "prediction_type_error_feedback_delivers_short_program", "snippet": PAUSED_BATCH,
         "responses": [predict_type_error, good], "actions": ["RIGHT", "RIGHT"], "calls": 2,
         "feedback_stage": "initial_prediction", "feedback_code": predict_type_error,
         "feedback_success": True, "feedback_error": "tuple"},
        {"name": "second_invalid_stops_and_restores_state", "snippet": PAUSED_BATCH,
         "responses": [top_level_constant, unavailable_with_sentinel],
         "actions": [], "calls": 2, "rejected": True, "rollback": True,
         "feedback_stage": "extract", "feedback_code": top_level_constant},
        {"name": "zero_action_fix_shares_mismatch_repair_quota", "snippet": PAUSED_BATCH,
         "mode": "mismatch_first", "responses": [top_level_constant, good],
         "actions": ["RIGHT"], "calls": 2, "required_status": "mismatch",
         "feedback_stage": "extract", "feedback_code": top_level_constant},
        {"name": "mismatch_repair_validation_failure_does_not_retry", "snippet": PAUSED_BATCH,
         "mode": "mismatch_first", "responses": [good, predict_type_error],
         "actions": ["RIGHT"], "calls": 2, "required_status": "mismatch"},
        {"name": "feedback_budget_exhausted_does_not_request", "snippet": PAUSED_BATCH,
         "responses": [top_level_constant], "actions": [], "calls": 1,
         "exhaust_extra_budget_on_response": True, "rejected": True, "rollback": True},
        {"name": "native_transport_failure_is_not_program_feedback", "snippet": PAUSED_BATCH,
         "responses": [good], "actions": [], "calls": 1,
         "transport_fault": "Sandbox process could not start.",
         "rejected": True, "rollback": True},
        {"name": "declared_unknown_does_not_request_code_repair", "snippet": PAUSED_BATCH,
         "responses": [declared_unknown], "actions": [], "calls": 1,
         "rejected": True, "rollback": True},
    ]
    if args.scenario:
        unknown = set(args.scenario) - {s["name"] for s in scenarios}
        if unknown:
            parser.error("Unknown scenarios: " + ", ".join(sorted(unknown)))
        scenarios = [s for s in scenarios if s["name"] in args.scenario]
    try:
        # Small pure regressions cover definition-time execution and the
        # bounded diagnostic envelope; the scenarios below exercise delivery
        # and rollback through the real native child.
        from arc3_research.executable_plan_contract import (
            DefinitionContractError, extract_definitions, validate_plan,
        )

        def delivered(code):
            return {"tool_calls": [{"function": {"name": "submit_program",
                    "arguments": json.dumps({"code": code})}}]}

        report["contract_checks"] = []
        immutable_defaults = (
            'def options(a=None, b=True, c=-3, d=0.5, e="x", f=(1, ("x", None))):\n'
            '    return f\n\n' + good)
        entry_default = good.replace("def plan_program(frame):", "def plan_program(frame=None):")
        for name, source, allow, accepted in [
            ("immutable_helper_defaults", immutable_defaults, True, True),
            ("legacy_defaults_remain_rejected", literal_defaults, False, False),
            ("entry_default_remains_rejected", entry_default, True, False),
            ("computed_default_remains_rejected", computed_default, True, False),
            ("mutable_default_remains_rejected", mutable_default, True, False),
        ]:
            try:
                extracted = extract_definitions(delivered(source),
                    expected_tool_name="submit_program", max_code_bytes=12000,
                    allow_literal_defaults=allow)
            except DefinitionContractError as exc:
                assert not accepted, (name, exc)
                details = exc.to_dict()
                assert details["errors"] and details["total_errors"] >= 1
                report["contract_checks"].append({"name": name, "status": "passed",
                                                   "accepted": False, "diagnostics": details})
            else:
                assert accepted, name + " was unexpectedly accepted"
                assert extracted["code"] == source
                report["contract_checks"].append({"name": name, "status": "passed",
                                                   "accepted": True})
        crowded_errors = "\n".join(f"DISALLOWED_{i} = {i}" for i in range(20)) + "\n" + good
        try:
            extract_definitions(delivered(crowded_errors), expected_tool_name="submit_program",
                                max_code_bytes=12000, allow_literal_defaults=True)
        except DefinitionContractError as exc:
            details = exc.to_dict()
            assert len(details["errors"]) == 16, details
            assert details["total_errors"] >= 20, details
            assert details["truncated_count"] == details["total_errors"] - 16, details
            report["contract_checks"].append({"name": "static_diagnostics_are_bounded",
                "status": "passed", "accepted": False, "diagnostics": details})
        else:
            raise AssertionError("Multiple invalid top-level assignments were accepted")
        hidden_side_effect = crowded_errors + '\ndef forbidden_after_many_errors():\n    open("blocked")\n'
        try:
            extract_definitions(delivered(hidden_side_effect), expected_tool_name="submit_program",
                                max_code_bytes=12000, allow_literal_defaults=True)
        except DefinitionContractError as exc:
            details = exc.to_dict()
            assert len(details["errors"]) == 16, details
            assert details["total_errors"] > 20 and details["has_side_effect_rejection"] is True, details
            report["contract_checks"].append({"name": "truncation_does_not_hide_side_effect_rejection",
                "status": "passed", "accepted": False, "diagnostics": details})
        else:
            raise AssertionError("A forbidden call after the diagnostic cap was accepted")

        # A status-aware abstention never supplies an executable action. Ready
        # and completed plans retain the evidence/replacement obligations.
        base_plan = copy.deepcopy(duplicate_wrong_plan)
        base_plan["evidence_pixels"] = [[2, 1, ARC_COLOR_CHARS[2]]]
        synthetic_grid = [[0] * 10 for _ in range(5)]
        synthetic_grid[2][1] = 2
        honest_abstain = {**copy.deepcopy(base_plan), "status": "abstain", "actions": [],
                          "evidence_pixels": [], "replaces": []}
        for name, value, accepted, options, available in [
            ("status_aware_empty_abstain", honest_abstain, True,
             {"status_aware": True, "aggregate_errors": True}, []),
            ("legacy_empty_abstain_still_rejected", honest_abstain, False, {}, ["old_plan"]),
            ("abstain_actions_still_rejected", {**honest_abstain, "actions": [{"action": "RIGHT"}]},
             False, {"status_aware": True, "aggregate_errors": True}, []),
            ("abstain_empty_reason_still_rejected", {**honest_abstain, "reason": " "},
             False, {"status_aware": True, "aggregate_errors": True}, []),
            ("completed_empty_evidence_still_rejected", {**base_plan, "status": "completed",
             "actions": [], "evidence_pixels": []}, False,
             {"status_aware": True, "aggregate_errors": True}, ["old_plan"]),
            ("ready_empty_replaces_still_rejected", {**base_plan, "replaces": []}, False,
             {"status_aware": True, "aggregate_errors": True}, ["old_plan"]),
            ("ready_complete_plan_still_accepted", base_plan, True,
             {"status_aware": True, "aggregate_errors": True}, ["old_plan"]),
        ]:
            validation = validate_plan(value, synthetic_grid, ARC_COLOR_CHARS, ["RIGHT", "LEFT"],
                                       available, **options)
            assert validation["passed"] is accepted, (name, validation)
            if accepted and value["status"] == "abstain":
                assert validation["plan"]["actions"] == []
                assert validation["coverage"]["evidence_pixels"] == 0
            elif not accepted:
                assert "plan" not in validation, (name, validation)
            report["contract_checks"].append({"name": name, "status": "passed",
                                               "accepted": accepted, "validation": validation})
        crowded_plan = {**base_plan, "evidence_pixels": [[2, 1, ARC_COLOR_CHARS[0]]] * 21}
        validation = validate_plan(crowded_plan, synthetic_grid, ARC_COLOR_CHARS, ["RIGHT", "LEFT"],
                                   ["old_plan"], status_aware=True, aggregate_errors=True)
        diagnostics = validation["plan_diagnostics"]
        assert validation["passed"] is False and "plan" not in validation
        assert len(diagnostics["errors"]) == 16
        assert diagnostics["total_errors"] == 21
        assert diagnostics["truncated_count"] == 5
        assert diagnostics["wrong_pixels"] == 21
        assert diagnostics["total_duplicate_coordinates"] == 20
        assert len(diagnostics["differences"]) == len(diagnostics["duplicate_coordinates"]) == 16
        report["contract_checks"].append({"name": "plan_diagnostics_are_bounded_without_accepting_invalid_plan",
            "status": "passed", "accepted": False, "validation": validation})

        # Read the already archived strict-JSON values and exact public frame;
        # never execute the old model sources to make this regression pass.
        prior_dir = ROOT / "experiments/034-v8-analysis"
        prior_path = ROOT / "experiments/034-v9-preparation/v8-plan-fixtures.json"
        prior_review = json.loads(prior_path.read_text())
        report["real_v8_plan_regressions"] = {
            "scope": "Pure validation of archived offline_plan values on exact saved public ASCII; no model program execution or game actions.",
            "fixture_sha256": hashlib.sha256(prior_path.read_bytes()).hexdigest(), "results": []}
        for prior in prior_review["records"]:
            game, event_index = prior["game"], prior["event_index"]
            source_path = prior_dir / "extracted-programs" / f"{game}-{event_index}.py"
            assert hashlib.sha256(source_path.read_bytes()).hexdigest() == prior["source_sha256"]
            observation = prior["current_observation"]
            rows = observation["ascii"].splitlines()
            saved_grid = [[ARC_COLOR_CHARS.index(character) for character in row] for row in rows]
            bindings = prior["available_bindings"]
            value = prior["returned_plan"]
            legal = tool_agent._normalize_valid_actions(prior["valid_actions"])
            validation = validate_plan(value, saved_grid, ARC_COLOR_CHARS, legal, bindings,
                                       status_aware=True, aggregate_errors=True)
            if value["status"] == "abstain":
                assert validation["passed"] and validation["plan"]["actions"] == [], (game, validation)
            else:
                assert game.startswith("su15") and event_index == 1
                assert not validation["passed"] and "plan" not in validation
                diagnostics = validation["plan_diagnostics"]
                assert diagnostics["total_duplicate_coordinates"] == 2
                assert diagnostics["wrong_pixels"] == 6
                assert {"evidence_duplicate_coordinate", "evidence_wrong_pixels"} <= {
                    error["code"] for error in diagnostics["errors"]}
            report["real_v8_plan_regressions"]["results"].append({
                "game": game, "event_index": event_index, "source_sha256": prior["source_sha256"],
                "saved_observation_grid_sha256": observation["grid_sha256"],
                "archived_status": value["status"], "status": "passed", "validation": validation})
        assert len(report["real_v8_plan_regressions"]["results"]) == 4

        def key_occurrences(value, key):
            if type(value) is dict:
                return int(key in value) + sum(key_occurrences(child, key) for child in value.values())
            if type(value) is list:
                return sum(key_occurrences(child, key) for child in value)
            return 0

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
            history_before = copy.deepcopy(agent._history_messages)
            repeat_guard_object = agent._repeat_state_seen
            responses = []
            request_invariants = []
            transport_fault["pending"] = scenario.get("transport_fault")

            def completion(actor, messages, tools, *, timeout, max_tokens, **request_options):
                index = len(responses)
                request_invariants.append({
                    "functions_restored": agent._kept_functions == retained_before,
                    "history_restored": agent._history_messages == history_before,
                    "same_repeat_guard_object": agent._repeat_state_seen is repeat_guard_object,
                    "repeat_guard_contents": sorted(agent._repeat_state_seen),
                })
                responses.append({"index": index, "observed_step": world.step,
                                  "observed_col": world.col, "timeout": timeout,
                                  "max_tokens": max_tokens, "usage": USAGE,
                                  "request_options": request_options,
                                  "last_message": messages[-1]})
                if index >= len(scenario["responses"]):
                    raise AssertionError("Unexpected extra scripted completion request")
                if scenario.get("exhaust_extra_budget_on_response"):
                    # Simulate already consumed auxiliary time without waiting
                    # in the checker. No second generation may start afterward.
                    state.extra_seconds = patch.extra_limit
                message = {"role": "assistant", "content": "", "tool_calls": [
                    {"id": f"cpu-{index}", "type": "function", "function": {
                        "name": tools[0]["function"]["name"], "arguments": json.dumps({"code": scenario["responses"][index]})}}]}
                return tool_agent._ChatCompletionResult(message=message, usage=dict(USAGE),
                                                        finish_reason="tool_calls", served_by="scripted-cpu")

            patch = install_executable_plan(completion=completion, min_remaining_seconds=0,
                auxiliary_reasoning_mode=args.auxiliary_reasoning_mode)
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
                    if scenario.get("after_code"):
                        extra = agent._run_python_tool(state_path, {"code": scenario["after_code"]})
                        case["ordinary_followup"] = _payload(extra.content)
                actions = [a["action"] for call in world.calls for a in call["actions"]]
                statuses = [e.get("status") for e in state.events]
                case.update(actions=actions, action_calls=world.calls, scripted_completions=responses,
                            request_invariants=request_invariants,
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
                assert case["patch"]["patch"] == "034-executable-plan-v9"
                assert case["patch"]["auxiliary_reasoning_mode"] == args.auxiliary_reasoning_mode
                assert patch.request_seconds == 60 and patch.extra_limit == 120
                assert len(responses) <= 2, "Reasoning mode must not add a third request"
                for event in state.events:
                    if event.get("kind") not in {"program_recomputed", "plan_recomputed"}:
                        continue
                    for field in ("returned_plan", "plan_diagnostics"):
                        if field in event:
                            # A repair trigger may reference the preceding
                            # failure; count only this event's own result.
                            own_result = {key: value for key, value in event.items() if key != "trigger"}
                            assert key_occurrences(own_result, field) == 1, (field, event)
                if scenario.get("required_status"):
                    assert scenario["required_status"] in statuses, statuses
                if scenario.get("rejected"):
                    assert payload["executable_plan"]["status"] == "rejected", payload
                if scenario.get("rollback"):
                    assert agent._kept_functions == retained_before, "Candidate function escaped rollback"
                    assert agent._history_messages == history_before, "Branch changed ordinary history"
                    assert agent._repeat_state_seen is repeat_guard_object
                    assert agent._repeat_state_seen == set(request_invariants[0]["repeat_guard_contents"])
                if scenario.get("inactive"):
                    assert state.program is None and not state.repair_used
                if scenario.get("local_status"):
                    assert payload["executable_plan"]["status"] == scenario["local_status"]
                    assert payload["executable_plan"]["environment_success_claim"] is False
                if scenario.get("empty_abstain"):
                    assert not state.repair_used and state.pending is None
                    branch = next(e for e in state.events if e.get("kind") == "program_recomputed")
                    assert branch["returned_plan"]["actions"] == []
                    assert branch["returned_plan"]["evidence_pixels"] == []
                    assert branch["returned_plan"]["replaces"] == []
                    assert branch["plan_diagnostics"]["total_errors"] == 0
                    assert "zero_action_feedback" not in branch
                if scenario.get("ascii_api_prompt"):
                    prompt = responses[0]["last_message"]["content"]
                    assert "frame.ascii is a str" in prompt and "rows = frame.ascii.splitlines()" in prompt
                if "start_col" in scenario:
                    assert payload["executable_plan"]["goal"]["start_col"] == scenario["start_col"]
                    assert responses[0]["observed_col"] == scenario["start_col"]
                if scenario["name"] == "single_helpers_pause_second":
                    trigger = next(e for e in state.events if e.get("kind") == "bootstrap")
                    assert trigger["already_executed_in_snippet"] == 1
                if scenario["name"] == "mismatch_repairs_then_acts":
                    assert responses[1]["observed_step"] == 1
                    assert responses[1]["observed_col"] == 0
                    assert payload["executable_plan"]["followup_repair"]["actual_actions"] == 3
                if scenario["name"] == "short_contract_total_action_limit":
                    assert payload["executable_plan"]["stop_reason"] == "short_plan_action_limit"
                if scenario["name"] == "ordinary_action_after_contract":
                    assert state.events[-1]["kind"] == "unchecked_action"
                if scenario["name"] == "recomputation_failure_keeps_action_accounting":
                    branch = payload["executable_plan"]
                    assert branch["status"] == "execution_failed" and branch["made_progress"]
                    hosts = [e for e in state.events if e["kind"] == "host_plan_execution"]
                    assert len(hosts) == 1 and hosts[0]["actual_actions"] == 1
                    assert hosts[0]["extra_seconds_used"] > 0
                if scenario.get("feedback_stage"):
                    # Check the actual second request, including complete failed
                    # source and concrete zero-action error, not only an event
                    # claiming that a repair was requested.
                    package = json.loads(responses[1]["last_message"]["content"].split(
                        "COMPACT LIVE EVIDENCE PACKAGE:\n", 1)[1])
                    trigger = package["facts"]["trigger"]
                    feedback = trigger["validation_feedback"]
                    assert trigger["kind"] == "repair"
                    assert feedback["stage"] == scenario["feedback_stage"]
                    assert feedback["actual_actions"] == 0 and feedback["observation_unchanged"]
                    assert feedback["before"] == feedback["after"]
                    assert feedback["error"], "Validation error did not reach retry request"
                    assert package["previous_program"] == scenario["feedback_code"]
                    assert "previous_program" not in trigger
                    assert "raw_submission" not in feedback, "Decoded program was duplicated in error feedback"
                    assert responses[1]["observed_step"] == responses[0]["observed_step"] == 0
                    assert request_invariants[1]["functions_restored"]
                    assert request_invariants[1]["history_restored"]
                    assert request_invariants[1]["same_repeat_guard_object"]
                    assert request_invariants[1]["repeat_guard_contents"] == request_invariants[0]["repeat_guard_contents"]
                    assert "followup_repair" in payload["executable_plan"]
                    assert "followup_repair" not in payload["executable_plan"]["followup_repair"]
                    if scenario.get("feedback_error"):
                        assert scenario["feedback_error"] in json.dumps(feedback)
                    if scenario.get("feedback_diagnostic_minimum"):
                        diagnostics = feedback["contract_diagnostics"]
                        errors = diagnostics["errors"]
                        assert len(errors) >= scenario["feedback_diagnostic_minimum"], diagnostics
                        assert len(errors) <= 16, diagnostics
                        assert diagnostics["total_errors"] >= len(errors)
                        assert diagnostics["truncated_count"] == diagnostics["total_errors"] - len(errors)
                        assert len({error["code"] for error in errors}) >= 3, diagnostics
                        assert all(type(error["line"]) is int and error["line"] > 0
                                   and error["code"] and error["message"] for error in errors), diagnostics
                    if scenario.get("feedback_plan_minimum"):
                        diagnostics = feedback["plan_diagnostics"]
                        assert len(diagnostics["errors"]) >= scenario["feedback_plan_minimum"], diagnostics
                        assert len(diagnostics["errors"]) <= 16
                        assert diagnostics["total_errors"] >= len(diagnostics["errors"])
                        assert diagnostics["truncated_count"] == diagnostics["total_errors"] - len(diagnostics["errors"])
                        assert key_occurrences(feedback, "plan_diagnostics") == 1
                        assert key_occurrences(feedback, "returned_plan") == 1
                        assert "validation_errors" not in feedback
                    if scenario.get("returned_plan"):
                        assert feedback["returned_plan"] == scenario["returned_plan"]
                        assert diagnostics["total_duplicate_coordinates"] == 1
                        assert diagnostics["wrong_pixels"] == 2
                        assert {"evidence_duplicate_coordinate", "evidence_wrong_pixels"} <= {
                            error["code"] for error in diagnostics["errors"]}
                    if scenario.get("feedback_success"):
                        followup = payload["executable_plan"]["followup_repair"]
                        assert followup["status"] == "recomputed_plan_executed"
                        assert followup["actual_actions"] == 2
                        assert payload["executable_plan"]["actual_actions"] == 2
                        assert step_executed and made_progress
                if scenario["name"] in {"zero_action_fix_shares_mismatch_repair_quota",
                                        "mismatch_repair_validation_failure_does_not_retry"}:
                    assert payload["executable_plan"]["actual_actions"] == world.step == 1
                    assert state.pending is None
                if scenario["name"] == "mismatch_repair_validation_failure_does_not_retry":
                    followup = payload["executable_plan"]["followup_repair"]
                    assert followup["failure_stage"] == "initial_prediction"
                    assert "followup_repair" not in followup
                if scenario["name"] == "feedback_budget_exhausted_does_not_request":
                    assert state.extra_seconds >= patch.extra_limit
                    assert not any(e.get("usage") for e in state.events if
                                   e.get("trigger", {}).get("kind") == "repair")
                if scenario.get("transport_fault"):
                    assert transport_fault["pending"] is None, "Transport fault was not exercised"
                    assert not state.repair_used
                    assert "followup_repair" not in payload["executable_plan"]
                    branch = next(e for e in state.events if e.get("kind") == "program_recomputed")
                    assert branch["zero_action_feedback"]["reason"] == "native_infrastructure_or_unattributed_failure"
                if scenario["name"] == "declared_unknown_does_not_request_code_repair":
                    assert not state.repair_used
                    assert "followup_repair" not in payload["executable_plan"]
                    branch = next(e for e in state.events if e.get("kind") == "program_recomputed")
                    assert branch["first_prediction_validation"]["declared_unknown"]
                    assert branch["zero_action_feedback"]["reason"] == "declared_unknown"
                for request in responses:
                    assert request["max_tokens"] == 4096
                    assert 0 < request["timeout"] <= 60
                    assert request["request_options"]["enable_thinking"] is (args.auxiliary_reasoning_mode == "low")
                    if args.auxiliary_reasoning_mode == "low":
                        assert request["request_options"]["reasoning_effort"] == "low"
                    else:
                        assert "reasoning_effort" not in request["request_options"]
                    assert request["request_options"]["max_input_tokens"] == 16384
                    assert request["request_options"]["tool_choice_override"]["function"]["name"] == "submit_program"
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
