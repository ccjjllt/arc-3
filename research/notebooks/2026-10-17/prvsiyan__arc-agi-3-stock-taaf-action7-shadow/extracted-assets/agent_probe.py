"""Observe one real ARC3 V1 model/tool/action path without changing its results.

Install only after the exact reviewed harness is loaded. The native driver owns
the process deadline, selected public game, action cap, and terminal GameRun
checks. This helper neither starts a model nor executes generated code itself.
Linkage starts at the original _chat_completion return, after the harness's
native tool-call normalization. It is not a raw HTTP/wire observation. Any later
dispatch must match a python call present at that boundary. Native parser flags
remain unchanged. No generated text or tool arguments appear in receipts.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import json
import threading


class ProbeFailure(RuntimeError):
    """A fixed diagnostic code, never an exception containing model content."""


def _digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _positive_output_tokens(usage):
    if not isinstance(usage, dict):
        return 0
    values = [usage.get(k) for k in
              ("completion_tokens", "output_tokens", "generated_tokens")]
    return max([v for v in values if type(v) is int and v > 0] or [0])


class AgentProbe:
    def __init__(self, agent_class, session_class, *, expected_game_id=None,
                 require_non_reset=True, max_events=256):
        if expected_game_id is not None and (
                not isinstance(expected_game_id, str) or not expected_game_id):
            raise ProbeFailure("EXPECTED_GAME_ID_INVALID")
        if type(max_events) is not int or not 16 <= max_events <= 4096:
            raise ProbeFailure("EVENT_BOUND_INVALID")
        self._expected_game_hash = (_digest(expected_game_id)
                                    if expected_game_id is not None else None)
        self._require_non_reset = bool(require_non_reset)
        self._max_events = max_events
        self._lock = threading.RLock()
        self._local = threading.local()
        self._events = []
        self._errors = set()
        self._responses = {}
        self._patches = []
        self._closed = False
        specs = [
            (agent_class, "_chat_completion",
             ("self", "messages", "tools", "request_timeout_seconds",
              "max_tokens", "enable_thinking")),
            (agent_class, "_dispatch_tool",
             ("self", "state_path", "name", "arguments")),
            (session_class, "_execute_action",
             ("self", "action", "batch_index", "batch_size", "generated_tokens",
              "flush_viewer_payload", "automatic")),
        ]
        originals = []
        for cls, name, required in specs:
            fn = getattr(cls, name)
            if getattr(fn, "_arc3_probe_wrapper", False):
                raise ProbeFailure("PROBE_ALREADY_INSTALLED")
            if inspect.iscoroutinefunction(fn):
                raise ProbeFailure("UNEXPECTED_ASYNC_METHOD")
            if tuple(inspect.signature(fn).parameters) != required:
                raise ProbeFailure("HARNESS_SIGNATURE_DRIFT")
            originals.append(fn)

        chat_original, dispatch_original, action_original = originals

        @functools.wraps(chat_original)
        def chat(agent, *args, **kwargs):
            # A failed newer call must not leave an older response eligible.
            with self._lock:
                self._responses.pop(id(agent), None)
            result = chat_original(agent, *args, **kwargs)
            try:
                message = result.message
                if not isinstance(message, dict):
                    raise ProbeFailure("MESSAGE_SHAPE_INVALID")
                python_calls = []
                calls = message.get("tool_calls") or []
                if not isinstance(calls, list):
                    raise ProbeFailure("TOOL_CALL_SHAPE_INVALID")
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    function = call.get("function")
                    if not isinstance(function, dict) or function.get("name") != "python":
                        continue
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    if isinstance(arguments, dict):
                        python_calls.append(_digest(arguments))
                event = self._event("model_response", {
                    "harness_message_sha256": _digest(message),
                    "python_argument_sha256": python_calls,
                    "output_tokens": _positive_output_tokens(getattr(result, "usage", None)),
                })
                with self._lock:
                    self._responses[id(agent)] = (agent, event)
            except Exception:
                self._error("MODEL_OBSERVATION_FAILED")
            return result

        @functools.wraps(dispatch_original)
        def dispatch(agent, *args, **kwargs):
            previous = getattr(self._local, "dispatch", None)
            context = None
            try:
                bound = inspect.signature(dispatch_original).bind(agent, *args, **kwargs)
                name = bound.arguments["name"]
                arguments = bound.arguments["arguments"]
                arg_hash = _digest(arguments) if isinstance(arguments, dict) else None
                with self._lock:
                    stored = self._responses.get(id(agent))
                    response = stored[1] if stored and stored[0] is agent else None
                linked = bool(response and name == "python" and
                              arg_hash in response["python_argument_sha256"] and
                              response["output_tokens"] > 0)
                start = self._event("tool_dispatch_begin", {
                    "tool_is_python": name == "python",
                    "arguments_sha256": arg_hash,
                    "response_event": response["sequence"] if response else None,
                    "matches_model_response": linked,
                })
                context = {"agent": agent, "response": response, "linked": linked,
                           "start": start, "actions": []}
                self._local.dispatch = context
            except Exception:
                self._error("DISPATCH_OBSERVATION_FAILED")
                self._local.dispatch = None
            try:
                result = dispatch_original(agent, *args, **kwargs)
                try:
                    step = getattr(result, "step_executed", None) is True
                    payload = json.loads(result.content)
                    json_object = isinstance(payload, dict)
                    tool_error = not json_object or bool(payload.get("error"))
                    clean = bool(json_object and payload.get("tool") == "python" and
                                 type(payload.get("returncode")) is int and
                                 payload["returncode"] == 0 and not tool_error)
                    qualified = [a for a in context["actions"] if a["qualified"]] if context else []
                    self._event("tool_dispatch_return", {
                        "dispatch_event": context["start"]["sequence"] if context else None,
                        "step_executed": step,
                        "clean_python_completion": clean,
                        "tool_error": tool_error,
                        "result_sha256": _digest(payload),
                        "qualified_action_events": [a["sequence"] for a in qualified] if step and clean else [],
                    })
                except Exception:
                    self._error("DISPATCH_RESULT_OBSERVATION_FAILED")
                return result
            finally:
                self._local.dispatch = previous

        @functools.wraps(action_original)
        def action(session, *args, **kwargs):
            before = None
            try:
                before = len(session.game.game_run.history)
            except Exception:
                self._error("ACTION_HISTORY_OBSERVATION_FAILED")
            result = action_original(session, *args, **kwargs)
            try:
                bound = inspect.signature(action_original).bind(session, *args, **kwargs)
                bound.apply_defaults()
                context = getattr(self._local, "dispatch", None)
                run = session.game.game_run
                game_id = run.game_id
                if not isinstance(game_id, str) or not game_id:
                    raise ProbeFailure("GAME_ID_INVALID")
                game_hash = _digest(game_id)
                after = len(run.history)
                payload_ok = isinstance(result, dict) and result.get("executed") is True
                automatic = (bound.arguments["automatic"] is not False or
                             not isinstance(result, dict) or result.get("automatic") is not False)
                action_name = result.get("action_name") if isinstance(result, dict) else None
                actual_action = bound.arguments["action"].id.name
                name_ok = isinstance(action_name, str) and action_name == actual_action
                non_reset = name_ok and action_name != "RESET"
                same_agent = bool(context and session.analyzer is context["agent"])
                expected = self._expected_game_hash is None or game_hash == self._expected_game_hash
                appended_once = type(before) is int and after == before + 1
                qualified = bool(context and context["linked"] and same_agent and expected and
                                 payload_ok and not automatic and appended_once and name_ok and
                                 (non_reset or not self._require_non_reset))
                event = self._event("engine_action", {
                    "game_id_sha256": game_hash,
                    "expected_game": expected,
                    "response_event": context["response"]["sequence"] if context and context["response"] else None,
                    "dispatch_event": context["start"]["sequence"] if context else None,
                    "same_agent": same_agent,
                    "executed": payload_ok,
                    "automatic": automatic,
                    "non_reset": non_reset,
                    "action_name": action_name if name_ok else None,
                    "history_before": before,
                    "history_after": after,
                    "appended_once": appended_once,
                    "qualified": qualified,
                })
                if context is not None:
                    context["actions"].append(event)
            except Exception:
                self._error("ACTION_OBSERVATION_FAILED")
            return result

        for (cls, name, _), original, wrapper in zip(specs, originals, (chat, dispatch, action)):
            wrapper._arc3_probe_wrapper = True
            setattr(cls, name, wrapper)
            self._patches.append((cls, name, original, wrapper))

    def _error(self, code):
        with self._lock:
            self._errors.add(code)

    def _event(self, kind, fields):
        with self._lock:
            if len(self._events) >= self._max_events:
                self._errors.add("EVENT_BOUND_EXCEEDED")
                raise ProbeFailure("EVENT_BOUND_EXCEEDED")
            event = {"sequence": len(self._events) + 1, "kind": kind, **fields}
            self._events.append(event)
            return event

    def summary(self):
        with self._lock:
            events = json.loads(json.dumps(self._events))
            errors = sorted(self._errors)
        returned = {n for e in events if e["kind"] == "tool_dispatch_return"
                    for n in e["qualified_action_events"]}
        actions = [e for e in events if e["kind"] == "engine_action" and e["sequence"] in returned]
        games = sorted({e["game_id_sha256"] for e in actions})
        passed = bool(actions and len(games) == 1 and not errors)
        return {"schema": "arc3-model-tool-action-probe-v1",
                "status": "PASS" if passed else "HOLD",
                "response_boundary": "original ToolAgent._chat_completion return after native normalization",
                "raw_wire_response_observed": False,
                "native_parser_flags_changed": False,
                "expected_game_id_sha256": self._expected_game_hash,
                "require_non_reset": self._require_non_reset,
                "model_response_count": sum(e["kind"] == "model_response" for e in events),
                "linked_action_count": len(actions), "linked_game_id_sha256": games,
                "errors": errors, "closed": self._closed, "events": events,
                "terminal_game_and_resource_checks_owned_by_driver": True}

    def assert_meaningful_step(self):
        result = self.summary()
        if result["status"] != "PASS":
            raise ProbeFailure("NO_QUALIFIED_MODEL_TOOL_ACTION")
        return result

    def close(self):
        if self._closed:
            return
        # Do not clobber another owner's class mutation.
        if any(getattr(cls, name) is not wrapper for cls, name, _, wrapper in self._patches):
            self._error("WRAPPER_OWNERSHIP_DRIFT")
            raise ProbeFailure("WRAPPER_OWNERSHIP_DRIFT")
        for cls, name, original, _ in reversed(self._patches):
            setattr(cls, name, original)
        self._closed = True
        self._responses.clear()


def install_probe(*, agent_class=None, session_class=None, expected_game_id=None,
                  require_non_reset=True, max_events=256):
    """Install scoped observers; inject invented classes for offline fixtures."""
    if (agent_class is None) != (session_class is None):
        raise ProbeFailure("BOTH_CLASSES_REQUIRED")
    if agent_class is None:
        # Native-only integration; offline fixtures never import these modules.
        from inference.agent.tool_agent import ToolAgent
        from inference.framework.solver import _HarnessGameSession
        agent_class, session_class = ToolAgent, _HarnessGameSession
    return AgentProbe(agent_class, session_class, expected_game_id=expected_game_id,
                      require_non_reset=require_non_reset, max_events=max_events)
