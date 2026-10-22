"""One bounded, executable program repair using the existing agent and model.

The extra branch executes the model's Python through the real sandbox, then
leaves its actual tool output and retained functions in the main conversation.
It never supplies a game rule, an answer, or an action plan computed by the host.
"""
from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any
import uuid


DEFAULT_CONFIG = {
    "trigger_strategy": "consecutive_python_errors_v2",
    "min_consecutive_errors": 2,
    "max_events_per_game": 1,
    "max_calls_per_event": 2,
    "max_output_tokens": 4096,
    "call_timeout_seconds": 60,
    "event_timeout_seconds": 120,
    "min_remaining_seconds": 180,
    "zero_env_actions": True,
}

REPAIR_PROMPT = """A bounded program-repair branch is running because an earlier Python
calculation failed or conflicts with recorded observations. Locate a concrete
error in your existing code or its inputs using the actual observations and
tool outputs already available. Recompute the relevant extraction, simulator,
or search with corrected executable Python. Print a compact verification that
compares your corrected result with the real evidence. Redefine any corrected
top-level helper as a self-contained def so it can be retained. Ordinary global
variables do not survive the next Python call.

This branch must execute ZERO game actions: do not call action(), RESET, UNDO,
or any helper that moves the environment. Read current_frame, previous_frame,
history and the existing outputs instead. Do not invent a successful result.
Emit one small python tool call now; keep reasoning brief. The main solver
will receive your actual execution output and revised functions afterwards."""


def _configuration(config: dict[str, Any] | None) -> dict[str, Any]:
    result = {**DEFAULT_CONFIG, **(config or {})}
    if not result["zero_env_actions"]:
        raise ValueError("Program repair currently supports zero environment actions only")
    if result["trigger_strategy"] != "consecutive_python_errors_v2":
        raise ValueError("Unsupported program repair trigger strategy")
    for key in ("max_events_per_game", "max_calls_per_event", "max_output_tokens",
                "min_consecutive_errors"):
        if int(result[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    return result


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(p.get("text", "")) for p in content if isinstance(p, dict)
                         and p.get("type") == "text")
    return str(content or "")


def _plain_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # The serving model is text-only. Historical screenshots are redundant
    # with the recorded frame/ASCII views and can make the chat template fail.
    clean = copy.deepcopy(messages)
    for message in clean:
        if isinstance(message.get("content"), list):
            message["content"] = _text(message["content"])
    return clean


def _payload(content: Any) -> dict[str, Any]:
    try:
        value = json.loads(_text(content))
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def failure_signal(messages: list[dict[str, Any]], *,
                   min_consecutive_errors: int = 2) -> dict[str, Any] | None:
    """A current chain of distinct Python errors, or a structured mismatch.

    An empty search, a long stall or arbitrary prose containing 'mismatch' is
    not a machine-verifiable trigger. Error streaks are derived from actual
    tool exchanges, not incremented when the same history is read again. A
    successful or excluded-guard tool result ends the current error streak.
    """
    minimum = max(1, int(min_consecutive_errors))
    tool_names = {}
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                if isinstance(call, dict) and call.get("id"):
                    tool_names[str(call["id"])] = call.get("function", {}).get("name")
    errors = []
    seen = set()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") != "tool":
            continue
        call_id = str(message.get("tool_call_id") or "")
        # Proper exchanges have a stable tool_call_id. The content fallback
        # handles text-only diagnostic messages without counting copied output
        # twice; different real calls with ids still count as separate errors.
        identity = ("call", call_id) if call_id else ("content", _text(message.get("content")))
        if identity in seen:
            continue
        seen.add(identity)
        data = _payload(message.get("content"))
        # Only the newest tool output may own an immediate mismatch signal.
        # Older mismatches may already have been corrected by later outputs.
        if not errors:
            result = data.get("result")
            checks = [data, result] if isinstance(result, dict) else [data]
            for check in checks:
                if (check.get("status") in ("prediction_mismatch", "mismatch")
                        and "expected" in check and "observed" in check
                        and check["expected"] != check["observed"]):
                    return {"kind": "prediction_mismatch", "message_index": index,
                            "expected": check["expected"], "observed": check["observed"]}
        name = str(data.get("tool") or tool_names.get(call_id) or "")
        error = str(data.get("error") or "")
        if name != "python" or not error or any(label in error for label in (
                "KnownNoOpActionError", "KnownDeathActionError", "StaleStateActionError",
                "RepeatedActionInStateError", "TerminalStateActionError",
                "Sandbox process exited unexpectedly", "timed out")):
            return None
        errors.append({"message_index": index, "tool_call_id": call_id,
                       "error": error[-3000:]})
        if len(errors) >= minimum:
            return {"kind": "consecutive_python_errors", "message_index": errors[0]["message_index"],
                    "error": errors[0]["error"], "consecutive_errors": len(errors),
                    "errors": errors, "trigger_strategy": "consecutive_python_errors_v2"}
    return None


def _remaining(analyzer: Any) -> float | None:
    callback = getattr(analyzer, "_step_env_callback", None)
    session = getattr(callback, "__self__", None)
    candidates = []
    if session is not None:
        try:
            value = session.timing_payload().get("time_remaining_seconds")
            if value is not None:
                candidates.append(float(value))
        except (AttributeError, TypeError, ValueError):
            pass
        try:
            value = session.solver.soft_time_remaining_seconds()
            if value is not None:
                candidates.append(float(value))
        except (AttributeError, TypeError, ValueError):
            pass
    return max(0.0, min(candidates)) if candidates else None


def _write_event(state_path: Path, event: dict[str, Any]) -> None:
    destination = state_path.with_name(state_path.stem + "_program-repair.jsonl")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        event["event_log"] = str(destination)
    except OSError as exc:
        event["log_error"] = str(exc)


def _completion(analyzer: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                *, timeout: float, max_tokens: int, enable_thinking: bool | None = None,
                tool_choice: str | None = None, parallel_tool_calls: bool | None = None,
                preserve_thinking: bool | None = None) -> Any:
    """Same model payload and sampling; one bounded request without retries.

    Non-streaming HTTP makes the read timeout bound the whole generation wait;
    this branch cannot silently retry a sixty-second request several times.
    """
    module = importlib.import_module(type(analyzer).__module__)
    payload = module.build_chat_payload(
        provider=analyzer._model.provider, model=analyzer._model.model_id,
        messages=messages, max_tokens=max_tokens,
        temperature=module._LOCAL_ANALYZER_TEMPERATURE,
        top_p=module._LOCAL_ANALYZER_TOP_P, top_k=module._LOCAL_ANALYZER_TOP_K,
        thinking=(bool(module._LOCAL_ANALYZER_ENABLE_THINKING)
                  if enable_thinking is None else enable_thinking), tools=tools,
        tool_choice=(module._request_tool_choice(tools) if tool_choice is None else tool_choice),
        seed=module._LOCAL_ANALYZER_SEED)
    preferences = module._openrouter_provider_prefs(analyzer._model.provider)
    if preferences:
        payload["provider"] = preferences
    template = {**(payload.get("chat_template_kwargs") or {}),
                **analyzer._harness_template_kwargs()}
    # Request-local control, after the merge, as in the frozen actor's own
    # _chat_completion. Never change its global thinking or tool-choice defaults.
    if enable_thinking is not None:
        template["enable_thinking"] = bool(enable_thinking)
    if preserve_thinking is not None:
        template["preserve_thinking"] = bool(preserve_thinking)
    if template:
        payload["chat_template_kwargs"] = template
    if parallel_tool_calls is not None:
        payload["parallel_tool_calls"] = bool(parallel_tool_calls)
    payload["messages"] = module._strip_control_keys(module._apply_summary_visibility(
        payload.get("messages") or [], evicted=getattr(analyzer, "_has_evicted", False)))
    payload["stream"] = False
    payload.pop("stream_options", None)
    response = module.requests.post(
        analyzer._model.base_url.rstrip("/") + "/chat/completions",
        headers=analyzer._headers(), json=payload,
        timeout=(min(float(module._CONNECT_TIMEOUT_SECONDS), timeout), timeout))
    try:
        response.raise_for_status()
        body = response.json()
    finally:
        response.close()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("Repair request returned no completion choices")
    choice = choices[0]
    return module._ChatCompletionResult(
        message=module._extract_leaked_tool_calls(choice.get("message") or {}),
        usage=body.get("usage"), finish_reason=str(choice.get("finish_reason") or ""),
        served_by=str(body.get("provider") or ""))


def run_program_repair(analyzer: Any, state_path: Path, *,
                       messages: list[dict[str, Any]] | None = None,
                       reason: Any = "recorded_failure", remaining_seconds: float | None = None,
                       config: dict[str, Any] | None = None,
                       should_stop: Any = None) -> dict[str, Any]:
    """Run and execute a repair, appending actual exchanges to the main history.

    The caller must initialize the agent's session BEFORE restoring its history
    and functions, and bind the real session callback/current valid actions.
    Pass ``messages`` from an active analyze turn for in-place transfer, or omit
    it for a restored fork (the function then updates ``_history_messages``).
    """
    cfg = _configuration(config)
    state_path = Path(state_path)
    started = time.monotonic()
    event = {"kind": "program_repair", "reason": reason, "calls": [],
             "env_actions_executed": 0, "blocked_action_calls": 0,
             "status": "not_started", "config": cfg}
    used = int(getattr(analyzer, "_program_repair_event_count", 0))
    if getattr(analyzer, "_program_repair_disabled", False):
        event["status"] = "disabled"
        return event
    if used >= int(cfg["max_events_per_game"]):
        event["status"] = "event_limit"
        return event
    remaining = _remaining(analyzer) if remaining_seconds is None else float(remaining_seconds)
    if remaining is None or remaining < float(cfg["min_remaining_seconds"]):
        event.update(status="insufficient_time", remaining_seconds=remaining)
        return event
    if should_stop is not None and should_stop():
        event["status"] = "stopped"
        return event
    analyzer._program_repair_event_count = used + 1
    analyzer._program_repair_game_state_parent = state_path.parent
    analyzer._program_repair_active = True
    event.update(event_index=used + 1, remaining_seconds=remaining)
    source_messages = messages
    if source_messages is None:
        source_messages = [{"role": "system", "content": analyzer._system_prompt},
                           *copy.deepcopy(analyzer._history_messages)]
    repair_messages = _plain_messages(source_messages)
    repair_messages.append({"role": "user", "content": REPAIR_PROMPT})
    transfer: list[dict[str, Any]] = [repair_messages[-1]]
    tools = analyzer._tools(state_path)
    original_callback = analyzer._step_env_callback
    original_python_timeout = analyzer._python_timeout
    original_action_result = copy.deepcopy(getattr(analyzer, "_last_action_call_result", None))
    original_step_summary = copy.deepcopy(getattr(analyzer, "_last_step_summary", None))
    original_valid_actions = list(getattr(analyzer, "_current_valid_actions", []))
    deadline = started + min(float(cfg["event_timeout_seconds"]), remaining)

    def no_environment_actions(request: Any) -> dict[str, Any]:
        event["blocked_action_calls"] += 1
        # An existing closed-set refusal ends even an except-Exception loop in
        # the native sandbox and preserves stdout plus retained definitions.
        # The real callback is NEVER invoked, so an env action cannot leak.
        return {"executed": False, "executed_count": 0, "requested_count": 0,
                "stopped_early": True, "stop_reason": "known_noop",
                "stop_detail": "Program repair is recompute-only: no action was executed.",
                "valid_actions": original_valid_actions}

    analyzer._step_env_callback = no_environment_actions
    try:
        for call_index in range(int(cfg["max_calls_per_event"])):
            left = deadline - time.monotonic()
            if left <= 0 or (should_stop is not None and should_stop()):
                event["status"] = "time_budget"
                break
            call = {"index": call_index + 1}
            event["calls"].append(call)
            try:
                request_messages = analyzer._trim_messages_for_context(repair_messages, tools=tools)
                result = _completion(analyzer, request_messages, tools,
                                     timeout=max(0.1, min(float(cfg["call_timeout_seconds"]), left)),
                                     max_tokens=int(cfg["max_output_tokens"]))
                analyzer._accumulate_usage_tokens(result.usage)
                call.update(usage=result.usage, finish_reason=result.finish_reason)
                message = dict(result.message or {})
                calls = message.get("tool_calls") or []
                chosen = next((item for item in calls if
                               item.get("function", {}).get("name") == "python"), None)
                if chosen is None:
                    content = _text(message.get("content"))
                    match = re.search(r"```(?:python)?\s*\n(.*?)```", content, re.S)
                    if match:
                        chosen = {"id": "repair_" + uuid.uuid4().hex,
                                  "type": "function", "function": {
                                      "name": "python", "arguments": json.dumps({"code": match.group(1)})}}
                if chosen is None:
                    call["assistant_content"] = _text(message.get("content"))
                    event["status"] = "no_executable_code"
                    repair_messages.append({"role": "user", "content":
                        "Emit the small corrected Python program as a python tool call now; do not explain only."})
                    continue
                function = chosen["function"]
                arguments = function.get("arguments") or {}
                arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                code = str(arguments.get("code") or "")
                if not code.strip():
                    raise ValueError("Repair python call had empty code")
                compile(code, "<program_repair>", "exec")
                chosen = {**chosen, "id": chosen.get("id") or "repair_" + uuid.uuid4().hex}
                assistant = {"role": "assistant", "content": _text(message.get("content")) or None,
                             "tool_calls": [chosen]}
                repair_messages.append(assistant)
                transfer.append(assistant)
                call["code"] = code
                analyzer._python_timeout = max(0.1, min(float(original_python_timeout),
                                                     deadline - time.monotonic()))
                dispatch = analyzer._dispatch_tool(state_path, "python", {"code": code})
                if dispatch.step_executed:
                    raise RuntimeError("Repair invariant failed: dispatcher reports an environment action")
                actual = {"role": "tool", "tool_call_id": chosen["id"], "content": dispatch.content}
                repair_messages.append(actual)
                transfer.append(actual)
                call["tool_output"] = dispatch.content
                call["retained_functions"] = list(getattr(analyzer, "_kept_functions", {}))
                payload = _payload(dispatch.content)
                if payload.get("error"):
                    event["status"] = "execution_error"
                    repair_messages.append({"role": "user", "content":
                        "The repair code failed. Correct the actual reported error with one smaller recompute-only Python call."})
                    continue
                event["status"] = "executed"
                break
            except Exception as exc:
                call["error"] = f"{type(exc).__name__}: {exc}"
                event["status"] = "request_or_code_error"
                break
    finally:
        analyzer._step_env_callback = original_callback
        analyzer._python_timeout = original_python_timeout
        analyzer._last_action_call_result = original_action_result
        analyzer._last_step_summary = original_step_summary
        analyzer._current_valid_actions = original_valid_actions
        analyzer._program_repair_active = False
        source_messages.extend(transfer)
        if messages is None:
            analyzer._history_messages = [m for m in source_messages if m.get("role") != "system"]
        event["elapsed_seconds"] = time.monotonic() - started
        event["transferred_messages"] = len(transfer)
        event["retained_functions_after"] = list(getattr(analyzer, "_kept_functions", {}))
        _write_event(state_path, event)
    return event


class ProgramRepairPatch:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        from inference.agent.tool_agent import ToolAgent
        self.config = _configuration(config)
        self.agent_class = ToolAgent
        self.original_analyze = ToolAgent.analyze
        self.original_chat = ToolAgent._chat_completion
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

        def analyze(agent: Any, state_path: Path, *args: Any, **kwargs: Any) -> Any:
            parent = Path(state_path).parent
            previous = getattr(agent, "_program_repair_game_state_parent", None)
            if previous is not None and previous != parent:
                agent._program_repair_event_count = 0
            agent._program_repair_game_state_parent = parent
            agent._program_repair_state_path = Path(state_path)
            agent._program_repair_should_stop = kwargs.get("should_stop")
            return self.original_analyze(agent, state_path, *args, **kwargs)

        def chat(agent: Any, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
            repaired = None
            if not (getattr(agent, "_program_repair_active", False)
                    or getattr(agent, "_program_repair_disabled", False)):
                signal = failure_signal(messages,
                                        min_consecutive_errors=int(self.config["min_consecutive_errors"]))
                state = getattr(agent, "_program_repair_state_path", None)
                if signal is not None and state is not None:
                    event = run_program_repair(
                        agent, state, messages=messages, reason=signal, config=self.config,
                        should_stop=getattr(agent, "_program_repair_should_stop", None))
                    if event.get("calls"):
                        repaired = (state, event)
                        with self._lock:
                            self._events.append({k: event.get(k) for k in (
                                "status", "elapsed_seconds", "reason", "event_log",
                                "blocked_action_calls", "transferred_messages")})
            result = self.original_chat(agent, messages, **kwargs)
            if repaired is not None:
                state, event = repaired
                # Native request snapshots are captured just before this hook;
                # save the actual subsequent response as separate causal
                # evidence that the main model received the repair exchanges.
                _write_event(state, {"kind": "main_response_after_program_repair",
                                    "repair_event_index": event.get("event_index"),
                                    "repair_status": event.get("status"),
                                    "main_message": result.message,
                                    "usage": result.usage,
                                    "repair_messages_present": event.get("transferred_messages")})
            return result

        self.analyze = analyze
        self.chat = chat
        ToolAgent.analyze = analyze
        ToolAgent._chat_completion = chat

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"patch": "bounded-program-repair-v2", "config": dict(self.config),
                    "events": list(self._events), "event_count": len(self._events),
                    "trigger": "at least two consecutive distinct Python errors, or immediate structured prediction mismatch",
                    "transport": "same model/sampling/template, non-streaming, no retry"}

    def uninstall(self) -> None:
        if self.agent_class.analyze is self.analyze:
            self.agent_class.analyze = self.original_analyze
        if self.agent_class._chat_completion is self.chat:
            self.agent_class._chat_completion = self.original_chat


def install_program_repair(config: dict[str, Any] | None = None) -> ProgramRepairPatch:
    return ProgramRepairPatch(config)
