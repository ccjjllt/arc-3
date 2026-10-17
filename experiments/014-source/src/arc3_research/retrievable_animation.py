"""Opt-in, bounded retrieval of earlier actions' public SDK return frames.

Install only in the candidate process, before solving games. Capture wraps the
actual per-action executor, not the batch result. No SDK action is issued here;
the archive copies ``current_state.raw.frame`` immediately after execution.
The baseline's latest-animation record, guards and action payloads are untouched.
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


QUERY = "retrievable_animation"
API_NOTE = (
    "\n\nHistorical SDK frames are available read-only in python: "
    "animation_refs(limit=16) returns {status, records}; each record has an exact "
    "ref with game_id/session_id/attempt/action_num. animation_at(ref) returns "
    "{status, frames, before_frame, metadata}; use frames only when status=='hit'. "
    "For a nonempty refs=animation_refs()['records'], a=animation_at(refs[0]['ref']) "
    "fetches that chosen action. "
    "On a hit, a['frames'][i].ascii is raw SDK frame i (zero-based, duplicates "
    "retained); a['before_frame'] is separate. FrameView supports the usual "
    "ascii/shape/segmentation access, plus content_sha256. Print selected frames or cells, not the "
    "whole archive. The ref's attempt starts at 0 and increases on each executed "
    "RESET; metadata reports level_before/level_after. Old frames are historical "
    "observations, not current_frame. Storage is bounded: missing, evicted and "
    "wrong-scope refs return explicit statuses, never the latest frames. "
    "last_animation_frames and last_animation_timeline keep their existing meaning."
)

# Injected before _available_names is built, so retained user functions may
# reference these helpers without changing function-persistence policy.
_BOOTSTRAP_ANCHOR = '    runtime_globals["action"] = action\n'
_LATEST_ANCHOR = '    if initial.get("animation_enabled"):\n'
_LATEST_GUARD = ('    if initial.get("animation_enabled") and '
                 'initial.get("state", {}).get("_research_latest_animation_enabled", True):\n')
_BOOTSTRAP_API = '''
    def _historical_animation_request(request):
        _send({"type": "animation", "request": {"kind": "retrievable_animation", **request}})
        reply = _recv()
        if reply.get("type") == "animation_error":
            raise RuntimeError(str(reply.get("error", "animation failed")))
        if reply.get("type") != "animation_result":
            raise RuntimeError("Invalid historical-animation response from sandbox host.")
        payload = reply.get("animation")
        if not isinstance(payload, dict):
            raise RuntimeError("Historical-animation response must be a dictionary.")
        return payload

    def animation_refs(limit=16):
        """List recent exact action references, including unavailable records."""
        return _historical_animation_request({"op": "list", "limit": limit})

    def animation_at(ref):
        """Read an exact action's SDK frames; never substitute another action."""
        payload = _historical_animation_request({"op": "get", "ref": ref})
        if payload.get("status") == "hit":
            def frame_view(item):
                frame = FrameView(ascii=item["ascii"], step=item["step"],
                                  level=item["level"], shape=item["shape"], grid=item["grid"])
                frame.raw_frame_index = item.get("raw_frame_index")
                frame.content_sha256 = item["content_sha256"]
                return frame
            payload["frames"] = [frame_view(item) for item in payload["frames"]]
            payload["before_frame"] = frame_view(payload["before_frame"])
        return payload

    runtime_globals["animation_refs"] = animation_refs
    runtime_globals["animation_at"] = animation_at
'''


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _source_hash(function: Any) -> str:
    return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()


class RetrievableAnimationPatch:
    """A process-wide archive; all counters and byte limits share one lock.

    Byte limits count the exact UTF-8 JSON blobs containing before + raw frames,
    not Python RSS. Metadata is independently bounded by sessions and records.
    Old session identities are never reactivated after session eviction.
    """

    def __init__(self, tool_agent_class: type, session_class: type,
                 *, max_records_per_session: int, max_bytes_per_session: int,
                 max_total_bytes: int, max_sessions: int) -> None:
        self.tool_agent_class = tool_agent_class
        self.session_class = session_class
        self.limits = {
            "max_records_per_session": max_records_per_session,
            "max_bytes_per_session": max_bytes_per_session,
            "max_total_bytes": max_total_bytes,
            "max_sessions": max_sessions,
        }
        if any(type(value) is not int or value < 1 for value in self.limits.values()):
            raise ValueError("Archive limits must be positive integers.")
        self._agent_module = importlib.import_module(tool_agent_class.__module__)
        self._solver_module = importlib.import_module(session_class.__module__)
        self._original_execute = session_class._execute_action
        self._original_step = session_class.step_env
        self._original_tool = tool_agent_class._run_python_tool
        self._original_ensure = tool_agent_class._ensure_session
        self._original_sandbox = self._agent_module.run_sandboxed_python
        self._sandbox_module = importlib.import_module(self._original_sandbox.__module__)
        self._format_grid = importlib.import_module("inference.utils.grid_utils").format_grid_ascii
        self._lock = threading.RLock()
        self._local = threading.local()
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._blobs: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()
        self._counts: Counter[str] = Counter()
        self._events: deque[dict[str, Any]] = deque(maxlen=128)
        self._bytes = 0
        self._peak_bytes = 0
        self._capture_cpu = 0.0
        self._query_cpu = 0.0
        self._source_hashes = {
            name: _source_hash(function) for name, function in {
                "session._execute_action": self._original_execute,
                "session.step_env": self._original_step,
                "agent._run_python_tool": self._original_tool,
                "agent._ensure_session": self._original_ensure,
                "run_sandboxed_python": self._original_sandbox,
            }.items()
        }

    def _context(self, session: Any) -> dict[str, Any]:
        with self._lock:
            context = getattr(session, "_research_retrievable_animation_context", None)
            if context is not None:
                return context
            run = getattr(session.game, "game_run", None)
            context = {
                "game_id": str(getattr(run, "game_id", getattr(session, "game_index", ""))),
                "session_id": uuid.uuid4().hex,
                "attempt": 0,
                "sequence": 0,
            }
            session._research_retrievable_animation_context = context
            while len(self._sessions) >= self.limits["max_sessions"]:
                old_id = next(iter(self._sessions))
                old_store = self._sessions[old_id]
                for key in list(old_store["records"]):
                    self._drop_blob((old_id, *key), "session_evicted")
                self._sessions.pop(old_id)
                self._counts["evicted_sessions"] += 1
            self._sessions[context["session_id"]] = {
                "context": context,
                "records": OrderedDict(),
                "bytes": 0,
                "counts": Counter(),
                "metadata_evicted": 0,
            }
            self._counts["sessions_seen"] += 1
            return context

    def _drop_blob(self, key: tuple[str, int, int], reason: str) -> None:
        blob = self._blobs.pop(key, None)
        if blob is None:
            return
        self._bytes -= len(blob)
        store = self._sessions.get(key[0])
        if store is not None:
            store["bytes"] -= len(blob)
            metadata = store["records"].get(key[1:])
            if metadata is not None:
                metadata["status"] = "evicted"
                metadata["eviction_reason"] = reason
        self._counts["evicted_records"] += 1
        self._counts["evicted_bytes"] += len(blob)

    @staticmethod
    def _encode_frames(before: Any, raw_frames: Any, limit: int) -> tuple[bytes | None, int, str]:
        """Copy all returned frames, or reject the record without truncation.

        Encode incrementally so extra archive construction is byte-bounded even
        for an unexpectedly large SDK return. Grids themselves are SDK-sized;
        an explicit shape bound also rejects malformed/unbounded containers.
        """
        chunks = []
        size = 0

        def add(value: bytes) -> None:
            nonlocal size
            size += len(value)
            if size > limit:
                raise OverflowError
            chunks.append(value)

        def grid(value: Any) -> bytes:
            rows = value.tolist() if hasattr(value, "tolist") else value
            if len(rows) > 512 or any(len(row) > 512 for row in rows):
                raise ValueError("Unsupported frame shape")
            copied = []
            for row in rows:
                line = []
                for cell in row:
                    scalar = cell.item() if hasattr(cell, "item") else cell
                    if type(scalar) is not int or not 0 <= scalar <= 15:
                        raise ValueError("Invalid ARC frame cell")
                    line.append(scalar)
                copied.append(line)
            if copied and any(len(row) != len(copied[0]) for row in copied):
                raise ValueError("Ragged frame")
            return json.dumps(copied, separators=(",", ":")).encode()

        count = 0
        try:
            add(b'{"before":')
            add(grid(before))
            add(b',"frames":[')
            for frame in (() if raw_frames is None else raw_frames):
                if count:
                    add(b",")
                add(grid(frame))
                count += 1
            add(b"]}")
        except OverflowError:
            return None, count, "too_large"
        except (TypeError, ValueError, AttributeError):
            return None, count, "invalid_frames"
        if not count:
            return None, 0, "missing_frames"
        return b"".join(chunks), count, "available"

    def _capture(self, session: Any, context: dict[str, Any], payload: dict[str, Any],
                 before_grid: Any, before_level: int, before_step: int) -> None:
        action_num = payload.get("action_num")
        if payload.get("executed") is not True or type(action_num) is not int:
            with self._lock:
                self._counts["nonexecuted_returns_skipped"] += 1
            return
        is_reset = str(payload.get("action_name")) == "RESET"
        with self._lock:
            self._counts["capture_calls"] += 1
            context["sequence"] += 1
            if is_reset:
                context["attempt"] += 1
            ref = {name: context[name] for name in ("game_id", "session_id", "attempt")}
            ref["action_num"] = action_num
            store = self._sessions.get(context["session_id"])
            if store is None:
                self._counts["capture_session_evicted"] += 1
                return
            store["counts"]["capture_calls"] += 1
        raw = getattr(session.game.current_state, "raw", None)
        blob, frame_count, status = self._encode_frames(
            before_grid, getattr(raw, "frame", None),
            min(self.limits["max_bytes_per_session"], self.limits["max_total_bytes"]),
        )
        metadata = {
            "ref": ref,
            "sequence": context["sequence"],
            "status": status,
            "action": str(payload.get("action_display") or payload.get("action_name") or "")[:160],
            "automatic": bool(payload.get("automatic")),
            "level_before": before_level,
            "level_after": payload.get("level"),
            "before_step": before_step,
            "raw_frame_count": frame_count if status == "available" else None,
            "complete": status == "available",
            "frame_level_semantics": "returned_level",
            "stored_bytes": len(blob) if blob is not None else 0,
            "archive_sha256": hashlib.sha256(blob).hexdigest() if blob is not None else None,
        }
        key = (ref["attempt"], action_num)
        blob_key = (ref["session_id"], *key)
        with self._lock:
            # Another game may have evicted this session while encoding.
            store = self._sessions.get(ref["session_id"])
            if store is None:
                self._counts["capture_session_evicted"] += 1
                return
            self._sessions.move_to_end(ref["session_id"])
            if key in store["records"]:
                # An impossible duplicate identity must never overwrite evidence.
                self._counts["duplicate_refs_rejected"] += 1
                return
            while len(store["records"]) >= self.limits["max_records_per_session"]:
                old_key = next(iter(store["records"]))
                self._drop_blob((ref["session_id"], *old_key), "record_limit")
                store["records"].pop(old_key)
                store["metadata_evicted"] += 1
            store["records"][key] = metadata
            self._counts["capture_" + status] += 1
            store["counts"]["capture_" + status] += 1
            if blob is None:
                return
            while store["bytes"] + len(blob) > self.limits["max_bytes_per_session"]:
                old_key = next(k for k in self._blobs if k[0] == ref["session_id"])
                self._drop_blob(old_key, "session_byte_limit")
            while self._bytes + len(blob) > self.limits["max_total_bytes"]:
                self._drop_blob(next(iter(self._blobs)), "global_byte_limit")
            self._blobs[blob_key] = blob
            self._bytes += len(blob)
            store["bytes"] += len(blob)
            self._peak_bytes = max(self._peak_bytes, self._bytes)
            self._counts["captured_bytes"] += len(blob)
            self._counts["captured_raw_frames"] += frame_count

    def _frame(self, grid: Any, *, step: int, level: int, index: int | None) -> dict[str, Any]:
        return {"ascii": self._format_grid(grid), "step": step, "level": level,
                "shape": [len(grid), len(grid[0]) if grid else 0], "grid": grid,
                "raw_frame_index": index,
                "content_sha256": hashlib.sha256(json.dumps(grid, separators=(",", ":")).encode()).hexdigest()}

    def _query(self, session: Any, request: dict[str, Any]) -> dict[str, Any]:
        started = time.thread_time()
        context = self._context(session)
        op = request.get("op")
        with self._lock:
            self._counts["query_calls"] += 1
            counter = "list_queries" if op == "list" else "get_queries" if op == "get" else "invalid_queries"
            self._counts[counter] += 1
            store = self._sessions.get(context["session_id"])
            if store is not None:
                store["counts"]["query_calls"] += 1
            response = self._query_locked(context, store, request)
            status = response["status"]
            self._counts["query_status_" + status] += 1
            if op == "get":
                hit = status == "hit"
                self._counts["hits" if hit else "misses"] += 1
                if store is not None:
                    store["counts"]["hits" if hit else "misses"] += 1
                metadata = response.get("metadata") or {}
                if metadata and metadata["sequence"] < context["sequence"]:
                    self._counts["nonlatest_queries"] += 1
                    if hit:
                        self._counts["nonlatest_hits"] += 1
                        store["counts"]["nonlatest_hits"] += 1
                    response["nonlatest"] = True
                elif hit:
                    response["nonlatest"] = False
            # JSON size describes data crossing IPC, not prompt token consumption.
            response_bytes = len(json.dumps(response, separators=(",", ":")).encode())
            self._counts["response_json_bytes"] += response_bytes
            self._events.append({"op": str(op)[:24], "status": status,
                                 "session_id": context["session_id"],
                                 "ref": _copy_json(response.get("ref")),
                                 "nonlatest": response.get("nonlatest"),
                                 "response_json_bytes": response_bytes})
            self._query_cpu += time.thread_time() - started
            return response

    def _query_locked(self, context: dict[str, Any], store: dict[str, Any] | None,
                      request: dict[str, Any]) -> dict[str, Any]:
        op = request.get("op")
        if op not in ("list", "get"):
            return {"status": "invalid_operation"}
        if op == "list":
            limit = request.get("limit", 16)
            if type(limit) is not int or not 1 <= limit <= self.limits["max_records_per_session"]:
                return {"status": "invalid_limit", "maximum": self.limits["max_records_per_session"]}
            if store is None:
                return {"status": "session_evicted", "records": []}
            records = list(store["records"].values())[-limit:]
            return {"status": "ok", "records": _copy_json(records),
                    "session_id": context["session_id"], "attempt": context["attempt"],
                    "captured_actions": context["sequence"],
                    "metadata_evicted": store["metadata_evicted"],
                    "listed": len(records), "retained_metadata": len(store["records"])}
        ref = request.get("ref")
        if (not isinstance(ref, dict)
                or set(ref) != {"game_id", "session_id", "attempt", "action_num"}
                or type(ref["game_id"]) is not str or type(ref["session_id"]) is not str
                or type(ref["attempt"]) is not int or ref["attempt"] < 0
                or type(ref["action_num"]) is not int or ref["action_num"] < 0):
            return {"status": "invalid_ref"}
        # Never return records from another session, even if still resident.
        if ref["game_id"] != context["game_id"] or ref["session_id"] != context["session_id"]:
            return {"status": "wrong_scope"}
        if store is None:
            return {"status": "session_evicted", "ref": dict(ref)}
        key = (ref["attempt"], ref["action_num"])
        metadata = store["records"].get(key)
        if metadata is None:
            if store["metadata_evicted"] and store["records"] and key < next(iter(store["records"])):
                return {"status": "outside_retained_history", "ref": dict(ref),
                        "detail": "Older than retained metadata; original existence can no longer be verified."}
            elif any(other[1] == ref["action_num"] for other in store["records"]):
                status = "wrong_attempt"
            else:
                status = "missing"
            return {"status": status, "ref": dict(ref)}
        if metadata["status"] != "available":
            return {"status": metadata["status"], "ref": dict(ref), "metadata": _copy_json(metadata)}
        blob = self._blobs.get((ref["session_id"], *key))
        if blob is None:
            return {"status": "evicted", "ref": dict(ref)}
        decoded = json.loads(blob)
        self._counts["retrieved_blob_bytes"] += len(blob)
        return {
            "status": "hit", "ref": dict(ref), "metadata": _copy_json(metadata),
            "before_frame": self._frame(decoded["before"], step=metadata["before_step"],
                                         level=metadata["level_before"], index=None),
            "frames": [self._frame(grid, step=ref["action_num"], level=metadata["level_after"], index=i)
                       for i, grid in enumerate(decoded["frames"])],
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "intervention": "retrievable-animation-v1", "enabled": True,
                "limits": dict(self.limits), "counts": dict(self._counts),
                "stored_frame_json_bytes": self._bytes, "peak_frame_json_bytes": self._peak_bytes,
                "capture_cpu_seconds": self._capture_cpu, "query_cpu_seconds": self._query_cpu,
                "retained_sessions": len(self._sessions), "retained_frame_records": len(self._blobs),
                "sessions": [{"game_id": s["context"]["game_id"],
                              "session_id": sid, "attempt": s["context"]["attempt"],
                              "captured_actions": s["context"]["sequence"],
                              "stored_frame_json_bytes": s["bytes"],
                              "metadata_records": len(s["records"]),
                              "metadata_evicted": s["metadata_evicted"], "counts": dict(s["counts"])}
                             for sid, s in self._sessions.items()],
                "recent_queries": _copy_json(list(self._events)),
                "baseline_source_sha256": dict(self._source_hashes),
                "api_note": API_NOTE.strip(),
                "semantics": {
                    "frames": "All public raw SDK return frames, duplicates retained, zero-based; before is separate.",
                    "attempt": "0 initially; increments on each executed RESET, whose result belongs to the new attempt.",
                    "nonlatest": "Reference precedes the latest actually executed action in this session, including RESET.",
                    "bytes": "Exact stored frame JSON / compact response JSON bytes; not process RSS or prompt tokens.",
                    "hash": "SHA256 of UTF-8 json.dumps(grid, separators=(',', ':')); archive_sha256 hashes the full before+frames JSON blob.",
                    "eviction": "FIFO frames by byte/record limits; bounded session metadata; no latest fallback.",
                    "cpu": "thread_time spent in capture bookkeeping/copy and archive queries; excludes actions/models.",
                },
            }

    def install(self) -> None:
        patch = self
        bootstrap = self._sandbox_module._SANDBOX_BOOTSTRAP
        if bootstrap.count(_BOOTSTRAP_ANCHOR) != 1:
            raise RuntimeError("Unsupported sandbox source: action anchor must occur exactly once.")
        if bootstrap.count(_LATEST_ANCHOR) != 1:
            raise RuntimeError("Unsupported sandbox source: latest-animation guard must occur exactly once.")
        modified = bootstrap.replace(_BOOTSTRAP_ANCHOR, _BOOTSTRAP_ANCHOR + _BOOTSTRAP_API)
        modified = modified.replace(_LATEST_ANCHOR, _LATEST_GUARD)
        compile(modified, "<retrievable_animation_sandbox>", "exec")
        self._source_hashes["sandbox_bootstrap_before"] = hashlib.sha256(bootstrap.encode()).hexdigest()
        self._source_hashes["sandbox_bootstrap_after"] = hashlib.sha256(modified.encode()).hexdigest()

        @wraps(self._original_execute)
        def execute(session: Any, action: Any, **kwargs: Any) -> Any:
            started = time.thread_time()
            context = patch._context(session)
            before = patch._solver_module._grid_from_state(session.game.current_state)
            level = patch._solver_module._level_number(session.game)
            step = session.action_count
            before_cpu = time.thread_time() - started
            result = patch._original_execute(session, action, **kwargs)
            started = time.thread_time()
            try:
                patch._capture(session, context, result, before, level, step)
            except Exception as exc:
                # Observation failure cannot undo, repeat or hide an executed action.
                with patch._lock:
                    patch._counts["capture_errors"] += 1
                    patch._events.append({"op": "capture", "status": "error",
                                          "session_id": context["session_id"],
                                          "error": type(exc).__name__})
            finally:
                with patch._lock:
                    patch._capture_cpu += before_cpu + time.thread_time() - started
            return result

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
            original_handler = kwargs.get("animation_handler")

            def animation_handler(request: dict[str, Any]) -> Any:
                if request.get("kind") != QUERY:
                    return original_handler(request) if original_handler is not None else {}
                callback = getattr(agent, "_step_env_callback", None)
                if callback is None:
                    return {"status": "unavailable_session"}
                result = callback({"query": QUERY, "op": request.get("op"),
                                   "limit": request.get("limit", 16), "ref": request.get("ref")})
                if not isinstance(result, dict) or not isinstance(result.get("result"), dict):
                    return {"status": "invalid_host_response"}
                return result["result"]

            kwargs["animation_handler"] = animation_handler
            # A historical handler must not activate the original latest globals
            # when the caller disabled them. The normal state reader ignores this
            # private control field; gameplay state and action feedback are intact.
            kwargs["initial_state"] = {
                **kwargs["initial_state"],
                "_research_latest_animation_enabled": original_handler is not None,
            }
            return patch._original_sandbox(**kwargs)

        self._sandbox_module._SANDBOX_BOOTSTRAP = modified
        self.session_class._execute_action = execute
        self.session_class.step_env = step_env
        self.tool_agent_class._ensure_session = ensure
        self.tool_agent_class._run_python_tool = run_tool
        self._agent_module.run_sandboxed_python = sandbox


def install_retrievable_animation(
    tool_agent_class: type | None = None, session_class: type | None = None, *,
    max_records_per_session: int = 128, max_bytes_per_session: int = 4 * 1024 * 1024,
    max_total_bytes: int = 64 * 1024 * 1024, max_sessions: int = 128,
) -> RetrievableAnimationPatch:
    """Install only in a fresh candidate process; baseline must not call this."""
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if session_class is None:
        session_class = importlib.import_module("inference.framework.solver")._HarnessGameSession
    limits = dict(max_records_per_session=max_records_per_session,
                  max_bytes_per_session=max_bytes_per_session,
                  max_total_bytes=max_total_bytes, max_sessions=max_sessions)
    existing = getattr(tool_agent_class, "_research_retrievable_animation_patch", None)
    if existing is not None:
        if existing.session_class is not session_class or existing.limits != limits:
            raise ValueError("Retrievable animation is already installed with different settings.")
        return existing
    patch = RetrievableAnimationPatch(tool_agent_class, session_class, **limits)
    patch.install()
    tool_agent_class._research_retrievable_animation_patch = patch
    return patch
