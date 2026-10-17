"""Stop new requests after session cancellation or the shared soft deadline.

Installed identically in both research arms. This changes admission after stop,
not request payloads, timeouts, retries before stop, or in-flight responses. A
client transport-entry check cannot guarantee the server's receive time or
cancel a request already sent. The original session owns all finalization and
slot release; this patch never releases/reacquires a priority slot itself.
"""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from functools import wraps
import hashlib
import importlib
import inspect
import math
import threading
import time
from typing import Any


class RequestDeadlineReached(BaseException):
    """Private control flow: bypass original retry/generic-error handlers."""

    def __init__(self, owner: Any, reason: str) -> None:
        super().__init__(reason)
        self.owner = owner
        self.reason = reason


class RequestDeadlineCheckFailed(BaseException):
    """A failed stop check must not fall through to an HTTP request."""


class _RequestsProxy:
    def __init__(self, original: Any, post: Any) -> None:
        self._original = original
        self.post = post

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def _source(function: Any) -> dict[str, Any]:
    original = inspect.unwrap(function)
    try:
        digest = hashlib.sha256(inspect.getsource(original).encode()).hexdigest()
    except (TypeError, OSError):
        digest = None
    return {"signature": str(inspect.signature(original)), "sha256": digest,
            "module": getattr(original, "__module__", None),
            "qualname": getattr(original, "__qualname__", None)}


class RequestDeadlinePatch:
    def __init__(self, tool_agent_class: type, session_class: type, *, max_events: int) -> None:
        if type(max_events) is not int or max_events < 1:
            raise ValueError("max_events must be a positive integer")
        self.tool_agent_class = tool_agent_class
        self.session_class = session_class
        self.max_events = max_events
        self._module = importlib.import_module(tool_agent_class.__module__)
        self._original_play = session_class.play
        self._original_handover = tool_agent_class._maybe_handover
        self._original_chat = tool_agent_class._chat_completion
        self._original_requests = self._module.requests
        self._original_post = self._original_requests.post
        self._source = {"session.play": _source(self._original_play),
                        "session.should_stop": _source(session_class.should_stop),
                        "agent._maybe_handover": _source(self._original_handover),
                        "agent._chat_completion": _source(self._original_chat),
                        "requests.post": _source(self._original_post)}
        for function, required in ((self._original_chat, {"self", "messages", "tools"}),
                                   (self._original_handover, {"self"}),
                                   (self._original_play, {"self"})):
            if not required <= set(inspect.signature(inspect.unwrap(function)).parameters):
                raise ValueError(f"Unsupported deadline hook signature: {function!r}")
        self._local = threading.local()
        self._lock = threading.Lock()
        self._counts: Counter = Counter()
        self._boundary_counts: Counter = Counter()
        self._events: deque = deque(maxlen=max_events)
        self._active = 0
        self._origin = time.monotonic()
        self._origin_utc = datetime.now(timezone.utc).isoformat()
        self._installed = False

    def _record(self, kind: str, **fields: Any) -> None:
        # Diagnostic failures must not replace an original exception or cancel.
        try:
            event = {"t": time.monotonic() - self._origin, "kind": kind, **fields}
            with self._lock:
                self._counts[kind] += 1
                if "boundary" in fields:
                    self._boundary_counts[f"{kind}:{fields['boundary']}"] += 1
                self._events.append(event)
        except Exception:
            pass

    def _check(self, boundary: str) -> None:
        context = getattr(self._local, "context", None)
        if context is None:
            return
        session = context["session"]
        try:
            stopped = bool(session.should_stop())
            # An already observed cancellation wins over a failing secondary
            # clock lookup. Do not turn a known stop into a diagnostic failure.
            remaining = None if stopped else session.solver.soft_time_remaining_seconds()
            if remaining is not None:
                if type(remaining) not in (int, float) or not math.isfinite(remaining):
                    raise ValueError("soft_time_remaining_seconds must return finite seconds or None")
                remaining = float(remaining)
            reason = "session_stop" if stopped else "soft_deadline" if remaining is not None and remaining <= 0 else None
        except Exception as exc:
            self._record("check_failed", boundary=boundary, exception_type=type(exc).__name__)
            raise RequestDeadlineCheckFailed(f"Request stop check failed at {boundary}") from exc
        if reason is None:
            self._record("check_passed", boundary=boundary)
            return
        # _play_inner's existing finally will finish the game. Mark this game
        # cancelled before unwinding; do not set the shared stop_event because
        # a per-game action/token/runtime limit must not cancel other games.
        run = getattr(session.game, "game_run", None)
        if run is not None and run.state == "playing":
            run.state = "cancelled"
        self._record("request_blocked", boundary=boundary, reason=reason,
                     game_id=context["game_id"], soft_remaining_seconds=remaining)
        raise RequestDeadlineReached(self, reason)

    def install(self) -> None:
        if self._installed:
            return
        patch = self

        @wraps(self._original_play)
        def play(session: Any, *args: Any, **kwargs: Any) -> Any:
            previous = getattr(patch._local, "context", None)
            run = getattr(session.game, "game_run", None)
            context = {"session": session, "game_id": str(getattr(run, "game_id", "unknown"))[:200]}
            patch._local.context = context
            with patch._lock:
                patch._active += 1
            patch._record("session_begin", game_id=context["game_id"])
            try:
                return patch._original_play(session, *args, **kwargs)
            except RequestDeadlineReached as exc:
                if exc.owner is not patch:
                    raise
                # A rolling-summary chat can run before analyze's try/finally.
                # Mirror only its ephemeral callback cleanup on our stop path;
                # do not rewrite token/history accounting or replay tools.
                agent = session.analyzer
                solver_obj = getattr(getattr(agent, "_step_env_callback", None), "__self__", None)
                if solver_obj is not None and hasattr(solver_obj, "action_guard_hook"):
                    solver_obj.action_guard_hook = None
                agent._step_env_callback = None
                agent._current_valid_actions = []
                patch._record("session_cancelled", game_id=context["game_id"], reason=exc.reason)
                return None
            finally:
                patch._local.context = previous
                with patch._lock:
                    patch._active -= 1
                patch._record("session_end", game_id=context["game_id"])

        @wraps(self._original_handover)
        def handover(agent: Any, *args: Any, **kwargs: Any) -> Any:
            value = patch._original_handover(agent, *args, **kwargs)
            patch._check("after_handover")
            return value

        @wraps(self._original_chat)
        def chat(agent: Any, *args: Any, **kwargs: Any) -> Any:
            patch._check("chat_entry")
            previous = getattr(patch._local, "chat_active", False)
            patch._local.chat_active = True
            try:
                return patch._original_chat(agent, *args, **kwargs)
            finally:
                patch._local.chat_active = previous

        @wraps(self._original_post)
        def post(*args: Any, **kwargs: Any) -> Any:
            if getattr(patch._local, "chat_active", False):
                patch._check("http_entry")
            return patch._original_post(*args, **kwargs)

        self._play = play
        self._handover = handover
        self._chat = chat
        self._requests_proxy = _RequestsProxy(self._original_requests, post)
        self.session_class.play = play
        self.tool_agent_class._maybe_handover = handover
        self.tool_agent_class._chat_completion = chat
        self._module.requests = self._requests_proxy
        self.tool_agent_class._research_request_deadline_patch = self
        self._installed = True

    def uninstall(self) -> None:
        """Uninstall in reverse hook-install order, only after worker drain."""
        if not self._installed:
            return
        with self._lock:
            if self._active:
                raise RuntimeError("Cannot uninstall request deadline while sessions are active")
        if (self.session_class.play is not self._play or
                self.tool_agent_class._maybe_handover is not self._handover or
                self.tool_agent_class._chat_completion is not self._chat or
                self._module.requests is not self._requests_proxy):
            raise RuntimeError("Uninstall later hooks before request deadline; refusing to overwrite them")
        self.session_class.play = self._original_play
        self.tool_agent_class._maybe_handover = self._original_handover
        self.tool_agent_class._chat_completion = self._original_chat
        self._module.requests = self._original_requests
        if getattr(self.tool_agent_class, "_research_request_deadline_patch", None) is self:
            delattr(self.tool_agent_class, "_research_request_deadline_patch")
        self._installed = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counts, events, active = dict(self._counts), list(self._events), self._active
            boundary_counts = dict(self._boundary_counts)
        return {"patch": "request-deadline-v1", "installed": self._installed,
                "active_sessions": active, "provisional": bool(active),
                "max_events": self.max_events, "events": events, "counts": counts,
                "boundary_counts": boundary_counts,
                "events_dropped": max(0, sum(counts.values())-len(events)),
                "clock_origin_utc": self._origin_utc, "source": self._source,
                "semantics": {"scope": "Original Session.play thread; other calls pass through.",
                    "boundaries": "After original handover return, chat entry, and each original transport entry including retries.",
                    "unchanged_before_stop": "Original payload, timeout, retry count/backoff, result identity, exceptions and priority gate operations.",
                    "cancellation": "Private BaseException escapes retry/analyze catches, original finally blocks clean up; outer play consumes only this patch's stop sentinel.",
                    "limitations": "Does not abort in-flight work or guarantee server entry before deadline. A race remains between final client check and actual network send."}}


def install_request_deadline(tool_agent_class: type | None = None,
                             session_class: type | None = None, *,
                             max_events: int = 256) -> RequestDeadlinePatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if session_class is None:
        session_class = importlib.import_module("inference.framework.solver")._HarnessGameSession
    existing = getattr(tool_agent_class, "_research_request_deadline_patch", None)
    if existing is not None:
        if existing.session_class is not session_class or existing.max_events != max_events:
            raise ValueError("Request deadline already installed with different settings")
        return existing
    patch = RequestDeadlinePatch(tool_agent_class, session_class, max_events=max_events)
    patch.install()
    return patch
