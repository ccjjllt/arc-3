"""Bounded observation of existing model calls and priority-gate boundaries.

Install identically in both experiment arms. No request, retry, payload, timeout,
priority or response body is created/changed/read by this observer. Session.play
owns a thread-local ledger; hooks add no locks and never write files. Snapshot
after worker drain for a final report (a live snapshot is explicitly provisional).
"""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from functools import wraps
import hashlib
import importlib
import inspect
import itertools
import math
import threading
import time
from typing import Any


def generated_tokens_from_usage(usage: Any) -> int | None:
    """Use the baseline's key order without reading a response or adding tokens."""
    if not isinstance(usage, dict):
        return None
    for key in ("completion_tokens", "output_tokens", "generated_tokens"):
        value = usage.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return max(0, int(value))
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def _finite_number(value: Any) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def _function_hash(function: Any) -> str | None:
    try:
        return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()
    except (OSError, TypeError):
        return None


class _RequestsProxy:
    """Intercept only tool_agent's requests.post lookup, not the global module."""

    def __init__(self, original: Any, post: Any) -> None:
        self._original = original
        self.post = post

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class InferenceTimingPatch:
    def __init__(self, tool_agent_class: type, session_class: type, *,
                 max_sessions: int, max_events_per_session: int) -> None:
        if any(type(n) is not int or n < 1 for n in (max_sessions, max_events_per_session)):
            raise ValueError("Timing limits must be positive integers.")
        self.tool_agent_class = tool_agent_class
        self.session_class = session_class
        self.limits = dict(max_sessions=max_sessions, max_events_per_session=max_events_per_session)
        self._agent_module = importlib.import_module(tool_agent_class.__module__)
        self._gate_class = self._agent_module._PriorityGate
        self._original_requests = self._agent_module.requests
        self._original_post = self._original_requests.post
        self._original_play = session_class.play
        self._original_chat = tool_agent_class._chat_completion
        self._original_gate = {name: getattr(self._gate_class, name) for name in
                               ("acquire", "handover", "release", "_enqueue_and_wait", "_pump")}
        self._source_hashes = {"session.play": _function_hash(self._original_play),
                               "agent._chat_completion": _function_hash(self._original_chat),
                               **{f"gate.{k}": _function_hash(v) for k, v in self._original_gate.items()}}
        self._local = threading.local()
        self._serial = itertools.count(1)
        self._sessions: dict[int, dict[str, Any]] = {}
        self._origin = time.monotonic()
        self._origin_utc = datetime.now(timezone.utc).isoformat()

    def _now(self) -> float:
        return time.monotonic() - self._origin

    def _safe_now(self) -> float | None:
        try:
            return _finite_number(self._now())
        except Exception:
            return None

    @staticmethod
    def _difference(start: float | None, end: float | None) -> float | None:
        if start is None or end is None:
            return None
        return _finite_number(end - start)

    def _new_context(self, session: Any) -> dict[str, Any] | None:
        serial = next(self._serial)
        # Registration happens before gate admission. Ledger ownership stays with
        # this play thread. CPython next(count) allocates unique serials without
        # adding another lock inside any of the original gate critical sections.
        if serial > self.limits["max_sessions"]:
            return None
        run = getattr(session.game, "game_run", None)
        started = _finite_number(getattr(session, "started_at", None))
        context = {
            "session_id": f"s{serial:04d}",
            "game_id": str(getattr(run, "game_id", "unknown"))[:200],
            "game_index": getattr(session, "game_index", None),
            "pass_index": getattr(session, "pass_index", None),
            "session_started_t": None if started is None else started - self._origin,
            "events": deque(maxlen=self.limits["max_events_per_session"]),
            "counts": Counter(), "durations": Counter(), "first": {},
            "event_count": 0, "request_serial": 0, "gate_serial": 0,
            "held_since_t": None, "play_active": True,
        }
        self._sessions[serial] = context
        return context

    def _record(self, context: dict[str, Any] | None, kind: str, *,
                stamp: float | None = None, **fields: Any) -> None:
        """Fail-open observer only; caller return values/exceptions always win."""
        if context is None:
            return
        try:
            stamp = self._now() if stamp is None else stamp
            context["event_count"] += 1
            context["events"].append({"seq": context["event_count"], "t": stamp,
                                       "kind": kind, **fields})
            context["counts"][kind] += 1
            context["first"].setdefault(kind, stamp)
            duration = fields.get("duration_s")
            if duration is not None:
                context["durations"][kind] += duration
            if kind == "chat_return":
                tokens = fields.get("generated_tokens")
                context["counts"]["responses_with_known_tokens" if tokens is not None
                                   else "responses_with_unknown_tokens"] += 1
                if tokens is not None:
                    context["counts"]["observed_generated_tokens"] += tokens
            elif kind == "gate_admitted_return":
                if context["held_since_t"] is not None:
                    context["counts"]["unpaired_admission"] += 1
                context["held_since_t"] = stamp
            elif kind == "gate_release_credit":
                held = context["held_since_t"]
                if held is not None:
                    context["durations"]["observed_slot_held"] += stamp - held
                    context["held_since_t"] = None
                else:
                    context["counts"]["unpaired_release"] += 1
        except Exception:
            # In particular, observation cannot mask a successful action/request
            # or replace the exception from the original execution path.
            try:
                context["counts"]["observer_record_errors"] += 1
            except Exception:
                pass
            return

    def snapshot(self) -> dict[str, Any]:
        now = self._now()
        # count's reduction exposes its next value without advancing it, avoiding
        # an additional shared read/modify/write counter in concurrent play starts.
        seen_sessions = self._serial.__reduce__()[1][0] - 1
        sessions = []
        for _, context in sorted(list(self._sessions.items())):
            first = dict(context["first"])
            first_http = first.get("http_attempt_begin")
            started = context["session_started_t"]
            sessions.append({
                **{key: context[key] for key in ("session_id", "game_id", "game_index", "pass_index",
                                                  "session_started_t", "play_active", "held_since_t")},
                "first_times": first, "counts": dict(context["counts"]),
                "durations_s": dict(context["durations"]),
                "first_http_delay_from_session_start_s": (
                    first_http - started if first_http is not None and started is not None else None),
                "events_observed": context["event_count"],
                "events_dropped": max(0, context["event_count"] - self.limits["max_events_per_session"]),
                "events": [dict(event) for event in list(context["events"])],
            })
        return {
            "observer": "inference-timing-v1", "limits": dict(self.limits),
            "clock_origin_monotonic": self._origin, "clock_origin_utc": self._origin_utc,
            "snapshot_t": now, "provisional": any(s["play_active"] for s in sessions),
            "sessions_seen": seen_sessions, "sessions_recorded": len(sessions),
            "sessions_omitted_by_limit": max(0, seen_sessions - self.limits["max_sessions"]),
            "source_sha256": dict(self._source_hashes), "sessions": sessions,
            "semantics": {
                "clock": "All t values are seconds since observer install; original session.started_at is on the same monotonic clock.",
                "chat": "_chat_completion entry to original return/exception: includes payload build, retries, stream consumption and parsing. Includes summary calls; tools_present only labels whether a tools argument is supplied, not the call's purpose.",
                "http": "Entry to existing requests.post, then original return/exception. A streamed return may contain only headers; this does not measure server decode or full generation latency. No body/headers/payload is inspected.",
                "gate_wait": "Original _enqueue_and_wait entry to normal return, under the existing Condition: includes enqueue/pump/wait/wakeup, not just Condition.wait sleep. Admission is caller-observed ownership, not the earlier pump selection instant.",
                "release": "handover: enqueue entry immediately after original _free increment; final release: pump entry immediately after original _free increment. Neither hook performs release itself.",
                "slot_held": "Sum of admitted-return to release-credit intervals; includes model calls, Python work and idle time while the game owns a slot. Open intervals are reported separately.",
                "tokens": "Usage on successful original _chat_completion result only; null when absent. Partial/failed generation is unknown, not zero. No counters in the solver are changed.",
                "boundedness": "At most max_sessions ledgers; newest max_events_per_session events each. First timestamps and all-event aggregate counters survive event eviction.",
                "threading": "No added locks. Session ledgers have one play-thread writer; snapshot after drain for final consistency. Calls outside an observed play/chat scope pass through.",
            },
        }

    def install(self) -> None:
        patch = self

        @wraps(self._original_play)
        def play(session: Any, *args: Any, **kwargs: Any) -> Any:
            previous = getattr(patch._local, "session", None)
            try:
                context = patch._new_context(session)
            except Exception:
                context = None
            patch._local.session = context
            patch._record(context, "play_begin")
            try:
                result = patch._original_play(session, *args, **kwargs)
            except BaseException as exc:
                patch._record(context, "play_exception", exception_type=type(exc).__name__)
                raise
            else:
                patch._record(context, "play_return")
                return result
            finally:
                if context is not None:
                    context["play_active"] = False
                patch._local.session = previous

        @wraps(self._original_chat)
        def chat(agent: Any, *args: Any, **kwargs: Any) -> Any:
            context = getattr(patch._local, "session", None)
            if context is None:
                return patch._original_chat(agent, *args, **kwargs)
            previous = getattr(patch._local, "request", None)
            try:
                context["request_serial"] += 1
                request = {"id": context["request_serial"], "attempt": 0}
                patch._local.request = request
            except Exception:
                return patch._original_chat(agent, *args, **kwargs)
            started = patch._safe_now()
            patch._record(context, "chat_begin", stamp=started, request_id=request["id"],
                          tools_present=kwargs.get("tools") is not None)
            try:
                result = patch._original_chat(agent, *args, **kwargs)
            except BaseException as exc:
                patch._record(context, "chat_exception", request_id=request["id"],
                              duration_s=patch._difference(started, patch._safe_now()), exception_type=type(exc).__name__)
                raise
            else:
                ended = patch._safe_now()
                try:
                    tokens = generated_tokens_from_usage(getattr(result, "usage", None))
                    reason = str(getattr(result, "finish_reason", ""))[:64]
                except Exception:
                    tokens, reason = None, None
                patch._record(context, "chat_return", stamp=ended, request_id=request["id"],
                              duration_s=patch._difference(started, ended), generated_tokens=tokens, finish_reason=reason)
                return result
            finally:
                patch._local.request = previous

        @wraps(self._original_post)
        def post(*args: Any, **kwargs: Any) -> Any:
            context = getattr(patch._local, "session", None)
            request = getattr(patch._local, "request", None)
            if context is None or request is None:
                return patch._original_post(*args, **kwargs)
            try:
                request["attempt"] += 1
                fields = {"request_id": request["id"], "attempt": request["attempt"]}
            except Exception:
                return patch._original_post(*args, **kwargs)
            started = patch._safe_now()
            patch._record(context, "http_attempt_begin", stamp=started, **fields)
            try:
                result = patch._original_post(*args, **kwargs)
            except BaseException as exc:
                patch._record(context, "http_attempt_exception", **fields,
                              duration_s=patch._difference(started, patch._safe_now()), exception_type=type(exc).__name__)
                raise
            else:
                ended = patch._safe_now()
                patch._record(context, "http_attempt_return", stamp=ended, **fields,
                              duration_s=patch._difference(started, ended))
                return result

        def gate_outer(name: str) -> Any:
            original = patch._original_gate[name]

            @wraps(original)
            def invoke(gate: Any, *args: Any, **kwargs: Any) -> Any:
                context = getattr(patch._local, "session", None)
                if context is None:
                    return original(gate, *args, **kwargs)
                previous = getattr(patch._local, "gate", None)
                try:
                    context["gate_serial"] += 1
                    operation = {"name": name, "id": context["gate_serial"], "object": gate}
                    patch._local.gate = operation
                except Exception:
                    return original(gate, *args, **kwargs)
                started = patch._safe_now()
                patch._record(context, "gate_call_begin", stamp=started,
                              operation=name, gate_call_id=operation["id"])
                try:
                    result = original(gate, *args, **kwargs)
                except BaseException as exc:
                    patch._record(context, "gate_call_exception", operation=name,
                                  gate_call_id=operation["id"], duration_s=patch._difference(started, patch._safe_now()),
                                  exception_type=type(exc).__name__)
                    raise
                else:
                    patch._record(context, "gate_call_return", operation=name,
                                  gate_call_id=operation["id"], duration_s=patch._difference(started, patch._safe_now()))
                    return result
                finally:
                    patch._local.gate = previous
            return invoke

        @wraps(self._original_gate["_enqueue_and_wait"])
        def enqueue(gate: Any, *args: Any, **kwargs: Any) -> Any:
            context = getattr(patch._local, "session", None)
            operation = getattr(patch._local, "gate", None)
            observed = context is not None and operation is not None and operation["object"] is gate
            if not observed:
                return patch._original_gate["_enqueue_and_wait"](gate, *args, **kwargs)
            fields = {"operation": operation["name"], "gate_call_id": operation["id"]}
            started = patch._safe_now()
            if operation["name"] == "handover":
                patch._record(context, "gate_release_credit", stamp=started, **fields)
            patch._record(context, "gate_enqueue_begin", stamp=started, **fields)
            result = patch._original_gate["_enqueue_and_wait"](gate, *args, **kwargs)
            ended = patch._safe_now()
            patch._record(context, "gate_admitted_return", stamp=ended,
                          duration_s=patch._difference(started, ended), **fields)
            return result

        @wraps(self._original_gate["_pump"])
        def pump(gate: Any, *args: Any, **kwargs: Any) -> Any:
            context = getattr(patch._local, "session", None)
            operation = getattr(patch._local, "gate", None)
            if (context is not None and operation is not None
                    and operation["object"] is gate and operation["name"] == "release"):
                patch._record(context, "gate_release_credit", operation="release",
                              gate_call_id=operation["id"])
            return patch._original_gate["_pump"](gate, *args, **kwargs)

        self.session_class.play = play
        self.tool_agent_class._chat_completion = chat
        self._agent_module.requests = _RequestsProxy(self._original_requests, post)
        for name in ("acquire", "handover", "release"):
            setattr(self._gate_class, name, gate_outer(name))
        self._gate_class._enqueue_and_wait = enqueue
        self._gate_class._pump = pump


def install_inference_timing(
    tool_agent_class: type | None = None, session_class: type | None = None, *,
    max_sessions: int = 128, max_events_per_session: int = 4096,
) -> InferenceTimingPatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if session_class is None:
        session_class = importlib.import_module("inference.framework.solver")._HarnessGameSession
    existing = getattr(tool_agent_class, "_research_inference_timing_patch", None)
    limits = dict(max_sessions=max_sessions, max_events_per_session=max_events_per_session)
    if existing is not None:
        if existing.session_class is not session_class or existing.limits != limits:
            raise ValueError("Timing observer is already installed with different settings.")
        return existing
    patch = InferenceTimingPatch(tool_agent_class, session_class, **limits)
    patch.install()
    tool_agent_class._research_inference_timing_patch = patch
    return patch
