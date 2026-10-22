"""034: bounded repair of a live program, host recomputation and checked actions.

Installs in memory on the frozen actor. No game names, answers or hidden state.
A native snippet is ended before a queued batch (or its second action call).
One bounded model request builds a current-frame plan and predictor. The host
executes that plan, freezes predictions before each real action, and sends a
structured counterexample to one subsequent bounded repair request. Unknown
checks stop the snippet; an invalid contract can be abandoned for exploration.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any

from arc3_research.program_repair import _completion, _plain_messages, _payload, _remaining
from arc3_research.executable_plan_contract import (
    binding_names, compare_prediction, extract_definitions, validate_plan, validate_prediction,
)


PROMPT = """The host paused a real Python action sequence. Repair the SMALL live
program/input that generated it, then recompute its current goal and plan.
Reuse the existing rule/search when evidence supports it; revise a contradicted
rule instead of just repeating the previous actions. Current state is live.
Return one python tool call containing self-contained function definitions and
imports only, with these two entry points:

plan_program(frame) -> {"goal": nonempty current target description/data,
 "actions": [model-facing action dicts, at most 12],
 "evidence_pixels": [[row,col,color_character], ...],
 "replaces": [names from the paused code or retained functions], "reason": str}
predict(frame, action) -> {"expected_pixels": [[row,col,color_character], ...],
 "scope": "which observable change this checks"}

plan_program must READ frame and actually RECOMPUTE the relevant input, goal
and actions. Do not just rename a stale hand-written target or old action list.
predict runs before each action and returns concrete, nonempty pixel predictions
for the action's relevant observable consequences. Predict actual color values,
not flags such as ok=True. MOUSE uses row/col; other actions use only action.
Do not propose RESET or UNDO. Return no prints or top-level calls. Definitions
must have no decorators, default arguments, annotations, global or nonlocal.
Computational imports such as math, collections, itertools, heapq and numpy
are supported. No function
may execute action(), RESET, UNDO or other environment side effects. The host
will run plan_program and predict itself in a zero-action sandbox, check pixel
evidence against the current public image, and then execute the plan through
the ordinary action path. A pixel/schema check does NOT certify your rule.

Ordinary globals do not persist. Put dependencies/parameters in the returned
functions; existing retained helpers are available, but stale layout constants
must be rebound from this frame. Frame has ascii, shape, level, step; you may
internally read exact current ASCII for this computation, without printing the
whole image. If the rule is uncertain, make a short useful next plan, with an
honest prediction to test. Do not copy every pixel as a replacement task model.
"""


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
            f.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
        return entry

    def current(self, state):
        from inference.agent.runtime_state import load_runtime_state
        frame, history = load_runtime_state(state.path)
        if state.level is not None and frame.level != state.level:
            state.program = None
            state.prediction_support = 0
        state.level = frame.level
        return frame, history

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
                raise ValueError("zero-action validation attempted a side effect or changed the observation")
            if payload.get("error") or "result" not in payload:
                raise ValueError("program did not return result: " + str(payload)[:1200])
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
            reply = execute(actions, stale_after=stale_after)
            context["reply_state"] = copy.deepcopy(reply.get("state", context["reply_state"]))
            outcome = reply.get("action_result", {})
            count = int(outcome.get("executed_count") or bool(outcome.get("executed")))
            context["executed"] += count
            state.observation_serial += count
            if any(outcome.get(k) for k in ("game_over", "level_completed", "run_complete", "done")):
                state.program = None
                state.attempt_event += int(bool(outcome.get("game_over")))
            self.event(state, {"kind": "unchecked_action", "status": "unverified",
                               "actions": normalized, "actual_actions": count})
            return reply

        replies, animations = [], []
        context["death_override"] = False
        for index, action in enumerate(normalized):
            if self.stopped(state) or self.remaining(agent, state) <= 0:
                return self.interrupt(context, "deadline", "Shared deadline reached; suffix stopped") if not replies else self.aggregate(context, replies, len(normalized), interrupt="deadline")
            before, _ = self.current(state)
            try:
                predicted = self.evaluate(agent, state, state.program +
                    "\nresult = predict(current_frame, " + repr(action) + ")")
                valid = validate_prediction(predicted, before.grid, self.chars)
                if not valid["passed"]:
                    raise ValueError(str(valid.get("errors")))
                frozen = copy.deepcopy(valid["prediction"])
            except Exception as exc:
                problem = {"kind": "prediction_unavailable", "status": "unknown",
                           "action": action, "error": f"{type(exc).__name__}: {exc}"}
                self.invalidate(state, problem)
                return self.interrupt(context, "unknown", str(problem)) if not replies else self.aggregate(context, replies, len(normalized), interrupt="unknown")
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
                                   "action": action, "actual_actions": count})
                state.program = None
                state.prediction_support = 0
                state.attempt_event += int(bool(outcome.get("game_over")))
                break
            if not count:
                self.event(state, {"kind": "checked_action", "status": "not_executed", "outcome": outcome})
                break
            comparison = compare_prediction(frozen, after.grid, self.chars)
            self.event(state, {"kind": "checked_action", "action": action,
                               "expected": frozen, "observed": comparison,
                               "status": comparison["status"], "actual_actions": count})
            if comparison["status"] != "match":
                self.invalidate(state, {"kind": "counterexample", "status": comparison["status"],
                    "action": action, "expected": frozen, "observed": comparison})
                return self.aggregate(context, replies, len(normalized), interrupt=comparison["status"])
            state.prediction_support += 1
        agent._last_animation_chain = animations
        return self.aggregate(context, replies, len(normalized)) if replies else self.interrupt(context, "empty", "No actions to execute")

    def invalidate(self, state, problem):
        source_hash = state.program_hash
        previous_program = state.program
        state.program = None
        state.prediction_support = 0
        self.event(state, {**problem, "invalidated_program_hash": source_hash})
        if not state.repair_used:
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
        state.in_branch = True
        event = {"kind": "program_recomputed", "trigger": trigger, "actual_actions": 0,
                 "request_budget_seconds": min(self.request_seconds, self.extra_limit - state.extra_seconds),
                 "semantic_claim": "current pixels and selected prediction only; goal/rules are hypotheses"}
        try:
            current, history_entries = self.current(state)
            source = trigger.get("source_code", state.source_code)
            bindings = _bindings(source, old_functions)
            public_now = {"level": current.level, "step": current.step,
                          "shape": current.shape, "ascii": current.ascii,
                          "recent_real_actions": [{"action": h.action, "step": h.frame.step,
                                                   "level": h.frame.level, "result": h.result}
                                                  for h in history_entries[-2:]],
                          "last_actual_result": agent._last_action_call_result}
            public_trigger = {k: v for k, v in trigger.items() if k not in ("source_code", "previous_program")}
            text = (PROMPT + "\nLive program bindings: " + repr(bindings)
                    + "\nPaused code:\n" + source[-12000:]
                    + "\nActive program being corrected (if present):\n" + str(trigger.get("previous_program") or "")[-16000:]
                    + "\nPublic trigger:\n" + json.dumps(public_trigger, ensure_ascii=False)
                    + "\nCURRENT public observation AFTER any already executed action (not the old request image):\n"
                    + json.dumps(public_now, ensure_ascii=False))
            history = state.latest_messages or [{"role": "system", "content": agent._system_prompt}, *old_history]
            messages = _plain_messages(history)
            # A pending tool call is rendered as text so there are no orphan
            # tool IDs in the additional bounded request.
            for message in messages:
                if message.get("tool_calls"):
                    message["content"] = str(message.get("content") or "") + "\n" + json.dumps(message.pop("tool_calls"))
                if message.get("role") == "tool":
                    message["role"] = "user"
                    message.pop("tool_call_id", None)
            messages.append({"role": "user", "content": text})
            tools = agent._tools(state.path)
            messages = agent._trim_messages_for_context(messages, tools=tools)
            timeout = min(self.request_seconds, branch_deadline - time.monotonic(),
                          self.remaining(agent, state))
            if timeout < 1 or self.stopped(state):
                raise TimeoutError("extra-branch deadline exhausted before request")
            response = self.completion(agent, messages, tools, timeout=timeout, max_tokens=4096)
            agent._accumulate_usage_tokens(response.usage)
            event.update(usage=response.usage, response=response.message)
            definitions = extract_definitions(response.message)
            code = definitions["code"]
            result = self.evaluate(agent, state, code + "\nresult = plan_program(current_frame)", deadline=branch_deadline)
            validation = validate_plan(result, current.grid, self.chars,
                                       self.module._normalize_valid_actions(agent._current_valid_actions), bindings)
            event.update(program_code=code, validation=validation)
            if not validation["passed"]:
                raise ValueError("plan rejected: " + str(validation.get("errors")))
            first_prediction = self.evaluate(agent, state, code + "\nresult = predict(current_frame, "
                + repr(validation["plan"]["actions"][0]) + ")", deadline=branch_deadline)
            first_validation = validate_prediction(first_prediction, current.grid, self.chars)
            if not first_validation["passed"]:
                raise ValueError("first prediction rejected: " + str(first_validation.get("errors")))
            event["first_prediction_validation"] = first_validation
            # Re-evaluate the returned source to check determinism and commit
            # its functions. Host action consumption below establishes use;
            # this is not a separate cross-call retention certificate.
            result2 = self.evaluate(agent, state, code + "\nresult = plan_program(current_frame)", commit=True, deadline=branch_deadline)
            if _hash(result) != _hash(result2):
                raise ValueError("plan_program is nondeterministic on unchanged observation")
            if time.monotonic() - started > self.extra_limit - state.extra_seconds or self.stopped(state):
                raise TimeoutError("shared extra-branch deadline exhausted before actions")
            state.program = code
            state.program_hash = definitions["code_sha256"]
            state.prediction_support = 0
            event.update(status="plan_recomputed_and_bound", program_hash=state.program_hash,
                         goal=result["goal"], plan_hash=_hash(validation["plan"]),
                         proposed_actions=validation["plan"]["actions"])
            self.event(state, event)
        except Exception as exc:
            agent._kept_functions = old_functions
            state.program = None
            event.update(status="rejected", error=f"{type(exc).__name__}: {exc}")
            self.event(state, event)
            return {"status": "rejected", "error": event["error"], "actual_actions": 0,
                    "next": "Continue ordinary exploration from current_frame; previous suffix did not run."}
        finally:
            state.extra_seconds += time.monotonic() - started
            state.in_branch = False
            agent._history_messages = old_history
        # The bounded model branch is finished. Ordinary per-action CPU checks
        # and real actions are charged to the game/global wall clock.
        old_context = getattr(self.tls, "context", None)
        context = {"agent": agent, "state": state, "calls": 0, "executed": 0,
                   "validation": False, "host_plan": True}
        self.tls.context = context
        try:
            dispatch = self.original_python(agent, state.path,
                {"code": "result = action(" + repr(validation["plan"]["actions"]) + ")"})
            report = {"status": "recomputed_plan_executed", "program_hash": state.program_hash,
                      "goal": result["goal"], "actual_actions": context["executed"],
                      "made_progress": dispatch.made_progress, "tool_output": _payload(dispatch.content),
                      "extra_seconds_used": state.extra_seconds}
            self.event(state, {"kind": "host_plan_execution", **report})
        finally:
            self.tls.context = old_context
        if state.pending is not None and state.pending.get("kind") == "repair" and not state.repair_used:
            pending, state.pending = state.pending, None
            repair = self.run_branch(agent, state, pending)
            report["followup_repair"] = repair
            report["actual_actions"] += repair.get("actual_actions", 0)
            report["made_progress"] |= bool(repair.get("made_progress"))
        return report

    def snapshot(self):
        with self.lock:
            return {"patch": "034-executable-plan-v1", "games": len(self.states),
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
