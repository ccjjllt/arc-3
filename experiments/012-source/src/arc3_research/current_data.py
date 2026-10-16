"""Opt-in, observation-bound JSON handoff through the existing sandbox IPC.

Only an acknowledged host write is a confirmed commit. It survives subsequent
snippet errors/timeouts, but every actually executed action makes old values
stale. A binding describes the observation at *write time*; it is not evidence
that the value came from that observation or that the value is correct.
"""
from __future__ import annotations

from collections import Counter, OrderedDict, deque
from functools import wraps
import hashlib
import importlib
import inspect
import json
import threading
import time
from typing import Any
import uuid


QUERY = "current_data"
_SESSION_ATTR = "_research_current_data_context"
_LATEST_FLAG = "_research_current_data_latest_enabled"
_BOOTSTRAP_ANCHOR = '    runtime_globals["action"] = action\n'
_LATEST_ANCHORS = (
    '    if initial.get("animation_enabled"):\n',
    '    if initial.get("animation_enabled") and initial.get("state", {}).get("_research_latest_animation_enabled", True):\n',
)
API_NOTE = (
    "\n\nIn python, current_data.put(key, value) stores a JSON value for the current "
    "observation; current_data.get(key) returns {status, value, written_at} only "
    "when status=='current'. Other statuses contain no saved value. Values "
    "survive snippets, but any executed action (including no-op or RESET) makes "
    "them stale. For example: entry=current_data.get('measurement'); "
    "value=entry['value'] if entry['status']=='current' else None. "
    "Optionally obtain at=current_data.context()['context'] before computing, "
    "then put(key, value, at=at); a changed observation rejects this write. "
    "A stored response confirms a host commit, including if the snippet later "
    "fails or times out; missing acknowledgment means the write outcome is "
    "unknown. written_at identifies the observation at commit, not the value's "
    "source or correctness. Previously read local aliases do not auto-invalidate. "
    "JSON only: null/bool/int/finite float/string/list/dict with string keys; "
    "no objects, tuples, cycles or depth over 16. Default limits are 16 KiB/value, "
    "64 KiB/session and 32 keys; keys are nonempty strings of at most 128 UTF-8 "
    "bytes. Rejected writes preserve existing valid values. No value is printed "
    "automatically."
)


def _encode_json(value, byte_limit, max_depth):
    """Strict, incremental canonical JSON; shared by host and isolated child.

    Scalars are bounded before encoding and container output is accumulated only
    up to byte_limit. Exact built-in types avoid implicit tuple/key coercion and
    invoking arbitrary user-object serialization methods.
    """
    parts = []
    size = 0
    active = set()

    def add(data):
        nonlocal size
        size += len(data)
        if size > byte_limit:
            raise ValueError("value_too_large")
        parts.append(data)

    def scalar(item):
        if type(item) is str and len(item) > byte_limit:
            raise ValueError("value_too_large")
        if type(item) is int and item.bit_length() > byte_limit * 4:
            raise ValueError("value_too_large")
        try:
            return json.dumps(item, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":")).encode("utf-8")
        except (ValueError, UnicodeError):
            raise ValueError("invalid_scalar") from None

    def walk(item, depth):
        if depth > max_depth:
            raise ValueError("value_too_deep")
        kind = type(item)
        if item is None or kind in (str, bool, int, float):
            add(scalar(item))
            return
        if kind not in (dict, list):
            raise ValueError("unsupported_type")
        if id(item) in active:
            raise ValueError("cyclic_value")
        if len(item) > byte_limit:
            raise ValueError("value_too_large")
        active.add(id(item))
        if kind is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("non_string_key")
            add(b"{")
            for index, key in enumerate(sorted(item)):
                if index:
                    add(b",")
                add(scalar(key))
                add(b":")
                walk(item[key], depth + 1)
            add(b"}")
        else:
            add(b"[")
            for index, child in enumerate(item):
                if index:
                    add(b",")
                walk(child, depth + 1)
            add(b"]")
        active.remove(id(item))

    walk(value, 0)
    return b"".join(parts)


_BOOTSTRAP_API = '''
    def _current_data_request(request):
        _send({"type": "animation", "request": {"kind": "current_data", **request}})
        try:
            reply = _recv()
        except Exception as exc:
            raise RuntimeError("Current-data acknowledgment unavailable; write outcome may be unknown.") from exc
        if reply.get("type") == "animation_error":
            raise RuntimeError(str(reply.get("error", "Current-data host failed; write outcome may be unknown.")))
        if reply.get("type") != "animation_result" or not isinstance(reply.get("animation"), dict):
            raise RuntimeError("Invalid current-data acknowledgment; write outcome may be unknown.")
        return reply["animation"]

    class _CurrentData:
        def _reject(self, op, reason):
            return _current_data_request({"op": "rejected", "target_op": op, "reason": reason})

        def _key_valid(self, key):
            if type(key) is not str or not key or len(key) > 128:
                return False
            try:
                return len(key.encode("utf-8")) <= 128
            except UnicodeError:
                return False

        def context(self):
            return _current_data_request({"op": "context"})

        def put(self, key, value, *, at=None):
            if not self._key_valid(key):
                return self._reject("put", "invalid_key")
            limits = initial.get("state", {}).get("_research_current_data_limits", {})
            try:
                blob = _encode_json(value, limits.get("max_value_bytes", 16384), limits.get("max_depth", 16))
                if at is not None:
                    _encode_json(at, 2048, 4)
            except ValueError as exc:
                return self._reject("put", str(exc))
            return _current_data_request({"op": "put", "key": key, "value": json.loads(blob), "at": at})

        def get(self, key):
            if not self._key_valid(key):
                return self._reject("get", "invalid_key")
            return _current_data_request({"op": "get", "key": key})

    runtime_globals["current_data"] = _CurrentData()
'''


class CurrentDataPatch:
    """Bounded host-owned stores. Locks never span original actions or IPC.

    Byte limits count canonical value JSON, not Python RSS. At most max_keys
    bounded-key records (including stale metadata) are retained per session;
    session eviction frees all values and never reactivates the same identity.
    An in-flight action temporarily makes queries unavailable, so put cannot
    commit midway through a wrapped action even if another thread calls it.
    """

    def __init__(self, tool_agent_class: type, session_class: type, **limits: int) -> None:
        if any(type(value) is not int or value < 1 for value in limits.values()):
            raise ValueError("Current-data limits must be positive integers.")
        if limits["max_depth"] > 64:
            raise ValueError("max_depth cannot exceed 64.")
        self.limits = limits
        self.tool_agent_class = tool_agent_class
        self.session_class = session_class
        self._agent_module = importlib.import_module(tool_agent_class.__module__)
        self._solver_module = importlib.import_module(session_class.__module__)
        self._original_execute = session_class._execute_action
        self._original_step = session_class.step_env
        self._original_tool = tool_agent_class._run_python_tool
        self._original_ensure = tool_agent_class._ensure_session
        self._original_sandbox = self._agent_module.run_sandboxed_python
        self._sandbox_module = importlib.import_module(self._original_sandbox.__module__)
        self._lock = threading.RLock()
        self._local = threading.local()
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._counts: Counter[str] = Counter()
        self._events: deque[dict[str, Any]] = deque(maxlen=128)
        self._bytes = 0
        self._peak_bytes = 0
        self._query_cpu = 0.0
        self._action_cpu = 0.0
        self._source_hashes = {
            name: hashlib.sha256(inspect.getsource(function).encode()).hexdigest()
            for name, function in {
                "session._execute_action": self._original_execute,
                "session.step_env": self._original_step,
                "agent._run_python_tool": self._original_tool,
                "agent._ensure_session": self._original_ensure,
                "run_sandboxed_python": self._original_sandbox,
            }.items()
        }

    def _identity(self, session: Any) -> dict[str, Any]:
        grid = self._solver_module._grid_from_state(session.game.current_state)
        frame = json.dumps(grid, separators=(",", ":")).encode()
        return {"action_num": int(session.action_count),
                "level": int(self._solver_module._level_number(session.game)),
                "frame_sha256": hashlib.sha256(frame).hexdigest()}

    def _context(self, session: Any) -> dict[str, Any]:
        context = getattr(session, _SESSION_ATTR, None)
        if context is not None:
            return context
        run = getattr(session.game, "game_run", None)
        context = {"game_id": str(getattr(run, "game_id", getattr(session, "game_index", "")))[:256],
                   "session_id": uuid.uuid4().hex, "attempt": 0, "revision": 0,
                   "identity": self._identity(session), "inflight": 0}
        setattr(session, _SESSION_ATTR, context)
        while len(self._sessions) >= self.limits["max_sessions"]:
            _, old = self._sessions.popitem(last=False)
            self._bytes -= old["bytes"]
            self._counts["evicted_sessions"] += 1
            self._counts["evicted_bytes"] += old["bytes"]
        self._sessions[context["session_id"]] = {
            "context": context, "records": OrderedDict(), "bytes": 0, "counts": Counter()}
        self._counts["sessions_seen"] += 1
        return context

    @staticmethod
    def _binding(context: dict[str, Any]) -> dict[str, Any]:
        return {name: context[name] for name in ("game_id", "session_id", "attempt", "revision")} | context["identity"]

    def _invalidate(self, context: dict[str, Any], reason: str) -> None:
        store = self._sessions.get(context["session_id"])
        if store is None:
            return
        entries = 0
        for entry in store["records"].values():
            if entry.pop("blob", None) is not None:
                entry["status"] = "stale"
                entry["reason"] = reason
                entries += 1
        self._counts["invalidated_entries"] += entries
        self._counts["invalidated_bytes"] += store["bytes"]
        store["counts"]["invalidated_entries"] += entries
        self._bytes -= store["bytes"]
        store["bytes"] = 0

    def _sync(self, session: Any, context: dict[str, Any]) -> None:
        identity = self._identity(session)
        if identity != context["identity"]:
            self._invalidate(context, "host_observation_changed")
            context["identity"] = identity
            context["revision"] += 1
            self._counts["observation_resyncs"] += 1

    def _begin_action(self, session: Any) -> dict[str, Any]:
        with self._lock:
            context = self._context(session)
            self._sync(session, context)
            context["inflight"] += 1
            return context

    @staticmethod
    def _cpu_now() -> float | None:
        try:
            return time.thread_time()
        except Exception:
            return None

    @classmethod
    def _cpu_elapsed(cls, started: float | None) -> float:
        ended = cls._cpu_now()
        return max(0.0, ended - started) if started is not None and ended is not None else 0.0

    def _action_error(self, context: dict[str, Any] | None) -> None:
        # Cache maintenance must not replace an action return/exception. If its
        # own cleanup failed, discard payloads and make every old token stale.
        try:
            with self._lock:
                self._counts["action_observer_errors"] += 1
                if context is not None:
                    self._invalidate(context, "action_observer_error")
                    context["revision"] += 1
                    context["inflight"] = max(0, context["inflight"] - 1)
        except Exception:
            pass

    def _end_action(self, session: Any, context: dict[str, Any], action: Any, result: Any) -> None:
        with self._lock:
            try:
                identity = self._identity(session)
                executed = isinstance(result, dict) and result.get("executed") is True
                # A post-execution viewer/write failure can skip the normal return.
                # Actual history/observation changes still invalidate in finally.
                changed = identity != context["identity"]
                if executed or changed:
                    self._invalidate(context, "action_executed")
                    context["revision"] += 1
                    if getattr(getattr(action, "id", None), "name", None) == "RESET":
                        context["attempt"] += 1
                    context["identity"] = identity
                    self._counts["executed_action_boundaries"] += 1
            except Exception:
                self._invalidate(context, "unavailable_observation")
                self._counts["action_observer_errors"] += 1
            finally:
                context["inflight"] = max(0, context["inflight"] - 1)

    @staticmethod
    def _valid_key(key: Any) -> bool:
        if type(key) is not str or not key or len(key) > 128:
            return False
        try:
            return len(key.encode("utf-8")) <= 128
        except UnicodeError:
            return False

    def _query(self, session: Any, request: dict[str, Any]) -> dict[str, Any]:
        started = time.thread_time()
        op = request.get("op")
        effective_op = request.get("target_op") if op == "rejected" else op
        if effective_op not in ("put", "get", "context"):
            effective_op = "invalid"
        with self._lock:
            context = self._context(session)
            store = self._sessions.get(context["session_id"])
            self._counts["queries"] += 1
            self._counts[effective_op + "_requests"] += 1
            if store is not None:
                store["counts"][effective_op + "_requests"] += 1
            try:
                if store is None:
                    response = {"status": "session_evicted"}
                elif context["inflight"]:
                    response = {"status": "action_in_progress"}
                else:
                    self._sync(session, context)
                    response = self._operate(context, store, request)
            except Exception as exc:
                self._invalidate(context, "query_error")
                self._counts["query_errors"] += 1
                response = {"status": "unavailable_observation", "error_type": type(exc).__name__}
            self._counts["status_" + response["status"]] += 1
            self._counts[effective_op + "_" + response["status"]] += 1
            if store is not None:
                store["counts"]["queries"] += 1
                store["counts"]["status_" + response["status"]] += 1
                store["counts"][effective_op + "_" + response["status"]] += 1
            self._events.append({"op": op if op in ("context", "put", "get", "rejected") else "invalid",
                                 "requested_op": effective_op,
                                 "session_id": context["session_id"], "action_num": context["identity"]["action_num"],
                                 "status": response["status"]})
            self._counts["response_json_bytes"] += len(json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode())
            self._query_cpu += time.thread_time() - started
            return response

    def _operate(self, context: dict[str, Any], store: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        op = request.get("op")
        binding = self._binding(context)
        if op == "context":
            return {"status": "current", "context": binding}
        if op == "rejected":
            # Child rejects before IPC: only a bounded reason, never the value.
            reason = request.get("reason")
            allowed = {"invalid_key", "value_too_large", "value_too_deep", "invalid_scalar",
                       "unsupported_type", "cyclic_value", "non_string_key"}
            return {"status": "rejected", "reason": reason if reason in allowed else "invalid_value"}
        if op not in ("put", "get"):
            return {"status": "invalid_operation"}
        key = request.get("key")
        if not self._valid_key(key):
            return {"status": "rejected", "reason": "invalid_key"}
        entry = store["records"].get(key)
        if op == "get":
            if entry is None:
                return {"status": "missing", "key": key}
            if entry["status"] != "current" or entry["written_at"] != binding:
                return {"status": "stale", "key": key, "written_at": dict(entry["written_at"])}
            blob = entry["blob"]
            self._counts["read_value_bytes"] += len(blob)
            return {"status": "current", "key": key, "value": json.loads(blob),
                    "written_at": dict(entry["written_at"]), "value_sha256": entry["value_sha256"]}
        if "value" not in request:
            return {"status": "rejected", "reason": "missing_value"}
        try:
            blob = _encode_json(request["value"], self.limits["max_value_bytes"], self.limits["max_depth"])
            at = request.get("at")
            if at is not None:
                _encode_json(at, 2048, 4)
                # Avoid equality coercions such as True == 1 in a forged token.
                if _encode_json(at, 2048, 4) != _encode_json(binding, 2048, 4):
                    return {"status": "stale_context"}
        except ValueError as exc:
            return {"status": "rejected", "reason": str(exc)}
        if entry is None and len(store["records"]) >= self.limits["max_keys"]:
            return {"status": "rejected", "reason": "key_capacity"}
        previous_bytes = len(entry.get("blob", b"")) if entry is not None else 0
        new_bytes = store["bytes"] - previous_bytes + len(blob)
        if new_bytes > self.limits["max_session_bytes"]:
            return {"status": "rejected", "reason": "session_byte_capacity"}
        digest = hashlib.sha256(blob).hexdigest()
        # No mutations precede full validation/capacity checks. This replacement
        # is the commit; the normal animation IPC acknowledges after we return.
        store["records"][key] = {"status": "current", "blob": blob,
                                  "written_at": binding, "value_sha256": digest}
        store["bytes"] = new_bytes
        self._bytes += len(blob) - previous_bytes
        self._peak_bytes = max(self._peak_bytes, self._bytes)
        self._counts["committed_puts"] += 1
        self._counts["written_value_bytes"] += len(blob)
        return {"status": "stored", "key": key, "written_at": dict(binding),
                "bytes": len(blob), "value_sha256": digest}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": True, "limits": dict(self.limits), "max_key_utf8_bytes": 128,
                "counts": dict(self._counts), "stored_value_bytes": self._bytes,
                "peak_stored_value_bytes": self._peak_bytes,
                "query_cpu_seconds": self._query_cpu, "action_boundary_cpu_seconds": self._action_cpu,
                "sessions": [{"binding": self._binding(store["context"]),
                              "keys": len(store["records"]), "stored_value_bytes": store["bytes"],
                              "current_keys": sum(entry["status"] == "current" for entry in store["records"].values()),
                              "counts": dict(store["counts"])} for store in self._sessions.values()],
                "recent_queries": list(self._events), "baseline_source_sha256": dict(self._source_hashes),
                "api_note": API_NOTE.strip(),
                "semantics": {
                    "binding": "Host observation at commit; does not prove value source or correctness.",
                    "invalidation": "Any executed action including no-op/RESET; get/put recheck live host identity.",
                    "commit": "Synchronous host replacement before IPC ack; no snippet-end commit or rollback. Unacknowledged write is unknown.",
                    "aliases": "Each get is a JSON copy; previously returned local aliases cannot auto-invalidate.",
                    "bytes": "Canonical UTF-8 JSON value bytes, not RSS; keys/stale metadata separately bounded.",
                    "hash": "SHA256 canonical sorted-key compact UTF-8 JSON. Frame hash uses compact settled grid JSON.",
                    "cpu": "Host thread CPU for query/action-boundary bookkeeping, excluding original actions and child validation.",
                    "eviction": "FIFO sessions; no resurrection. Up to max_keys current or stale records; new keys reject when full.",
                },
            }

    def install(self) -> None:
        patch = self
        bootstrap = self._sandbox_module._SANDBOX_BOOTSTRAP
        if bootstrap.count(_BOOTSTRAP_ANCHOR) != 1:
            raise RuntimeError("Unsupported sandbox: expected exactly one action anchor.")
        anchors = [anchor for anchor in _LATEST_ANCHORS if bootstrap.count(anchor) == 1]
        if len(anchors) != 1:
            raise RuntimeError("Unsupported sandbox: expected one known latest-animation guard.")
        modified = inspect.getsource(_encode_json) + "\n" + bootstrap
        modified = modified.replace(_BOOTSTRAP_ANCHOR, _BOOTSTRAP_ANCHOR + _BOOTSTRAP_API)
        guard = anchors[0].rstrip()[:-1] + ' and initial.get("state", {}).get("' + _LATEST_FLAG + '", True):\n'
        modified = modified.replace(anchors[0], guard)
        compile(modified, "<current_data_sandbox>", "exec")
        self._source_hashes["sandbox_bootstrap_before"] = hashlib.sha256(bootstrap.encode()).hexdigest()
        self._source_hashes["sandbox_bootstrap_after"] = hashlib.sha256(modified.encode()).hexdigest()

        @wraps(self._original_execute)
        def execute(session: Any, action: Any, **kwargs: Any) -> Any:
            started = patch._cpu_now()
            context = None
            try:
                context = patch._begin_action(session)
            except Exception:
                patch._action_error(getattr(session, _SESSION_ATTR, None))
            before_cpu = patch._cpu_elapsed(started)
            result = None
            try:
                result = patch._original_execute(session, action, **kwargs)
                return result
            finally:
                started = patch._cpu_now()
                try:
                    if context is not None:
                        patch._end_action(session, context, action, result)
                except Exception:
                    patch._action_error(context)
                try:
                    with patch._lock:
                        patch._action_cpu += before_cpu + patch._cpu_elapsed(started)
                except Exception:
                    pass

        @wraps(self._original_step)
        def step_env(session: Any, arguments: dict[str, Any]) -> Any:
            if arguments.get("query") == QUERY:
                return {"executed": False, "query": QUERY, "result": patch._query(session, arguments)}
            return patch._original_step(session, arguments)

        @wraps(self._original_ensure)
        def ensure(agent: Any, state_path: Any) -> Any:
            result = patch._original_ensure(agent, state_path)
            if API_NOTE not in agent._system_prompt:
                agent._system_prompt += API_NOTE
            return result

        @wraps(self._original_tool)
        def run_tool(agent: Any, state_path: Any, arguments: dict[str, Any]) -> Any:
            previous = getattr(patch._local, "agent", None)
            patch._local.agent = agent
            try:
                return patch._original_tool(agent, state_path, arguments)
            finally:
                patch._local.agent = previous

        @wraps(self._original_sandbox)
        def sandbox(**kwargs: Any) -> Any:
            agent = getattr(patch._local, "agent", None)
            callback = getattr(agent, "_step_env_callback", None)
            original_handler = kwargs.get("animation_handler")

            def animation_handler(request: dict[str, Any]) -> Any:
                if request.get("kind") != QUERY:
                    return original_handler(request) if original_handler is not None else {}
                if callback is None:
                    return {"status": "unavailable_session"}
                forwarded = {key: request[key] for key in ("op", "key", "value", "at", "target_op", "reason") if key in request}
                result = callback({**forwarded, "query": QUERY})
                if not isinstance(result, dict) or not isinstance(result.get("result"), dict):
                    return {"status": "invalid_host_response"}
                return result["result"]

            kwargs["animation_handler"] = animation_handler
            kwargs["initial_state"] = {**kwargs["initial_state"], _LATEST_FLAG: original_handler is not None,
                                       "_research_current_data_limits": dict(patch.limits)}
            return patch._original_sandbox(**kwargs)

        self._sandbox_module._SANDBOX_BOOTSTRAP = modified
        self.session_class._execute_action = execute
        self.session_class.step_env = step_env
        self.tool_agent_class._ensure_session = ensure
        self.tool_agent_class._run_python_tool = run_tool
        self._agent_module.run_sandboxed_python = sandbox


def install_current_data(
    tool_agent_class: type | None = None, session_class: type | None = None, *,
    max_value_bytes: int = 16 * 1024, max_session_bytes: int = 64 * 1024,
    max_keys: int = 32, max_sessions: int = 128, max_depth: int = 16,
) -> CurrentDataPatch:
    """Install in the candidate process only, before solving; disabled omits it."""
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if session_class is None:
        session_class = importlib.import_module("inference.framework.solver")._HarnessGameSession
    limits = dict(max_value_bytes=max_value_bytes, max_session_bytes=max_session_bytes,
                  max_keys=max_keys, max_sessions=max_sessions, max_depth=max_depth)
    existing = getattr(tool_agent_class, "_research_current_data_patch", None)
    if existing is not None:
        if existing.session_class is not session_class or existing.limits != limits:
            raise ValueError("Current data is already installed with different settings.")
        return existing
    patch = CurrentDataPatch(tool_agent_class, session_class, **limits)
    patch.install()
    tool_agent_class._research_current_data_patch = patch
    return patch
