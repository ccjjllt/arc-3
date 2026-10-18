"""Bounded observation of the original normalized model/tool/action boundary.

No model, tool, or engine result is replaced. Only hashes and counters are
retained, with one four-event clean witness per expected game. Ordinary request
failures are counted separately from observation failures. Native classes are
imported only by install_probe when fixture classes are not supplied.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import json
import threading
import weakref


class ProbeFailure(RuntimeError):
    """Fixed diagnostic only; never contains model content."""


def _digest(value, byte_limit=2 * 1024 * 1024):
    digest = hashlib.sha256()
    size = 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False)
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode("utf-8")
        size += len(encoded)
        if size > byte_limit:
            raise ProbeFailure("OBSERVATION_BYTE_BOUND_EXCEEDED")
        digest.update(encoded)
    return digest.hexdigest()


def _output_tokens(usage):
    if not isinstance(usage, dict):
        return 0
    return max([value for key in ("completion_tokens", "output_tokens", "generated_tokens")
                if type(value := usage.get(key)) is int and value > 0] or [0])


class FullGameProbe:
    def __init__(self, agent_class, session_class, *, expected_game_ids,
                 max_games=128, max_witness_events=4096):
        if type(max_games) is not int or not 1 <= max_games <= 128:
            raise ProbeFailure("GAME_BOUND_INVALID")
        if (not isinstance(expected_game_ids, (list, tuple))
                or not 1 <= len(expected_game_ids) <= max_games
                or any(not isinstance(game, str) or not game
                       or len(game.encode()) > 4096 for game in expected_game_ids)
                or len(set(expected_game_ids)) != len(expected_game_ids)):
            raise ProbeFailure("EXPECTED_GAME_IDS_INVALID")
        if (type(max_witness_events) is not int
                or not 4 * len(expected_game_ids) <= max_witness_events <= 4096):
            raise ProbeFailure("WITNESS_BOUND_INVALID")
        self._max_games = max_games
        self._max_witness_events = max_witness_events
        self._max_python_calls = 64
        self._lock = threading.RLock()
        self._local = threading.local()
        self._errors = set()
        self._responses = {}
        self._active_dispatches = 0
        self._sequence = 0
        self._closed = False
        self._patches = []
        self._counts = {name: 0 for name in (
            "model_calls_started", "model_calls_returned", "model_calls_failed",
            "model_responses_observed", "model_output_tokens_observed",
            "tool_dispatch_calls_started", "tool_dispatch_calls_returned", "tool_dispatch_calls_failed",
            "clean_python_returns", "action_calls_started", "action_calls_returned",
            "action_calls_failed", "engine_actions_observed", "qualified_clean_model_actions")}
        self._games = {_digest(game): {
            "engine_actions_observed": 0, "executed_actions": 0,
            "non_reset_executed_actions": 0, "qualified_action_candidates": 0,
            "qualified_clean_action_count": 0, "first_witness": None,
        } for game in expected_game_ids}
        specs = [
            (agent_class, "_chat_completion",
             ("self", "messages", "tools", "request_timeout_seconds", "max_tokens", "enable_thinking")),
            (agent_class, "_dispatch_tool", ("self", "state_path", "name", "arguments")),
            (session_class, "_execute_action",
             ("self", "action", "batch_index", "batch_size", "generated_tokens",
              "flush_viewer_payload", "automatic")),
        ]
        originals = []
        for cls, name, signature in specs:
            function = getattr(cls, name)
            if getattr(function, "_arc3_probe_wrapper", False):
                raise ProbeFailure("PROBE_ALREADY_INSTALLED")
            if inspect.iscoroutinefunction(function) or tuple(inspect.signature(function).parameters) != signature:
                raise ProbeFailure("HARNESS_SIGNATURE_DRIFT")
            originals.append(function)
        chat_original, dispatch_original, action_original = originals

        @functools.wraps(chat_original)
        def chat(agent, *args, **kwargs):
            key = (threading.get_ident(), id(agent))
            with self._lock:
                self._counts["model_calls_started"] += 1
                self._responses.pop(key, None)  # A failed newer call invalidates the old response.
            try:
                result = chat_original(agent, *args, **kwargs)
            except BaseException:
                self._count("model_calls_failed")
                raise
            self._count("model_calls_returned")
            try:
                message = result.message
                if not isinstance(message, dict):
                    raise ProbeFailure("MESSAGE_SHAPE_INVALID")
                calls = message.get("tool_calls") or []
                if not isinstance(calls, list) or len(calls) > self._max_python_calls:
                    raise ProbeFailure("TOOL_CALL_SHAPE_OR_BOUND_INVALID")
                python_hashes = []
                for call in calls:
                    function = call.get("function") if isinstance(call, dict) else None
                    if not isinstance(function, dict) or function.get("name") != "python":
                        continue
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        if len(arguments.encode()) > 2 * 1024 * 1024:
                            raise ProbeFailure("OBSERVATION_BYTE_BOUND_EXCEEDED")
                        arguments = json.loads(arguments)
                    if isinstance(arguments, dict):
                        python_hashes.append(_digest(arguments))
                event = self._event("model_response", {
                    "harness_message_sha256": _digest(message),
                    "python_argument_sha256": python_hashes,
                    "output_tokens": _output_tokens(getattr(result, "usage", None)),
                })
                agent_ref = weakref.ref(agent)  # Do not retain agents and their prompt histories.
                with self._lock:
                    self._counts["model_responses_observed"] += 1
                    self._counts["model_output_tokens_observed"] += event["output_tokens"]
                    if len(self._responses) >= self._max_games:
                        self._responses = {k: v for k, v in self._responses.items()
                                           if v[0]() is not None}
                    if len(self._responses) >= self._max_games:
                        raise ProbeFailure("RESPONSE_CONTEXT_BOUND_EXCEEDED")
                    self._responses[key] = (agent_ref, event)
            except Exception:
                self._error("MODEL_OBSERVATION_FAILED")
            return result

        @functools.wraps(dispatch_original)
        def dispatch(agent, *args, **kwargs):
            self._count("tool_dispatch_calls_started")
            previous = getattr(self._local, "dispatch", None)
            context = None
            try:
                bound = inspect.signature(dispatch_original).bind(agent, *args, **kwargs)
                name, arguments = bound.arguments["name"], bound.arguments["arguments"]
                arg_hash = _digest(arguments) if isinstance(arguments, dict) else None
                with self._lock:
                    stored = self._responses.get((threading.get_ident(), id(agent)))
                    response = stored[1] if stored and stored[0]() is agent else None
                    if self._active_dispatches >= self._max_games:
                        raise ProbeFailure("ACTIVE_DISPATCH_BOUND_EXCEEDED")
                    start = self._event("tool_dispatch_begin", {
                        "tool_is_python": name == "python", "arguments_sha256": arg_hash,
                        "response_event": response["sequence"] if response else None,
                        "matches_model_response": bool(response and name == "python"
                            and arg_hash in response["python_argument_sha256"] and response["output_tokens"] > 0),
                    })
                    context = {"agent_ref": weakref.ref(agent), "response": response,
                               "start": start, "candidates": {}}
                    self._active_dispatches += 1
                self._local.dispatch = context
            except Exception:
                self._error("DISPATCH_OBSERVATION_FAILED")
                self._local.dispatch = None
            try:
                try:
                    result = dispatch_original(agent, *args, **kwargs)
                except BaseException:
                    self._count("tool_dispatch_calls_failed")
                    raise
                self._count("tool_dispatch_calls_returned")
                try:
                    if not isinstance(result.content, str) or len(result.content.encode()) > 2 * 1024 * 1024:
                        raise ProbeFailure("TOOL_RESULT_SHAPE_OR_BOUND_INVALID")
                    payload = json.loads(result.content)
                    object_result = isinstance(payload, dict)
                    tool_error = not object_result or bool(payload.get("error"))
                    clean = bool(object_result and payload.get("tool") == "python"
                                 and type(payload.get("returncode")) is int
                                 and payload["returncode"] == 0 and not tool_error)
                    step = getattr(result, "step_executed", None) is True
                    returned = self._event("tool_dispatch_return", {
                        "dispatch_event": context["start"]["sequence"] if context else None,
                        "step_executed": step, "clean_python_completion": clean,
                        "tool_error": tool_error, "result_sha256": _digest(payload),
                    })
                    with self._lock:
                        if clean:
                            self._counts["clean_python_returns"] += 1
                        if context and clean and step:
                            for game_hash, candidate in context["candidates"].items():
                                game = self._games[game_hash]
                                count = candidate["count"]
                                game["qualified_clean_action_count"] += count
                                self._counts["qualified_clean_model_actions"] += count
                                if game["first_witness"] is None:
                                    action_event = candidate["first_event"]
                                    end = dict(returned, qualified_action_events=[action_event["sequence"]],
                                               qualified_action_events_are_sampled=True,
                                               qualified_action_count_in_dispatch=count)
                                    game["first_witness"] = [context["response"], context["start"], action_event, end]
                except Exception:
                    self._error("DISPATCH_RESULT_OBSERVATION_FAILED")
                return result
            finally:
                self._local.dispatch = previous
                if context is not None:
                    with self._lock:
                        self._active_dispatches -= 1

        @functools.wraps(action_original)
        def action(session, *args, **kwargs):
            self._count("action_calls_started")
            before = None
            try:
                before = len(session.game.game_run.history)
            except Exception:
                self._error("ACTION_HISTORY_OBSERVATION_FAILED")
            try:
                result = action_original(session, *args, **kwargs)
            except BaseException:
                self._count("action_calls_failed")
                raise
            self._count("action_calls_returned")
            try:
                bound = inspect.signature(action_original).bind(session, *args, **kwargs)
                bound.apply_defaults()
                context = getattr(self._local, "dispatch", None)
                run = session.game.game_run
                if not isinstance(run.game_id, str) or not run.game_id:
                    raise ProbeFailure("GAME_ID_INVALID")
                game_hash = _digest(run.game_id)
                if game_hash not in self._games:
                    raise ProbeFailure("UNEXPECTED_GAME_ID")
                after = len(run.history)
                executed = isinstance(result, dict) and result.get("executed") is True
                automatic = (bound.arguments["automatic"] is not False
                             or not isinstance(result, dict) or result.get("automatic") is not False)
                name = result.get("action_name") if isinstance(result, dict) else None
                name_ok = isinstance(name, str) and name == bound.arguments["action"].id.name
                non_reset = name_ok and name != "RESET"
                same_agent = bool(context and session.analyzer is context["agent_ref"]())
                appended = type(before) is int and after == before + 1
                qualified = bool(context and context["start"]["matches_model_response"]
                                 and same_agent and executed and not automatic and appended and non_reset)
                event = self._event("engine_action", {
                    "game_id_sha256": game_hash, "expected_game": True,
                    "response_event": context["response"]["sequence"] if context and context["response"] else None,
                    "dispatch_event": context["start"]["sequence"] if context else None,
                    "same_agent": same_agent, "executed": executed, "automatic": automatic,
                    "non_reset": non_reset, "action_name": name if name_ok else None,
                    "history_before": before, "history_after": after,
                    "appended_once": appended, "qualified": qualified,
                })
                with self._lock:
                    self._counts["engine_actions_observed"] += 1
                    game = self._games[game_hash]
                    game["engine_actions_observed"] += 1
                    game["executed_actions"] += int(executed)
                    game["non_reset_executed_actions"] += int(executed and non_reset)
                    if qualified:
                        game["qualified_action_candidates"] += 1
                        candidate = context["candidates"].get(game_hash)
                        if candidate is None:
                            context["candidates"][game_hash] = {"count": 1, "first_event": event}
                        else:
                            candidate["count"] += 1
            except Exception:
                self._error("ACTION_OBSERVATION_FAILED")
            return result

        for (cls, name, _), original, wrapper in zip(specs, originals, (chat, dispatch, action)):
            wrapper._arc3_probe_wrapper = True
            setattr(cls, name, wrapper)
            self._patches.append((cls, name, original, wrapper))

    def _count(self, name):
        with self._lock:
            self._counts[name] += 1

    def _error(self, code):
        with self._lock:
            self._errors.add(code)

    def _event(self, kind, fields):
        with self._lock:
            self._sequence += 1
            return {"sequence": self._sequence, "kind": kind, **fields}

    def summary(self):
        with self._lock:
            games = json.loads(json.dumps(self._games))
            counts = dict(self._counts)
            errors = sorted(self._errors)
            missing = sorted(key for key, value in games.items() if value["first_witness"] is None)
            retained = sum(len(value["first_witness"] or []) for value in games.values())
            return {
                "schema": "arc3-full-game-model-tool-action-probe-v1",
                "status": "PASS" if not missing and not errors else "HOLD",
                "coverage_complete": not missing,
                "expected_game_id_sha256": sorted(games), "missing_game_id_sha256": missing,
                "response_boundary": "original ToolAgent._chat_completion return after native normalization",
                "raw_wire_response_observed": False, "native_parser_flags_changed": False,
                "require_non_reset": True, "closed": self._closed,
                "observation_errors": errors, "errors": errors,
                "global_counts": counts, "per_game": games,
                "sampling": "Counters cover every observed call/action; only the first clean four-event witness per game is retained.",
                "storage": {"retained_witness_events": retained, "max_witness_events": self._max_witness_events,
                            "response_contexts": len(self._responses), "active_dispatches": self._active_dispatches,
                            "max_games": self._max_games, "max_response_contexts": self._max_games,
                            "max_active_dispatches": self._max_games,
                            "max_candidate_games_per_dispatch": len(self._games),
                            "max_python_calls_per_response": self._max_python_calls},
                "terminal_game_and_resource_checks_owned_by_driver": True,
            }

    def assert_meaningful_coverage(self):
        result = self.summary()
        if result["status"] != "PASS":
            raise ProbeFailure("INCOMPLETE_CLEAN_MODEL_ACTION_COVERAGE")
        return result

    def close(self):
        with self._lock:
            if self._closed:
                return
            if any(self._counts[prefix + "_started"] != self._counts[prefix + "_returned"] + self._counts[prefix + "_failed"]
                   for prefix in ("model_calls", "tool_dispatch_calls", "action_calls")):
                self._errors.add("ACTIVE_OBSERVATION_AT_CLOSE")
                raise ProbeFailure("ACTIVE_OBSERVATION_AT_CLOSE")
            if any(getattr(cls, name) is not wrapper for cls, name, _, wrapper in self._patches):
                self._errors.add("WRAPPER_OWNERSHIP_DRIFT")
                raise ProbeFailure("WRAPPER_OWNERSHIP_DRIFT")
            for cls, name, original, _ in reversed(self._patches):
                setattr(cls, name, original)
            self._closed = True
            self._responses.clear()


def install_probe(*, expected_game_ids, agent_class=None, session_class=None,
                  max_games=128, max_witness_events=4096):
    if (agent_class is None) != (session_class is None):
        raise ProbeFailure("BOTH_CLASSES_REQUIRED")
    if agent_class is None:
        from inference.agent.tool_agent import ToolAgent
        from inference.framework.solver import _HarnessGameSession
        agent_class, session_class = ToolAgent, _HarnessGameSession
    return FullGameProbe(agent_class, session_class, expected_game_ids=expected_game_ids,
                         max_games=max_games, max_witness_events=max_witness_events)
