"""033 bounded extraction repair with independent current-pixel validation.

Diagnostic only: the caller supplies a real recorded-state failure checkpoint.
No automatic online trigger or full world-model correctness is claimed.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import time

from arc3_research.program_repair import _completion, _plain_messages, _payload


REPAIR_PROMPT = """The controller is repairing the observation-to-program input at this
recorded failure. Existing code and its actual outputs are above. Locate the
actual historical code that filled every coordinate in each component's
boundary bounding rectangle. Repair that observation input without discarding
its downstream task: preserve/rebuild the pieces or pattern representation
needed by the existing target/mismatch computation. Returning the full image
alone satisfies only a pixel contract, not that task-specific correction.
Return a
python tool call containing self-contained function definitions, beginning with
extract(frame). No top-level execution, prints, action(), RESET or UNDO.

extract(frame) must return either {"runs": [[row, first_col, last_col_inclusive,
color_character], ...]} or {"pixels": [[row,col,color_character], ...]} covering
EVERY visible frame coordinate exactly once, with its actual color. This is an
exact observation, not a guessed object bounding rectangle or inferred rule.
The controller will call extract(current_frame) itself and independently check
the result against the same current image. Return data rather than printing.
Use the visible frame API. For this bounded extraction only, reading frame.ascii
across the frame is allowed; do not print or display the full board. Ordinary
globals do not survive: extract must take all input through its frame argument.
Also define a self-contained rebuild(frame), when possible, that consumes this
exact extraction and returns the compact task-specific pieces/patterns needed
by your existing reasoning. The controller will actually call rebuild and
deliver its output, but semantic correctness is not established by a generic
pixel check. Do not hardcode a supposedly correct pattern or game solution.

Do not spend time inventing a plan merely to satisfy this request. Optionally,
if your existing reasoning already supports one useful action, also define
propose(frame, extraction) returning {"action": {"action": name, ...},
"expected_pixels": [[row,col,color_character], ...], "reason": explanation}.
This must predict a nonempty concrete visible change before that action; no
action is allowed inside either function. The controller may execute at most
that one action after independent extraction validation. No hidden rules,
future frames or game-specific correct values are provided."""


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _canonical_runs(grid, chars):
    runs = []
    for row, values in enumerate(grid):
        start = 0
        for col in range(1, len(values) + 1):
            if col == len(values) or values[col] != values[start]:
                runs.append([row, start, col - 1, chars[values[start]]])
                start = col
    return runs


def validate_extraction(value, grid, chars):
    """Host compares actual coordinates/colors, independently of model code."""
    height, width = len(grid), len(grid[0])
    actual = {(r, c): chars[grid[r][c]] for r in range(height) for c in range(width)}
    if not isinstance(value, dict) or ("runs" in value) == ("pixels" in value):
        return {"passed": False, "error": "Return exactly one of runs or pixels"}
    kind = "runs" if "runs" in value else "pixels"
    records = value[kind]
    if not isinstance(records, list) or not 1 <= len(records) <= height * width:
        return {"passed": False, "error": "Extraction must be a bounded nonempty record list"}
    claimed, errors = {}, []
    for record in records:
        if not isinstance(record, (list, tuple)) or len(record) != (4 if kind == "runs" else 3):
            errors.append("Malformed coordinate/color record")
            break
        if kind == "runs":
            row, first, last, color = record
        else:
            row, first, color = record
            last = first
        if (any(type(v) is not int for v in (row, first, last))
                or not 0 <= row < height or not 0 <= first <= last < width
                or not isinstance(color, str) or len(color) != 1 or color not in chars):
            errors.append("Invalid coordinate, inclusive endpoint, or color")
            break
        for col in range(first, last + 1):
            if (row, col) in claimed:
                errors.append("Duplicate pixel coverage")
            claimed[(row, col)] = color
    differences = [{"row": r, "col": c, "claimed": color, "observed": actual[(r, c)]}
                   for (r, c), color in claimed.items() if color != actual[(r, c)]]
    missing = len(actual.keys() - claimed.keys())
    passed = not errors and not differences and missing == 0
    return {"passed": passed, "schema": kind, "covered_pixels": len(claimed),
            "expected_pixels": len(actual), "missing_pixels": missing,
            "wrong_pixels": len(differences), "errors": errors[:8],
            "pixel_differences_for_audit_only": differences[:16],
            "claim": "Exact pixels of this current observation only; no game-rule validation"}


def _definition_code(message):
    chosen = next((call for call in message.get("tool_calls", [])
                   if call.get("function", {}).get("name") == "python"), None)
    if chosen is None:
        raise ValueError("No python tool call returned")
    arguments = chosen["function"].get("arguments") or {}
    arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
    code = arguments.get("code", "")
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom)):
            raise ValueError("Return definitions/imports only; controller owns execution")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise ValueError("Decorated functions are outside the retained-source contract")
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "extract" not in names:
        raise ValueError("Missing extract(frame)")
    compile(code, "<controller_repair_candidate>", "exec")
    return code, "propose" in names, "rebuild" in names


def _valid_proposal(value, grid, chars, valid_actions):
    if not isinstance(value, dict) or not isinstance(value.get("reason"), str) or not value["reason"].strip():
        return False, "No explicit action rationale"
    action = value.get("action")
    if not isinstance(action, dict) or action.get("action") not in valid_actions:
        return False, "Action not in current public valid actions"
    if action["action"] in {"RESET", "UNDO"}:
        return False, "Diagnostic first step does not auto-reset or undo"
    if action["action"] == "MOUSE" and (set(action) != {"action", "row", "col"}
            or any(type(action.get(k)) is not int or not 0 <= action[k] < 64 for k in ("row", "col"))):
        return False, "MOUSE requires exact row/col schema"
    if action["action"] != "MOUSE" and set(action) != {"action"}:
        return False, "Unexpected action fields"
    predicted = value.get("expected_pixels")
    if not isinstance(predicted, list) or not 1 <= len(predicted) <= len(grid) * len(grid[0]):
        return False, "Nonempty predicted pixel change required"
    seen, changed = set(), False
    for cell in predicted:
        if not isinstance(cell, (list, tuple)) or len(cell) != 3:
            return False, "Invalid prediction record"
        r, c, color = cell
        if (type(r) is not int or type(c) is not int or not 0 <= r < len(grid)
                or not 0 <= c < len(grid[0]) or not isinstance(color, str)
                or len(color) != 1 or color not in chars or (r, c) in seen):
            return False, "Invalid or duplicate predicted pixel"
        seen.add((r, c))
        changed |= color != chars[grid[r][c]]
    return changed, "accepted_selected_pixel_prediction" if changed else "Vacuous unchanged-pixel prediction"


def run_controller_repair(analyzer, state_path, *, remaining_seconds,
                          should_stop=None, max_calls=2, event_seconds=120):
    """Stage source, call it in native sandbox, validate, and deliver exact data."""
    from inference.agent.runtime_state import load_runtime_state
    from inference.agent.tool_agent import _normalize_valid_actions
    from inference.utils.grid_utils import ARC_COLOR_CHARS
    state_path = Path(state_path)
    frame, _ = load_runtime_state(state_path)
    grid = [list(row) for row in frame.grid]
    started = time.monotonic()
    deadline = started + min(float(event_seconds), float(remaining_seconds))
    old_functions = copy.deepcopy(analyzer._kept_functions)
    old_history = copy.deepcopy(analyzer._history_messages)
    original_callback = analyzer._step_env_callback
    old_timeout = analyzer._python_timeout
    old_result = copy.deepcopy(analyzer._last_action_call_result)
    old_summary = copy.deepcopy(analyzer._last_step_summary)
    original_valid = list(analyzer._current_valid_actions)
    event = {"kind": "controller_extraction_repair", "diagnostic_forced_trigger": True,
        "status": "not_started", "calls": [], "blocked_action_calls": 0,
        "validation_environment_actions": 0, "input_grid_sha256": _hash(grid),
        "level": frame.level, "step": frame.step, "max_event_seconds": event_seconds,
        "old_function_names": sorted(old_functions), "old_functions_sha256": _hash(old_functions),
        "old_history_sha256": _hash(old_history), "controller_action": None,
        "adoption_claim": "Delivery/retention are recorded; later main-model consumption requires trace review"}
    messages = _plain_messages([{"role": "system", "content": analyzer._system_prompt +
        "\nFor this bounded controller extraction repair, full-frame ASCII reading is permitted solely to return exact pixels; do not print full-board text."},
        *old_history, {"role": "user", "content": REPAIR_PROMPT}])
    accepted = False
    proposal = None
    delivered = None

    def blocked(_request):
        event["blocked_action_calls"] += 1
        return {"executed": False, "executed_count": 0, "requested_count": 0,
            "stopped_early": True, "stop_reason": "known_noop",
            "stop_detail": "Controller validation forbids every environment action.",
            "valid_actions": original_valid}

    analyzer._step_env_callback = blocked
    try:
        for index in range(max_calls):
            left = deadline - time.monotonic()
            if left <= 1 or (should_stop and should_stop()):
                event["status"] = "event_deadline"
                break
            analyzer._kept_functions = copy.deepcopy(old_functions)
            call = {"index": index + 1}
            event["calls"].append(call)
            try:
                tools = analyzer._tools(state_path)
                request_messages = analyzer._trim_messages_for_context(messages, tools=tools)
                response = _completion(analyzer, request_messages, tools,
                    timeout=min(60, left), max_tokens=4096)
                analyzer._accumulate_usage_tokens(response.usage)
                call.update(usage=response.usage, assistant_message=response.message,
                            finish_reason=response.finish_reason)
                code, has_proposal, has_rebuild = _definition_code(response.message or {})
                call["code"] = code
                eval_code = code + "\n_controller_extraction = extract(current_frame)\nresult = {'extraction': _controller_extraction}"
                if has_proposal:
                    eval_code += "\nresult['proposal'] = propose(current_frame, _controller_extraction)"
                if has_rebuild:
                    eval_code += "\nresult['task_rebuild'] = rebuild(current_frame)"
                before_blocked = event["blocked_action_calls"]
                analyzer._python_timeout = max(1, min(old_timeout, deadline - time.monotonic()))
                dispatch = analyzer._dispatch_tool(state_path, "python", {"code": eval_code})
                payload = _payload(dispatch.content)
                call["actual_tool_output"] = payload
                if dispatch.step_executed or event["blocked_action_calls"] != before_blocked:
                    raise ValueError("Candidate attempted an environment action during validation")
                if payload.get("error") or not isinstance(payload.get("result"), dict):
                    raise ValueError("Candidate failed or printed instead of returning structured extraction")
                validation = validate_extraction(payload["result"].get("extraction"), grid, ARC_COLOR_CHARS)
                call["validation"] = validation
                if not validation["passed"]:
                    event["status"] = "rejected_pixels"
                    feedback = {k: v for k, v in validation.items() if k != "pixel_differences_for_audit_only"}
                    messages.extend([{"role": "assistant", "content": code},
                        {"role": "user", "content": "Independent current-image validation rejected the extraction: " +
                         json.dumps(feedback) + ". Return corrected self-contained definitions. No actions."}])
                    continue
                if "extract" not in analyzer._kept_functions:
                    raise ValueError("extract was not retained as self-contained source")
                # Actually invoke the retained extractor again, not merely retain
                # an optional function or trust the model's printed verification.
                delivery = analyzer._dispatch_tool(state_path, "python", {"code": "result = extract(current_frame)"})
                delivery_payload = _payload(delivery.content)
                call["retained_extract_invocation"] = delivery_payload
                second = validate_extraction(delivery_payload.get("result"), grid, ARC_COLOR_CHARS)
                call["retained_extract_validation"] = second
                if delivery.step_executed or event["blocked_action_calls"] != before_blocked or not second["passed"]:
                    raise ValueError("Retained extract invocation failed independent validation")
                current, _ = load_runtime_state(state_path)
                if _hash([list(row) for row in current.grid]) != event["input_grid_sha256"] or current.level != frame.level:
                    raise ValueError("Observation changed during zero-action validation")
                delivered = {"schema": "exact_current_pixel_runs_v1", "shape": [len(grid), len(grid[0])],
                    "level": frame.level, "step": frame.step,
                    "runs": _canonical_runs(grid, ARC_COLOR_CHARS),
                    "source": "Your extract(current_frame) was actually called twice; both outputs match every current pixel",
                    "validity": "This observation only; exact pixels do not establish the game's rules"}
                proposal = payload["result"].get("proposal")
                accepted = True
                event["status"] = "full_frame_pixel_contract_passed"
                event["accepted_code_sha256"] = hashlib.sha256(code.encode()).hexdigest()
                event["delivered_extraction"] = delivered
                event["task_rebuild_supplied"] = has_rebuild
                event["task_rebuild_output"] = payload["result"].get("task_rebuild")
                event["task_semantics_status"] = "Not automatically verified; inspect rebuilt pieces/patterns, target computation and actual subsequent actions"
                if has_rebuild:
                    delivered["task_rebuild_model_output_unverified"] = payload["result"].get("task_rebuild")
                break
            except Exception as exc:
                call["error"] = f"{type(exc).__name__}: {exc}"
                event["status"] = "request_or_execution_error"
                if deadline - time.monotonic() > 1:
                    messages.append({"role": "user", "content": "Controller could not accept the definitions: " +
                                     str(exc) + ". Return one small extract(frame); do not print or act."})
    finally:
        analyzer._step_env_callback = original_callback
        analyzer._python_timeout = old_timeout
        analyzer._last_action_call_result = old_result
        analyzer._last_step_summary = old_summary
        analyzer._current_valid_actions = original_valid
        analyzer._history_messages = copy.deepcopy(old_history)
        if not accepted:
            analyzer._kept_functions = copy.deepcopy(old_functions)
            analyzer._history_messages.append({"role": "user", "content":
                "A bounded controller extraction repair did not produce an independently validated replacement. "
                "No environment action was executed during validation. Your original functions and prior history were preserved; continue from the current observation."})
        else:
            message = "Controller full-frame pixel contract passed. The following exact structured pixel input was independently checked against the current visible frame and is supplied directly for your next computation. This does NOT establish that your old pieces/pattern/target computation is repaired or that a game rule is correct. Rebuild that task-specific extraction rather than filling object bounding rectangles; any task_rebuild_model_output_unverified is only your executed output, not a semantic verdict. Retained extract(frame) and any rebuild(frame) are callable.\n" + json.dumps(delivered, separators=(",", ":"))
            analyzer._history_messages.append({"role": "user", "content": message})
            event["delivery_message_sha256"] = hashlib.sha256(message.encode()).hexdigest()
            event["delivery_message_chars"] = len(message)
            event["status"] = "full_frame_pixel_contract_passed_and_delivered"
        event["functions_after"] = sorted(analyzer._kept_functions)
        event["failed_functions_rolled_back"] = not accepted and analyzer._kept_functions == old_functions
        event["original_history_prefix_preserved"] = analyzer._history_messages[:len(old_history)] == old_history

    if accepted and proposal is not None:
        valid, reason = _valid_proposal(proposal, grid, ARC_COLOR_CHARS, _normalize_valid_actions(original_valid))
        event["proposal"] = {"value": proposal, "valid": valid, "reason": reason}
        if valid and not (should_stop and should_stop()) and time.monotonic() < deadline:
            frozen = copy.deepcopy(proposal)
            try:
                action_code = "result = action(" + repr([frozen["action"]]) + ")"
                dispatch = analyzer._dispatch_tool(state_path, "python", {"code": action_code})
                after, _ = load_runtime_state(state_path)
                result = copy.deepcopy(analyzer._last_action_call_result)
                boundary = any(result.get(k) for k in ("level_completed", "game_over", "run_complete", "done")) or after.level != frame.level
                comparison = None if boundary or not dispatch.step_executed else [
                    {"row": r, "col": c, "expected": color, "observed": ARC_COLOR_CHARS[after.grid[r][c]]}
                    for r, c, color in frozen["expected_pixels"] if ARC_COLOR_CHARS[after.grid[r][c]] != color]
                event["controller_action"] = {"action": frozen["action"], "prediction_before_execution": frozen["expected_pixels"],
                    "actual_tool_output": _payload(dispatch.content), "step_executed": dispatch.step_executed,
                    "public_result": result, "boundary": boundary, "mismatches": comparison,
                    "claim": "At most one real action; comparison covers only declared pixels"}
            except Exception as exc:
                event["controller_action"] = {"error": f"{type(exc).__name__}: {exc}",
                                              "outcome": "unknown_no_retry"}
            analyzer._history_messages.append({"role": "user", "content":
                "Controller executed at most the independently accepted proposal's first action. Previous exact pixels belong to the pre-action observation. Re-read current_frame before continuing. Actual result: " +
                json.dumps(event["controller_action"], ensure_ascii=False)})
    event["elapsed_seconds"] = time.monotonic() - started
    event_path = state_path.with_name(state_path.stem + "_controller-repair.json")
    event_path.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n")
    return event
