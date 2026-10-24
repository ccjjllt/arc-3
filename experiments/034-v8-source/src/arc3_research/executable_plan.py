"""034: bounded repair of a live program, host recomputation and checked actions.

Installs in memory on the frozen actor. No game names, answers or hidden state.
A native snippet is ended before a queued batch (or its second action call).
One bounded model request builds a current-frame plan and predictor. The host
executes that plan, freezes predictions before each real action, and sends a
structured counterexample or zero-action validation error to one subsequent
bounded repair request, sharing the same one-repair quota. Unknown
checks stop the snippet; an invalid contract can be abandoned for exploration.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import inspect
import json
from pathlib import Path
import threading
import time
import traceback
from typing import Any

from arc3_research.program_repair import _completion, _payload, _remaining
from arc3_research.executable_plan_context import prepare_compact_context, delivery_tool_schema
from arc3_research.object_evidence import object_evidence
from arc3_research.executable_plan_contract import (
    DefinitionContractError, binding_names, compare_prediction, extract_definitions,
    validate_plan, validate_prediction,
)


PROMPT = """Deliver a SMALL executable program now using one submit_program tool call.
Implement ONE current decision and its related prediction first, not a large
general solver. Deliver complete source within 12000 UTF-8 bytes and this
4096-token response. There is no line-count limit; do not compress line breaks
to satisfy one. Keep constants and parameters inside functions, never at top level.
The host paused a real action sequence. Repair its relevant input/rule or
construct a small current decision program if no usable planner was retained.
Reuse existing rule/search when evidence supports it; revise a contradicted
rule instead of repeating old coordinates. Return self-contained function
definitions and allowed computational imports only, with two entry points:

plan_program(frame) -> {"status": "ready" | "completed" | "abstain",
 "goal": nonempty local target description/data,
 "actions": [model-facing action dicts, at most 3; empty unless ready],
 "evidence_pixels": [[row,col,color_character], ...],
 "replaces": [names from the paused code or retained functions], "reason": str}
predict(frame, action) -> {"mode": "change" | "noop", "action": action,
 "object_pixels": [[row,col,CURRENT color], ...],
 "target_pixels": [[row,col,CURRENT color], ...],
 "expected_pixels": [[row,col,EXPECTED color], ...],
 "precondition": "why this action has this effect or is blocked",
 "scope": "which task object and observable consequence this checks"}
If no relevant prediction is possible, return {"mode":"unknown","reason":str}.

Read frame.ascii, shape, level and step to RECOMPUTE current objects, target and
actions. frame.recent_transitions is refreshed on EVERY call: a tuple of recent
public transitions with action, before_frame, after_frame and result attributes.
frame.valid_actions and frame.last_action_result are current public facts.
Unknown historical state is not a fact; if essential state cannot be recovered,
abstain or propose only ONE useful action. completed refers only to your local
target, never a claim of environment success. Do not hardcode a moving target
as current_position plus a fixed distance on every call: express a meaningful
task target computed from the current board and known facts.

Use frame.object_evidence for exact current same-color connected components,
not a bounding box joining every pixel of one color or a grid with an assumed
origin. The supplied component catalogue is recomputed from this frame; IDs
are not stable across calls. Components are geometric observations, not proved
objects or roles. A task object may comprise several components. In your goal
state the selected component instances, their hypothesized roles and which
actual transition supports that choice. Distinguish an active piece, target,
legend, counter and control by evidence, not color or a fixed screen cutoff.
An unchanged component is not automatically UI; a UI control can be actionable.
Recent effect counts refer to screen coordinates, not tracked object identity
or causation. A level/shape boundary gives no action support for new-level
objects. If uncertain, choose ONE action that distinguishes the competing
roles/rules and predicts its relevant consequence, or abstain.
For each object/effect you claim, predict its complete relevant footprint
(expand rectangular bbox or row runs), not a few convenient sampled pixels.
Do not claim "nothing else changes" unless your projection checks that claim.

The host executes at most THREE actions for this contract, recalculating the
plan from the real new frame before every next action. Predictions are frozen
BEFORE action, cover BOTH declared object and target pixels and no undeclared
pixels. A noop must explain a task-relevant obstruction/precondition, not just
unchanged distant background. Pixel agreement does not prove your rule correct.
MOUSE uses row/col; other actions contain only action. No RESET/UNDO, calls to
action(), prints or top-level execution. No decorators, annotations, global or
nonlocal. Helper defaults may use only immutable literal
values, such as r0=10 or a tuple of literals; no computed or mutable defaults.
The two entry points must have the exact signatures above, without defaults.
Computational imports math, collections,
itertools, heapq, numpy are supported. Globals do not persist: keep parameters
inside functions, reuse supplied helpers and rebind layout from this frame.
Do not copy every pixel as a replacement model. No explanation outside the
single submit_program tool call. Keep the program short enough to finish this response.
If validation_feedback is supplied, it records a real host rejection before any
action. Correct all reported errors together in the supplied previous_program;
contract_diagnostics lists the statically discovered failures, with any omitted
error count. Do not merely fix the first error or claim the rejected code ran
or that its rules were confirmed. This shares the
single repair opportunity with a later real-action counterexample.
"""

_DELIVERY_MAX_NONEMPTY_LINES = None
_DELIVERY_MAX_CODE_BYTES = 12000


class _ValidationSideEffect(ValueError):
    """An attempted environment action is not an automatic repair opportunity."""


class _NativeEvaluationError(ValueError):
    def __init__(self, payload):
        self.payload = copy.deepcopy(payload)
        super().__init__("program did not return result: " + str(payload.get("error") or payload)[:1200])


def _submitted_source(message):
    """Copy raw delivered source for feedback, without accepting or repairing it."""
    try:
        calls = message["tool_calls"]
        if len(calls) != 1:
            return None
        arguments = calls[0]["function"]["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        code = arguments.get("code")
        return code if isinstance(code, str) else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _delivery_source_metadata(code):
    metadata = {"max_nonempty_lines": _DELIVERY_MAX_NONEMPTY_LINES,
                "max_code_bytes": _DELIVERY_MAX_CODE_BYTES,
                "source_available": isinstance(code, str)}
    if isinstance(code, str):
        metadata["nonempty_lines"] = sum(bool(line.strip()) for line in code.splitlines())
        try:
            encoded = code.encode("utf-8")
            metadata.update(code_bytes=len(encoded), code_sha256=hashlib.sha256(encoded).hexdigest())
        except UnicodeError as exc:
            metadata.update(code_bytes=None, code_sha256=None, utf8_error=str(exc))
    return metadata


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _bindings(code: str, functions: dict) -> list[str]:
    names = set(functions)
    try:
        names.update(binding_names(code))
    except ValueError:
        pass
    return sorted(names)


def _bootstrap(source: str) -> str:
    # The same pure geometry helper is used by the request and native child.
    # It is infrastructure, never retained model code or a game-role oracle.
    helper = inspect.getsource(object_evidence)
    frame_anchor = "class FrameView:\n"
    if source.count(frame_anchor) != 1:
        raise RuntimeError("034 object-evidence FrameView anchor differs")
    source = source.replace(frame_anchor, helper + "\n" + frame_anchor, 1)
    property_anchor = "    @property\n    def segmentation(self):\n"
    object_property = '''    @property
    def object_evidence(self):
        records = [{"action": t.action,
                    "before_ascii": t.before_frame.ascii,
                    "after_ascii": t.after_frame.ascii,
                    "before_level": t.before_frame.level,
                    "after_level": t.after_frame.level}
                   for t in getattr(self, "recent_transitions", ())[-2:]
                   if t.before_frame is not None and t.after_frame is not None]
        return object_evidence(self.ascii, records)

'''
    if source.count(property_anchor) != 1:
        raise RuntimeError("034 object-evidence property anchor differs")
    source = source.replace(property_anchor, object_property + property_anchor, 1)
    additions = [
        ('    class KnownNoOpActionError(BaseException):\n',
         '    class ExecutablePlanInterrupted(BaseException):\n        pass\n\n'
         '    class KnownNoOpActionError(BaseException):\n'),
        ('        _refresh_state(reply.get("state") or {})\n',
         '        _refresh_state(reply.get("state") or {})\n'
         '        if action_result.get("executable_plan_interrupt"):\n'
         '            raise ExecutablePlanInterrupted(str(action_result.get("stop_detail") or "Plan stopped; inspect the live state."))\n'),
        ('    except (\n        KnownNoOpActionError,\n',
         '    except (\n        ExecutablePlanInterrupted,\n        KnownNoOpActionError,\n'),
        ('        runtime_globals["current_frame"] = current_frame\n',
         '        if current_frame is not None:\n'
         '            current_frame.recent_transitions = tuple(transitions[-4:])\n'
         '            current_frame.valid_actions = tuple(str(a) for a in state_payload.get("valid_actions", []))\n'
         '            current_frame.last_action_result = dict(action_result)\n'
         '        runtime_globals["current_frame"] = current_frame\n'),
    ]
    for old, new in additions:
        if source.count(old) != 1:
            raise RuntimeError("034 sandbox anchor differs from the frozen runtime")
        source = source.replace(old, new, 1)
    compile(source, "<034-child>", "exec")
    return source


@dataclass
class _State:
    path: Path
    bootstrap_used: bool = False
    repair_used: bool = False
    extra_seconds: float = 0.0
    observation_serial: int = 0
    attempt_event: int = 0
    level: int | None = None
    program: str | None = None
    program_hash: str | None = None
    source_code: str = ""
    source_bindings: list[str] = field(default_factory=list)
    latest_messages: list = field(default_factory=list)
    should_stop: Any = None
    events: list[dict] = field(default_factory=list)
    pending: dict | None = None
    prediction_support: int = 0
    in_branch: bool = False
    program_bindings: list[str] = field(default_factory=list)


class ExecutablePlanPatch:
    def __init__(self, *, min_remaining_seconds=180, max_check_seconds=5,
                 request_seconds=60, extra_seconds=120, completion=None):
        from inference.agent import tool_agent, python_tool_sandbox
        from inference.utils.grid_utils import ARC_COLOR_CHARS
        if getattr(tool_agent.ToolAgent, "_executable_plan_installed", False):
            raise RuntimeError("034 is already installed")
        self.module = tool_agent
        self.chars = ARC_COLOR_CHARS
        self.sandbox_module = python_tool_sandbox
        self.agent_class = tool_agent.ToolAgent
        self.original_python = self.agent_class._run_python_tool
        self.original_analyze = self.agent_class.analyze
        self.original_chat = self.agent_class._chat_completion
        self.original_guard = self.agent_class._action_guard_hook
        self.original_sandbox = tool_agent.run_sandboxed_python
        self.original_bootstrap = python_tool_sandbox._SANDBOX_BOOTSTRAP
        self.tls = threading.local()
        self.lock = threading.Lock()
        self.states: list[_State] = []
        self.min_remaining = float(min_remaining_seconds)
        self.check_seconds = float(max_check_seconds)
        self.request_seconds = float(request_seconds)
        self.extra_limit = float(extra_seconds)
        self.completion = completion or _completion

        def analyze(agent, state_path, *args, **kwargs):
            agent._ensure_session(state_path)
            state = self.state(agent, state_path)
            state.should_stop = kwargs.get("should_stop")
            return self.original_analyze(agent, state_path, *args, **kwargs)

        def chat(agent, messages, **kwargs):
            result = self.original_chat(agent, messages, **kwargs)
            state = getattr(agent, "_executable_plan_state", None)
            if state is not None and not state.in_branch:
                state.latest_messages = copy.deepcopy(messages) + [{"role": "assistant", **copy.deepcopy(result.message or {})}]
            return result

        def python(agent, state_path, arguments):
            agent._ensure_session(state_path)
            state = self.state(agent, state_path)
            state.source_code = str(arguments.get("code", ""))
            state.source_bindings = _bindings(state.source_code, getattr(agent, "_kept_functions", {}))
            context = {"agent": agent, "state": state, "calls": 0,
                       "executed": 0, "validation": False, "host_plan": False}
            previous = getattr(self.tls, "context", None)
            self.tls.context = context
            start_events = len(state.events)
            try:
                result = self.original_python(agent, state_path, arguments)
                if state.pending is not None:
                    trigger, state.pending = state.pending, None
                    branch = self.run_branch(agent, state, trigger)
                    payload = _payload(result.content)
                    payload["executable_plan"] = branch
                    if branch.get("actual_actions", 0):
                        payload.pop("error", None)
                        payload["paused_snippet_status"] = "old_suffix_abandoned; recomputed program actually executed"
                    result = self.module._ToolDispatchResult(
                        json.dumps(payload, ensure_ascii=False),
                        step_executed=result.step_executed or bool(branch.get("actual_actions")),
                        made_progress=result.made_progress or bool(branch.get("made_progress")))
                elif len(state.events) > start_events:
                    payload = _payload(result.content)
                    payload["executable_plan_checks"] = [
                        {k: e[k] for k in ("kind", "status", "program_hash", "action", "actual_actions", "boundary") if k in e}
                        for e in state.events[start_events:][-12:]]
                    result = self.module._ToolDispatchResult(
                        json.dumps(payload, ensure_ascii=False),
                        step_executed=result.step_executed, made_progress=result.made_progress)
                return result
            finally:
                self.tls.context = previous

        def sandbox_call(**kwargs):
            context = getattr(self.tls, "context", None)
            if context is not None and kwargs.get("action_handler") is not None:
                original_handler = kwargs["action_handler"]
                context["reply_state"] = copy.deepcopy(kwargs.get("initial_state", {}))
                kwargs["action_handler"] = lambda actions, **kw: self.actions(
                    context, original_handler, actions, **kw)
            return self.original_sandbox(**kwargs)

        def guard(agent, grid, action_name, action_data, level=None, remaining=None):
            context = getattr(self.tls, "context", None)
            if context is not None and context.get("agent") is agent and context.get("guard_remaining"):
                remaining = context["guard_remaining"]
                agent._guard_death_override_batch = context.get("death_override", False)
            result = self.original_guard(agent, grid, action_name, action_data, level, remaining)
            if context is not None and context.get("agent") is agent:
                context["death_override"] = agent._guard_death_override_batch
            return result

        self.analyze, self.chat, self.python = analyze, chat, python
        self.sandbox_call, self.guard = sandbox_call, guard
        python_tool_sandbox._SANDBOX_BOOTSTRAP = _bootstrap(self.original_bootstrap)
        tool_agent.run_sandboxed_python = sandbox_call
        self.agent_class._run_python_tool = python
        self.agent_class.analyze = analyze
        self.agent_class._chat_completion = chat
        self.agent_class._action_guard_hook = guard
        self.agent_class._executable_plan_installed = True

    def state(self, agent, path):
        path = Path(path)
        state = getattr(agent, "_executable_plan_state", None)
        if state is None or state.path != path:
            state = _State(path=path)
            agent._executable_plan_state = state
            with self.lock:
                self.states.append(state)
        return state

    def stopped(self, state):
        return bool(state.should_stop and state.should_stop())

    def remaining(self, agent, state):
        left = _remaining(agent)
        return float("inf") if left is None else max(0.0, float(left))

    def event(self, state, value):
        entry = {"observation_id": state.observation_serial,
                 "attempt_event": state.attempt_event, "level": state.level,
                 "program_hash": state.program_hash, **value}
        state.events.append(entry)
        path = state.path.with_name(state.path.stem + "_executable-plan.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=True, allow_nan=False) + "\n")
        return entry

    def current(self, state):
        from inference.agent.runtime_state import load_runtime_state
        frame, history = load_runtime_state(state.path)
        if state.level is not None and frame.level != state.level:
            self.release(state, "level_changed")
        state.level = frame.level
        return frame, history

    def release(self, state, reason):
        if state.program is not None:
            self.event(state, {"kind": "contract_released", "status": reason,
                               "matched_actions": state.prediction_support})
        state.program = None
        state.program_hash = None
        state.program_bindings = []
        state.prediction_support = 0

    def transition_evidence(self, before, after):
        changed = []
        if before.shape == after.shape:
            for row, values in enumerate(before.grid):
                for col, color in enumerate(values):
                    if color != after.grid[row][col]:
                        changed.append([row, col, self.chars[color], self.chars[after.grid[row][col]]])
        return {"before": {"step": before.step, "level": before.level, "ascii": before.ascii},
                "after": {"step": after.step, "level": after.level, "ascii": after.ascii},
                "shape_changed": before.shape != after.shape,
                "changed_pixels": changed, "changed_pixel_count": len(changed)}

    def interrupt(self, context, status, detail):
        agent, state = context["agent"], context["state"]
        context["halted"] = True
        result = {"executed": False, "executed_count": 0, "requested_count": 0,
                  "stopped_early": True, "stop_reason": "executable_plan",
                  "stop_detail": detail, "executable_plan_interrupt": True,
                  "plan_status": status, "valid_actions": list(agent._current_valid_actions)}
        return {"action_result": result, "state": copy.deepcopy(context["reply_state"])}

    def can_branch(self, agent, state):
        return (not self.stopped(state) and state.extra_seconds < self.extra_limit
                and self.remaining(agent, state) >= self.min_remaining)

    def evaluate(self, agent, state, code, *, commit=False, deadline=None):
        """Native sandbox with all environment actions blocked and state restored."""
        old_functions = copy.deepcopy(agent._kept_functions)
        old_result = copy.deepcopy(agent._last_action_call_result)
        old_summary = copy.deepcopy(agent._last_step_summary)
        old_timeout = agent._python_timeout
        old_repeat = set(agent._repeat_state_seen)
        old_context = getattr(self.tls, "context", None)
        context = {"agent": agent, "state": state, "validation": True,
                   "calls": 0, "executed": 0, "blocked": 0}
        self.tls.context = context
        before, _ = self.current(state)
        try:
            timeout = min(old_timeout, self.check_seconds, self.remaining(agent, state),
                          float("inf") if deadline is None else deadline - time.monotonic())
            if timeout < 1 or self.stopped(state):
                raise TimeoutError("not enough remaining time to start a native check")
            agent._python_timeout = timeout
            dispatch = self.original_python(agent, state.path, {"code": code})
            payload = _payload(dispatch.content)
            after, _ = self.current(state)
            if (context["blocked"] or dispatch.step_executed or after.level != before.level
                    or after.step != before.step or _hash(after.grid) != _hash(before.grid)):
                raise _ValidationSideEffect("zero-action validation attempted a side effect or changed the observation")
            if payload.get("error") or "result" not in payload:
                raise _NativeEvaluationError(payload)
            if not commit:
                agent._kept_functions = old_functions
            return payload["result"]
        except BaseException:
            agent._kept_functions = old_functions
            raise
        finally:
            agent._last_action_call_result = old_result
            agent._last_step_summary = old_summary
            agent._python_timeout = old_timeout
            agent._repeat_state_seen.clear()
            agent._repeat_state_seen.update(old_repeat)
            self.tls.context = old_context

    def actions(self, context, execute, actions, *, stale_after=None):
        agent, state = context["agent"], context["state"]
        if context.get("validation"):
            context["blocked"] += 1
            return self.interrupt(context, "validation_action_refused", "Contract computation must not execute actions")
        if context.get("halted"):
            return self.interrupt(context, "suffix_already_stopped", "This Python snippet has already been stopped; no further actions allowed")
        normalized = agent._normalize_python_actions(actions)
        context["calls"] += 1
        frame, _ = self.current(state)
        if not context.get("host_plan") and state.program is not None:
            self.release(state, "ordinary_action_outside_short_plan")
        if (not context.get("host_plan") and state.program is None and not state.bootstrap_used
                and state.source_bindings and normalized
                and (len(normalized) > 1 or context["calls"] > 1)
                and self.can_branch(agent, state)):
            state.bootstrap_used = True
            state.pending = {"kind": "bootstrap", "source_code": state.source_code,
                             "proposed_actions": normalized,
                             "already_executed_in_snippet": context["executed"],
                             "before_grid_sha256": _hash(frame.grid)}
            self.event(state, {"kind": "contract_trigger", **state.pending})
            return self.interrupt(context, "contract_requested", "Old suffix stopped; host will recompute the current program")
        if state.program is None:
            if context.get("host_plan"):
                return self.interrupt(context, "inactive_contract", "Short-plan contract is no longer active")
            reply = execute(actions, stale_after=stale_after)
            context["reply_state"] = copy.deepcopy(reply.get("state", context["reply_state"]))
            outcome = reply.get("action_result", {})
            count = int(outcome.get("executed_count") or bool(outcome.get("executed")))
            context["executed"] += count
            state.observation_serial += count
            if any(outcome.get(k) for k in ("game_over", "level_completed", "run_complete", "done")):
                self.release(state, "ordinary_boundary")
                state.attempt_event += int(bool(outcome.get("game_over")))
            self.event(state, {"kind": "unchecked_action", "status": "unverified",
                               "actions": normalized, "actual_actions": count})
            return reply

        replies, animations = [], []
        context["death_override"] = False
        for index, action in enumerate(normalized):
            if (self.stopped(state) or self.remaining(agent, state) <= 0
                    or time.monotonic() >= context.get("deadline", float("inf"))):
                return self.interrupt(context, "deadline", "Shared deadline reached; suffix stopped") if not replies else self.aggregate(context, replies, len(normalized), interrupt="deadline")
            before, _ = self.current(state)
            try:
                predicted = self.evaluate(agent, state, state.program +
                    "\nresult = predict(current_frame, " + repr(action) + ")",
                    deadline=context.get("deadline"))
                valid = validate_prediction(predicted, before.grid, self.chars, expected_action=action)
                if not valid["passed"]:
                    raise ValueError(str(valid.get("errors")))
                frozen = copy.deepcopy(valid["prediction"])
            except Exception as exc:
                problem = {"kind": "prediction_unavailable", "status": "unknown",
                           "action": action, "error": f"{type(exc).__name__}: {exc}"}
                self.invalidate(state, problem, allow_repair=False)
                return self.interrupt(context, "unknown", str(problem)) if not replies else self.aggregate(context, replies, len(normalized), interrupt="unknown")
            if time.monotonic() >= context.get("deadline", float("inf")) or self.stopped(state):
                return self.interrupt(context, "deadline", "Extra-processing deadline reached before action") if not replies else self.aggregate(context, replies, len(normalized), interrupt="deadline")
            from inference.agent.action_names import to_engine_action
            context["guard_remaining"] = [(to_engine_action(a["action"]),
                {k: v for k, v in a.items() if k != "action"}) for a in normalized[index:]]
            self.event(state, {"kind": "prediction_frozen", "action": action,
                               "before": {"step": before.step, "grid_sha256": _hash(before.grid)},
                               "expected": frozen, "evidence": "prediction before real action, unproven dynamics"})
            reply = execute([action], stale_after=stale_after if index == 0 else None)
            context["reply_state"] = copy.deepcopy(reply.get("state", context["reply_state"]))
            replies.append(reply)
            outcome = reply.get("action_result", {})
            count = int(outcome.get("executed_count") or bool(outcome.get("executed")))
            context["executed"] += count
            state.observation_serial += count
            animations.extend(getattr(agent, "_last_animation_chain", []) or [])
            context["animations"] = animations
            after, _ = self.current(state)
            boundary = next((k for k in ("level_completed", "game_over", "run_complete", "done") if outcome.get(k)), None)
            if after.level != before.level:
                boundary = boundary or "level_changed"
            if boundary:
                self.event(state, {"kind": "checked_action", "status": "boundary", "boundary": boundary,
                                   "action": action, "actual_actions": count,
                                   "expected": frozen, "transition": self.transition_evidence(before, after)})
                self.release(state, boundary)
                state.attempt_event += int(bool(outcome.get("game_over")))
                break
            if not count:
                self.event(state, {"kind": "checked_action", "status": "not_executed", "outcome": outcome})
                break
            comparison = compare_prediction(frozen, after.grid, self.chars)
            self.event(state, {"kind": "checked_action", "action": action,
                               "expected": frozen, "observed": comparison,
                               "status": comparison["status"], "actual_actions": count,
                               "semantic_relevance_verified": False,
                               "transition": self.transition_evidence(before, after)})
            if comparison["status"] != "match":
                self.invalidate(state, {"kind": "counterexample", "status": comparison["status"],
                    "action": action, "expected": frozen, "observed": comparison},
                    allow_repair=comparison["status"] == "mismatch")
                return self.aggregate(context, replies, len(normalized), interrupt=comparison["status"])
            state.prediction_support += 1
        agent._last_animation_chain = animations
        return self.aggregate(context, replies, len(normalized)) if replies else self.interrupt(context, "empty", "No actions to execute")

    def invalidate(self, state, problem, *, allow_repair=True):
        source_hash = state.program_hash
        previous_program = state.program
        self.event(state, {**problem, "invalidated_program_hash": source_hash})
        self.release(state, problem.get("status", "invalidated"))
        if allow_repair and not state.repair_used:
            state.pending = {"kind": "repair", "counterexample": problem,
                             "source_code": state.source_code, "previous_program_hash": source_hash,
                             "previous_program": previous_program}

    def aggregate(self, context, replies, requested, interrupt=None):
        reply = copy.deepcopy(replies[-1])
        outcomes = [r["action_result"] for r in replies]
        result = reply["action_result"]
        count = sum(int(x.get("executed_count") or bool(x.get("executed"))) for x in outcomes)
        result.update(executed=bool(count), executed_count=count, requested_count=requested,
                      stopped_early=bool(interrupt) or count < requested)
        for key in ("board_changed", "gameplay_changed", "game_over", "level_completed", "run_complete", "done"):
            result[key] = any(bool(x.get(key)) for x in outcomes)
        result["executed_actions"] = [a for x in outcomes for a in (x.get("executed_actions") or [])]
        if interrupt:
            context["halted"] = True
            result.update(executable_plan_interrupt=True, stop_reason="executable_plan",
                          stop_detail=f"034 {interrupt}; remaining code and plan suffix stopped.")
        context["agent"]._last_action_call_result = copy.deepcopy(result)
        if isinstance(reply.get("state"), dict):
            reply["state"]["last_action_call_result"] = copy.deepcopy(result)
        if "animations" in context:
            context["agent"]._last_animation_chain = context["animations"]
        context["reply_state"] = copy.deepcopy(reply.get("state", context["reply_state"]))
        context["guard_remaining"] = None
        return reply

    def queue_validation_feedback(self, agent, state, trigger, context, event,
                                  before, exc, deadline):
        """Reuse the one repair slot only for an unchanged, zero-action failure.

        A rejected artifact is never executed or repaired by the host. The next
        bounded model call receives its original source and actual host error.
        Side-effect refusals and exhausted infrastructure budgets stop here.
        """
        summary = {"eligible": False, "queued": False, "stage": event["stage"],
                   "actual_actions": context["executed"], "observation_unchanged": False}
        event["zero_action_feedback"] = summary
        if event["stage"] not in {"extract", "plan_validation", "initial_prediction"}:
            summary["reason"] = "not_an_artifact_validation_failure"
            return
        if context["executed"]:
            summary["reason"] = "real_actions_already_executed"
            return
        if (event.get("first_prediction_validation") or {}).get("declared_unknown"):
            summary["reason"] = "declared_unknown"
            return
        after, _ = self.current(state)
        def identity(frame):
            return {"level": frame.level, "step": frame.step, "grid_sha256": _hash(frame.grid)}
        before_id, after_id = identity(before), identity(after)
        summary["observation_unchanged"] = before_id == after_id
        if not summary["observation_unchanged"]:
            summary["reason"] = "observation_changed"
            return
        contract_diagnostics = event.get("contract_diagnostics")
        diagnostic_messages = [str(item.get("message", ""))
                               for item in (contract_diagnostics or {}).get("errors", [])]
        detail = "\n".join([str(exc), *diagnostic_messages]).lower()
        if (isinstance(exc, TimeoutError)
                or any(text in detail for text in ("timeout", "timed out", "deadline"))):
            summary["reason"] = "time_budget_failure"
            return
        if isinstance(exc, _NativeEvaluationError):
            native_error = exc.payload.get("error")
            if native_error:
                # This is the frozen child's structured candidate traceback.
                # A dead process, invalid protocol, missing transport response
                # or startup error has no such attribution to candidate code.
                if (not isinstance(native_error, str)
                        or not native_error.startswith("Traceback (most recent call last):")
                        or 'File "<python_tool>"' not in native_error):
                    summary["reason"] = "native_infrastructure_or_unattributed_failure"
                    return
            elif exc.payload.get("returncode") != 0:
                summary["reason"] = "native_result_unavailable_without_completed_execution"
                return
        elif not isinstance(exc, ValueError):
            summary["reason"] = "not_an_attributed_artifact_error"
            return
        if (isinstance(exc, _ValidationSideEffect)
                or bool((contract_diagnostics or {}).get("has_side_effect_rejection"))
                or any(text in detail for text in (
                    "contains an action or executable-i/o call", "import is outside",
                    "functions must not mutate global bindings", "not allowed in the sandbox"))):
            summary["reason"] = "side_effect_or_capability_refusal"
            return
        if state.repair_used:
            summary["reason"] = "shared_repair_quota_exhausted"
            return
        if (not self.can_branch(agent, state)
                or deadline - time.monotonic() < 1):
            summary["reason"] = "remaining_budget"
            return
        response = event.get("response")
        failed_source = _submitted_source(response)
        feedback = {"stage": event["stage"], "error": event["error"],
                    "exception_type": type(exc).__name__, "traceback": traceback.format_exc(),
                    "actual_actions": 0, "observation_unchanged": True,
                    "before": before_id, "after": after_id}
        if contract_diagnostics is not None:
            feedback["contract_diagnostics"] = copy.deepcopy(contract_diagnostics)
        if isinstance(exc, _NativeEvaluationError):
            feedback["sandbox_payload"] = copy.deepcopy(exc.payload)
        for source, target in (("validation", "validation_errors"),
                               ("first_prediction_validation", "prediction_errors")):
            if event.get(source) is not None:
                feedback[target] = copy.deepcopy(event[source].get("errors", []))
        if failed_source is None:
            feedback["raw_submission"] = copy.deepcopy(response)
        state.pending = {"kind": "repair", "repair_reason": "zero_action_validation",
                         "source_code": trigger.get("source_code", state.source_code),
                         "previous_program": failed_source or "",
                         "previous_program_hash": _delivery_source_metadata(failed_source).get("code_sha256"),
                         "validation_feedback": feedback}
        summary.update(eligible=True, queued=True, reason="one_shared_repair_requested")

    def run_branch(self, agent, state, trigger):
        kind = trigger["kind"]
        if kind == "bootstrap":
            state.bootstrap_used = True
        if kind == "repair":
            if state.repair_used:
                return {"status": "repair_quota_exhausted", "actual_actions": 0}
            state.repair_used = True
        if not self.can_branch(agent, state):
            self.event(state, {"kind": "branch_skipped", "reason": "remaining_budget", "trigger": trigger})
            return {"status": "budget_unavailable", "actual_actions": 0}
        started = time.monotonic()
        branch_deadline = started + min(self.extra_limit - state.extra_seconds,
                                        self.remaining(agent, state))
        old_functions = copy.deepcopy(agent._kept_functions)
        old_history = copy.deepcopy(agent._history_messages)
        old_context = getattr(self.tls, "context", None)
        state.in_branch = True
        context = {"agent": agent, "state": state, "calls": 0, "executed": 0,
                   "validation": False, "host_plan": True, "deadline": branch_deadline}
        event = {"kind": "program_recomputed", "trigger": trigger, "actual_actions": 0,
                 "stage": "context", "timings": {}, "request_record": {},
                 "request_budget_seconds": min(self.request_seconds, branch_deadline - started),
                 "semantic_claim": "Current declared pixels and action binding only; goal and rules remain hypotheses"}
        report = {"status": "rejected", "actual_actions": 0, "made_progress": False}
        bound_hash = None
        current = None
        progress = False
        host_started = False
        try:
            current, history_entries = self.current(state)
            source = trigger.get("source_code", state.source_code)
            bindings = _bindings(source, old_functions)
            phase = time.monotonic()
            messages, context_metadata = prepare_compact_context(
                agent, state, trigger, current, history_entries, PROMPT)
            event.update(context_metadata=context_metadata)
            event["timings"]["context_seconds"] = time.monotonic() - phase
            # The branch submits an artifact. Ordinary REPL descriptions
            # encouraged the v3 model to print observations instead of deliver.
            tools = [delivery_tool_schema()]
            timeout = min(self.request_seconds, branch_deadline - time.monotonic(),
                          self.remaining(agent, state))
            if timeout < 1 or self.stopped(state):
                raise TimeoutError("extra-branch deadline exhausted before request")
            event["stage"] = "request"
            phase = time.monotonic()
            response = self.completion(agent, messages, tools, timeout=timeout, max_tokens=4096,
                enable_thinking=False,
                tool_choice_override={"type": "function", "function": {"name": "submit_program"}},
                request_record=event["request_record"], max_input_tokens=16384)
            event["timings"]["request_seconds"] = time.monotonic() - phase
            agent._accumulate_usage_tokens(response.usage)
            event.update(usage=response.usage, response=response.message,
                         finish_reason=response.finish_reason,
                         served_by=getattr(response, "served_by", None))
            event["stage"] = "extract"
            event["delivery_code"] = _delivery_source_metadata(_submitted_source(response.message))
            definitions = extract_definitions(response.message, expected_tool_name="submit_program",
                max_nonempty_lines=_DELIVERY_MAX_NONEMPTY_LINES, max_code_bytes=_DELIVERY_MAX_CODE_BYTES,
                allow_literal_defaults=True)
            code = definitions["code"]
            event.update(program_code=code, program_hash=definitions["code_sha256"])
            phase = time.monotonic()
            event["stage"] = "plan_validation"
            result = self.evaluate(agent, state, code + "\nresult = plan_program(current_frame)", deadline=branch_deadline)
            validation = validate_plan(result, current.grid, self.chars,
                self.module._normalize_valid_actions(agent._current_valid_actions), bindings)
            event["validation"] = validation
            if not validation["passed"]:
                raise ValueError("plan rejected: " + str(validation.get("errors")))
            plan = validation["plan"]
            report["goal"] = plan["goal"]
            if plan["status"] != "ready":
                agent._kept_functions = old_functions
                report.update(status="local_completed" if plan["status"] == "completed" else "abstained",
                              local_status=plan["status"], environment_success_claim=False)
                event.update(status=report["status"], stage="local_status", local_status=plan["status"])
            else:
                event["stage"] = "initial_prediction"
                first_prediction = self.evaluate(agent, state, code + "\nresult = predict(current_frame, "
                    + repr(plan["actions"][0]) + ")", deadline=branch_deadline)
                first_validation = validate_prediction(first_prediction, current.grid, self.chars,
                                                       expected_action=plan["actions"][0])
                event["first_prediction_validation"] = first_validation
                if not first_validation["passed"]:
                    raise ValueError("first prediction rejected: " + str(first_validation.get("errors")))
                result2 = self.evaluate(agent, state, code + "\nresult = plan_program(current_frame)",
                                        commit=True, deadline=branch_deadline)
                if _hash(result) != _hash(result2):
                    raise ValueError("plan_program is nondeterministic on unchanged observation")
                state.program = code
                state.program_hash = bound_hash = definitions["code_sha256"]
                state.program_bindings = bindings
                state.prediction_support = 0
                event["timings"]["validation_seconds"] = time.monotonic() - phase
                event.update(status="plan_recomputed_and_bound", goal=plan["goal"],
                             plan_hash=_hash(plan), proposed_actions=plan["actions"])
                self.event(state, {"kind": "contract_bound", "status": "ready", "plan": plan,
                                   "input_step": current.step, "input_grid_sha256": _hash(current.grid)})
                self.tls.context = context
                host_started = True
                phase = time.monotonic()
                last_output = {}
                terminal_status = "short_plan_action_limit"
                for action_index in range(3):
                    if self.stopped(state) or min(branch_deadline - time.monotonic(), self.remaining(agent, state)) < 1:
                        terminal_status = "deadline"
                        break
                    current, history_entries = self.current(state)
                    if state.program is None:
                        terminal_status = "contract_boundary"
                        break
                    if action_index:
                        event["stage"] = "live_recomputation"
                        result = self.evaluate(agent, state, code + "\nresult = plan_program(current_frame)",
                                               deadline=branch_deadline)
                        validation = validate_plan(result, current.grid, self.chars,
                            self.module._normalize_valid_actions(agent._current_valid_actions), bindings)
                        self.event(state, {"kind": "plan_recomputed", "validation": validation,
                            "input_step": current.step, "input_grid_sha256": _hash(current.grid),
                            "recent_real_actions": [{"action": h.action, "level": h.frame.level,
                                                     "step": h.frame.step, "result": h.result}
                                                    for h in history_entries[-4:]]})
                        if not validation["passed"]:
                            raise ValueError("recomputed plan rejected: " + str(validation.get("errors")))
                        plan = validation["plan"]
                        if plan["status"] != "ready":
                            terminal_status = "local_completed" if plan["status"] == "completed" else "abstained"
                            break
                    action = plan["actions"][0]
                    event["stage"] = "host_action"
                    count_before = context["executed"]
                    old_timeout = agent._python_timeout
                    try:
                        agent._python_timeout = min(old_timeout, branch_deadline - time.monotonic(),
                                                    self.remaining(agent, state))
                        if agent._python_timeout < 1:
                            raise TimeoutError("extra-branch deadline exhausted before action")
                        dispatch = self.original_python(agent, state.path,
                            {"code": "result = action(" + repr([action]) + ")"})
                    finally:
                        agent._python_timeout = old_timeout
                    last_output = _payload(dispatch.content)
                    progress |= bool(dispatch.made_progress)
                    if state.pending is not None:
                        terminal_status = "counterexample"
                        break
                    if context.get("halted") or state.program is None:
                        terminal_status = "contract_stopped"
                        break
                    if context["executed"] == count_before:
                        terminal_status = "not_executed"
                        break
                event["timings"]["host_execution_seconds"] = time.monotonic() - phase
                report.update(status="recomputed_plan_executed", program_hash=bound_hash,
                    actual_actions=context["executed"], made_progress=progress,
                    stop_reason=terminal_status, tool_output=last_output,
                    environment_success_claim=False)
                event.update(status=report["status"], stage="finished", actual_actions=context["executed"],
                             stop_reason=terminal_status)
        except Exception as exc:
            agent._kept_functions = old_functions
            # A completed HTTP generation can still be rejected by the
            # served-token cross-check. Its real cost must not disappear.
            request_record = event["request_record"]
            if "usage" not in event and isinstance(request_record.get("usage"), dict):
                agent._accumulate_usage_tokens(request_record["usage"])
                event.update(usage=request_record["usage"],
                             finish_reason=request_record.get("finish_reason"))
                body = request_record.get("response_body") or {}
                choices = body.get("choices") or []
                if choices:
                    event["response"] = choices[0].get("message")
            report.update(status="rejected" if not context["executed"] else "execution_failed",
                actual_actions=context["executed"], made_progress=progress,
                program_hash=bound_hash, error=f"{type(exc).__name__}: {exc}",
                failure_stage=event["stage"],
                next="Continue ordinary exploration from the real current_frame; the old suffix must not be replayed.")
            event.update(status=report["status"], error=report["error"], actual_actions=context["executed"])
            if isinstance(exc, DefinitionContractError):
                event["contract_diagnostics"] = exc.to_dict()
            if current is not None:
                self.queue_validation_feedback(agent, state, trigger, context, event,
                                               current, exc, branch_deadline)
        finally:
            self.release(state, "short_plan_ended")
            elapsed = time.monotonic() - started
            state.extra_seconds += elapsed
            state.in_branch = False
            agent._history_messages = old_history
            self.tls.context = old_context
            event.update(elapsed_seconds=elapsed, extra_seconds_used=state.extra_seconds,
                         budget_overrun_seconds=max(0.0, time.monotonic() - branch_deadline))
            report["extra_seconds_used"] = state.extra_seconds
            if host_started:
                self.event(state, {"kind": "host_plan_execution", **report})
            self.event(state, event)
        if state.pending is not None and state.pending.get("kind") == "repair" and not state.repair_used:
            pending, state.pending = state.pending, None
            repair = self.run_branch(agent, state, pending)
            report["followup_repair"] = repair
            report["actual_actions"] += repair.get("actual_actions", 0)
            report["made_progress"] |= bool(repair.get("made_progress"))
            report["extra_seconds_used"] = state.extra_seconds
        return report

    def snapshot(self):
        with self.lock:
            return {"patch": "034-executable-plan-v8", "games": len(self.states),
                    "bootstrap_calls": sum(s.bootstrap_used for s in self.states),
                    "repair_calls": sum(s.repair_used for s in self.states),
                    "extra_seconds": sum(s.extra_seconds for s in self.states),
                    "events": [{"path": str(s.path), "event_count": len(s.events),
                                "statuses": [e.get("status") for e in s.events if e.get("status")]}
                               for s in self.states]}

    def uninstall(self):
        for name, installed, original in (
            ("_run_python_tool", self.python, self.original_python),
            ("analyze", self.analyze, self.original_analyze),
            ("_chat_completion", self.chat, self.original_chat),
            ("_action_guard_hook", self.guard, self.original_guard),
        ):
            if getattr(self.agent_class, name) is installed:
                setattr(self.agent_class, name, original)
        if self.module.run_sandboxed_python is self.sandbox_call:
            self.module.run_sandboxed_python = self.original_sandbox
        self.sandbox_module._SANDBOX_BOOTSTRAP = self.original_bootstrap
        self.agent_class._executable_plan_installed = False


def install_executable_plan(**kwargs):
    return ExecutablePlanPatch(**kwargs)
