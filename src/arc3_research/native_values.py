"""Automatic short-lived native-value handoff, no new model API to learn.

Only successful inspection-only snippets commit. Any executed action
(including no-op or RESET), level/frame change, error/timeout, or action
request prevents a new commit. Commits replace the whole name set so
deletes/rebinds do not resurrect. Host-owned per-session stores, bounded.
"""
from __future__ import annotations

from collections import Counter, OrderedDict, deque
from dataclasses import dataclass
from functools import wraps
import hashlib
import importlib
import inspect
import json
import threading
import time
from typing import Any
import uuid


NV_LIMITS = {"bytes": 65536, "names": 32, "depth": 16, "nodes": 4096,
             "scalar_bytes": 16384, "int_bits": 4096}


class NativeValueError(ValueError):
    pass


def _nv_name(name):
    return (type(name) is str and 0 < len(name) <= 128 and name.isidentifier()
            and not name.startswith("__") and len(name.encode("utf-8")) <= 128)


def encode_values(values, limits=None):
    limits = NV_LIMITS if limits is None else limits
    if type(values) is not dict or len(values) > limits["names"]:
        raise NativeValueError("name_capacity")
    preflight_count = 0
    preflight_active = set()

    def preflight(item, depth):
        nonlocal preflight_count
        preflight_count += 1
        if preflight_count > limits["nodes"]:
            raise NativeValueError("node_capacity")
        if depth > limits["depth"]:
            raise NativeValueError("depth_capacity")
        kind = type(item)
        if kind not in (list, tuple, dict, set, frozenset):
            return
        if id(item) in preflight_active:
            raise NativeValueError("cycle")
        if len(item) > limits["nodes"]:
            raise NativeValueError("node_capacity")
        preflight_active.add(id(item))
        if kind is dict:
            for key, value in item.items():
                preflight(key, depth + 1)
                preflight(value, depth + 1)
        else:
            for value in item:
                preflight(value, depth + 1)
        preflight_active.remove(id(item))

    for value in values.values():
        preflight(value, 0)
    nodes, seen, active = [], {}, set()
    count, charged = 0, 0

    def charge(amount):
        nonlocal charged
        charged += amount
        if charged > limits["bytes"]:
            raise NativeValueError("byte_capacity")

    def visit(item, depth):
        nonlocal count
        count += 1
        if count > limits["nodes"]:
            raise NativeValueError("node_capacity")
        if depth > limits["depth"]:
            raise NativeValueError("depth_capacity")
        kind = type(item)
        if item is None:
            charge(8)
            return ["n"]
        if kind is bool:
            charge(16)
            return ["b", item]
        if kind is int:
            if item.bit_length() > limits["int_bits"]:
                raise NativeValueError("integer_capacity")
            value = str(item)
            charge(len(value) + 16)
            return ["i", value]
        if kind is float:
            if not __import__("math").isfinite(item):
                raise NativeValueError("nonfinite_float")
            value = item.hex()
            charge(len(value) + 16)
            return ["f", value]
        if kind is str:
            if len(item) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            try:
                encoded = json.dumps(item, ensure_ascii=False).encode("utf-8")
            except UnicodeError:
                raise NativeValueError("invalid_unicode") from None
            if len(encoded) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            charge(len(encoded) + 16)
            return ["s", item]
        if kind not in (list, tuple, dict, set, frozenset):
            raise NativeValueError("unsupported_type")
        object_id = id(item)
        if object_id in active:
            raise NativeValueError("cycle")
        if object_id in seen:
            charge(24)
            return ["r", seen[object_id]]
        if len(item) > limits["nodes"]:
            raise NativeValueError("node_capacity")
        charge(48)
        index = len(nodes)
        seen[object_id] = index
        nodes.append(None)
        active.add(object_id)
        if kind is dict:
            content = [[visit(k, depth + 1), visit(v, depth + 1)] for k, v in item.items()]
        else:
            content = [visit(v, depth + 1) for v in item]
        active.remove(object_id)
        nodes[index] = [kind.__name__, content]
        return ["r", index]

    roots = []
    for name, value in values.items():
        if not _nv_name(name):
            raise NativeValueError("invalid_name")
        charge(len(name.encode("utf-8")) + 16)
        roots.append([name, visit(value, 0)])
    blob = json.dumps({"version": 1, "roots": roots, "nodes": nodes},
                      ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(blob) > limits["bytes"]:
        raise NativeValueError("byte_capacity")
    return blob


def decode_values(blob, limits=None):
    import math
    limits = NV_LIMITS if limits is None else limits
    if type(blob) is not bytes or len(blob) > limits["bytes"]:
        raise NativeValueError("invalid_blob")
    try:
        data = json.loads(blob)
    except (ValueError, UnicodeError, RecursionError):
        raise NativeValueError("invalid_json") from None
    if (type(data) is not dict or set(data) != {"version", "roots", "nodes"}
            or type(data["version"]) is not int or data["version"] != 1
            or type(data["roots"]) is not list or type(data["nodes"]) is not list
            or len(data["roots"]) > limits["names"] or len(data["nodes"]) > limits["nodes"]):
        raise NativeValueError("invalid_schema")
    nodes, memo, active = data["nodes"], {}, set()
    count = 0

    def read(node, depth):
        nonlocal count
        count += 1
        if count > limits["nodes"] or depth > limits["depth"]:
            raise NativeValueError("decode_capacity")
        if type(node) is not list or not node or type(node[0]) is not str:
            raise NativeValueError("invalid_node")
        tag = node[0]
        if tag == "n" and len(node) == 1:
            return None
        if len(node) != 2:
            raise NativeValueError("invalid_node")
        value = node[1]
        if tag == "b" and type(value) is bool:
            return value
        if tag == "s" and type(value) is str:
            if len(value.encode("utf-8")) > limits["scalar_bytes"]:
                raise NativeValueError("scalar_capacity")
            return value
        if tag == "i" and type(value) is str:
            if len(value) > limits["int_bits"]:
                raise NativeValueError("integer_capacity")
            try:
                item = int(value)
            except ValueError:
                raise NativeValueError("invalid_integer") from None
            if str(item) != value or item.bit_length() > limits["int_bits"]:
                raise NativeValueError("invalid_integer")
            return item
        if tag == "f" and type(value) is str and len(value) <= 32:
            try:
                item = float.fromhex(value)
            except (ValueError, OverflowError):
                raise NativeValueError("invalid_float") from None
            if not math.isfinite(item) or item.hex() != value:
                raise NativeValueError("invalid_float")
            return item
        if tag != "r" or type(value) is not int or not 0 <= value < len(nodes):
            raise NativeValueError("invalid_reference")
        if value in active:
            raise NativeValueError("cycle")
        if value in memo:
            return memo[value]
        record = nodes[value]
        if (type(record) is not list or len(record) != 2 or type(record[0]) is not str
                or type(record[1]) is not list or len(record[1]) > limits["nodes"]):
            raise NativeValueError("invalid_container")
        kind, content = record
        active.add(value)
        if kind == "dict":
            item = {}
            for pair in content:
                if type(pair) is not list or len(pair) != 2:
                    raise NativeValueError("invalid_pair")
                key, val = read(pair[0], depth + 1), read(pair[1], depth + 1)
                try:
                    if key in item:
                        raise NativeValueError("duplicate_key")
                    item[key] = val
                except TypeError:
                    raise NativeValueError("unhashable_key") from None
        elif kind in ("list", "tuple", "set", "frozenset"):
            children = [read(child, depth + 1) for child in content]
            try:
                item = {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[kind](children)
            except TypeError:
                raise NativeValueError("unhashable_member") from None
            if kind in ("set", "frozenset") and len(item) != len(children):
                raise NativeValueError("duplicate_member")
        else:
            raise NativeValueError("invalid_container_tag")
        active.remove(value)
        memo[value] = item
        return item

    result = {}
    try:
        for root in data["roots"]:
            if type(root) is not list or len(root) != 2 or not _nv_name(root[0]) or root[0] in result:
                raise NativeValueError("invalid_root")
            result[root[0]] = read(root[1], 0)
        if len(memo) != len(nodes):
            raise NativeValueError("unreachable_nodes")
        encode_values(result, limits)
    except (UnicodeError, RecursionError):
        raise NativeValueError("invalid_value") from None
    return result


def capture_namespace(namespace, reserved, limits=None):
    limits = NV_LIMITS if limits is None else limits
    if type(namespace) is not dict:
        raise NativeValueError("invalid_namespace")
    values, rejected = {}, []
    for name, value in namespace.items():
        if not _nv_name(name) or name in reserved:
            continue
        if len(values) + len(rejected) >= limits["names"]:
            raise NativeValueError("name_capacity")
        try:
            encode_values({name: value}, limits)
        except NativeValueError as exc:
            rejected.append({"name": name, "reason": str(exc)})
            continue
        values[name] = value
    return encode_values(values, limits), rejected


_SESSION_ATTR = "_research_native_values_context"
_BOOTSTRAP_ANCHOR = "    def _collect_retention_payload():\n"
_HOST_FINAL_ANCHOR = '                    "result": message.get("result"),\n'
_CHILD_FINAL_ANCHOR = '                "type": "final",\n'

NATIVE_NOTE = (
    "\n\nPython variables from a successful inspection-only snippet are "
    "automatically available in the next snippet on the same board; any "
    "executed action (including no-op or RESET), level change, or new "
    "observation clears them. Re-import modules as needed; eligible functions "
    "are still retained separately. Do not assume a variable survived an "
    "action\u2014recompute after acting."
)


@dataclass(frozen=True)
class _Observation:
    session_id: str
    attempt: int
    action_num: int
    level: int
    frame_sha256: str
    revision: int


@dataclass(frozen=True)
class _Ticket:
    serial: int
    generation: int
    observation: _Observation


class NativeValuesPatch:
    """Host-owned one-blob-per-session stores with strict identity binding."""

    def __init__(self, tool_agent_class: type, session_class: type, **limits: int) -> None:
        if any(type(v) is not int or v < 1 for v in limits.values()):
            raise ValueError("Native-value limits must be positive integers.")
        self.limits = limits
        self.tool_agent_class = tool_agent_class
        self.session_class = session_class
        self._agent_module = importlib.import_module(tool_agent_class.__module__)
        self._solver_module = importlib.import_module(session_class.__module__)
        self._original_execute = session_class._execute_action
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
        self._tool_cpu = 0.0
        self._action_cpu = 0.0
        self._serial = 0
        self._source_hashes = {
            name: hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()
            for name, fn in {
                "session._execute_action": self._original_execute,
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
                   "identity": self._identity(session), "inflight": 0,
                   "observation": None, "blob": encode_values({}), "generation": 0,
                   "pending": None}
        setattr(session, _SESSION_ATTR, context)
        while len(self._sessions) >= self.limits["max_sessions"]:
            _, old = self._sessions.popitem(last=False)
            self._bytes -= old["bytes"]
            self._counts["evicted_sessions"] += 1
        self._sessions[context["session_id"]] = {
            "context": context, "bytes": 0, "counts": Counter()}
        self._counts["sessions_seen"] += 1
        return context

    def _observation(self, context: dict[str, Any]) -> _Observation:
        ident = context["identity"]
        return _Observation(session_id=context["session_id"], attempt=int(context["attempt"]),
                            action_num=int(ident["action_num"]), level=int(ident["level"]),
                            frame_sha256=str(ident["frame_sha256"]), revision=int(context["revision"]))

    def _invalidate(self, context: dict[str, Any], reason: str) -> None:
        store = self._sessions.get(context["session_id"])
        if store is None:
            return
        freed = store["bytes"]
        self._bytes -= freed
        store["bytes"] = 0
        store["counts"]["invalidations"] += 1
        self._counts["invalidations"] += 1
        self._counts["invalidated_bytes"] += freed
        context["blob"] = encode_values({})
        context["observation"] = self._observation(context)
        context["generation"] += 1
        context["pending"] = None

    def _sync(self, session: Any, context: dict[str, Any]) -> None:
        identity = self._identity(session)
        if identity != context["identity"]:
            self._invalidate(context, "host_observation_changed")
            context["identity"] = identity
            context["revision"] += 1
            context["observation"] = self._observation(context)
            self._counts["observation_resyncs"] += 1

    @staticmethod
    def _cpu_now():
        try:
            return time.thread_time()
        except Exception:
            return None

    @classmethod
    def _cpu_elapsed(cls, started):
        ended = cls._cpu_now()
        return max(0.0, ended - started) if started is not None and ended is not None else 0.0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "intervention": "native-values-v1",
                "enabled": True, "limits": dict(self.limits),
                "counts": dict(self._counts),
                "stored_value_bytes": self._bytes, "peak_stored_value_bytes": self._peak_bytes,
                "tool_cpu_seconds": self._tool_cpu, "action_boundary_cpu_seconds": self._action_cpu,
                "sessions": [{"game_id": s["context"]["game_id"],
                              "stored_value_bytes": s["bytes"],
                              "counts": dict(s["counts"])} for s in self._sessions.values()],
                "recent_events": list(self._events),
                "baseline_source_sha256": dict(self._source_hashes),
                "note": NATIVE_NOTE.strip(),
                "semantics": {
                    "commit": "Only successful snippets with zero action calls commit; whole namespace replaces prior set.",
                    "invalidation": "Any executed action (incl no-op/RESET), identity change, error/timeout clears; refused preserves prior but commits nothing.",
                    "binding": "session/attempt/action/level/frame_sha256/revision; child cannot choose identity.",
                    "bytes": "Bounded DAG codec bytes, not RSS; exact builtins only, no pickle/protocols.",
                },
            }

    def install(self) -> None:
        patch = self
        bootstrap = self._sandbox_module._SANDBOX_BOOTSTRAP
        if bootstrap.count(_BOOTSTRAP_ANCHOR) != 1:
            raise RuntimeError("Unsupported sandbox: retention anchor changed.")
        if bootstrap.count(_CHILD_FINAL_ANCHOR) != 1:
            raise RuntimeError("Unsupported sandbox: final anchor changed.")
        codec_source = "\n".join([
            "import math",
            "NV_LIMITS = " + repr(NV_LIMITS),
            inspect.getsource(NativeValueError),
            inspect.getsource(_nv_name),
            inspect.getsource(encode_values),
            inspect.getsource(decode_values),
            inspect.getsource(capture_namespace),
        ]) + "\n"
        restore = '''    _nv_reserved = set(runtime_globals) | set(runtime_globals["__builtins__"])
    try:
        _nv_raw = initial.get("state", {}).get("_native_values", "")
        _nv_restored = decode_values(_nv_raw.encode("utf-8")) if type(_nv_raw) is str and _nv_raw else {}
    except Exception:
        raise NativeValueError("reserved_name_collision")
    if set(_nv_restored) & _nv_reserved:
        raise NativeValueError("reserved_name_collision")
    runtime_globals.update(_nv_restored)

    def _native_snapshot():
        try:
            blob, rejected = capture_namespace(runtime_globals, _nv_reserved)
            return {"blob": blob.decode("utf-8"), "rejected": rejected}
        except NativeValueError as exc:
            return {"blob": None, "reason": str(exc)}

'''
        modified = codec_source + "\n" + bootstrap.replace(_BOOTSTRAP_ANCHOR, restore + _BOOTSTRAP_ANCHOR)
        modified = modified.replace(_CHILD_FINAL_ANCHOR,
                                    _CHILD_FINAL_ANCHOR + '                "native_values": _native_snapshot(),\n')
        compile(modified, "<native_values_sandbox>", "exec")
        self._source_hashes["sandbox_bootstrap_before"] = hashlib.sha256(bootstrap.encode()).hexdigest()
        self._source_hashes["sandbox_bootstrap_after"] = hashlib.sha256(modified.encode()).hexdigest()

        source = inspect.getsource(self._original_sandbox)
        if source.count(_HOST_FINAL_ANCHOR) != 1:
            raise RuntimeError("Unsupported runner: host final anchor changed.")
        namespace = dict(vars(self._sandbox_module))
        namespace["_SANDBOX_BOOTSTRAP"] = modified
        exec(compile(source.replace(
            _HOST_FINAL_ANCHOR,
            _HOST_FINAL_ANCHOR + '                    "native_values": message.get("native_values"),\n'),
            "<native_values_runner>", "exec"), namespace)
        wrapped_runner = namespace["run_sandboxed_python"]

        @wraps(self._original_execute)
        def execute(session: Any, action: Any, **kwargs: Any) -> Any:
            started = patch._cpu_now()
            context = None
            try:
                with patch._lock:
                    context = patch._context(session)
                    patch._sync(session, context)
                    context["inflight"] += 1
            except Exception:
                context = getattr(session, _SESSION_ATTR, None)
            before_cpu = patch._cpu_elapsed(started)
            result = None
            try:
                result = patch._original_execute(session, action, **kwargs)
                return result
            except Exception:
                try:
                    with patch._lock:
                        if context is not None:
                            patch._invalidate(context, "action_error")
                            context["revision"] += 1
                            context["inflight"] = max(0, context["inflight"] - 1)
                            patch._counts["action_observer_errors"] += 1
                except Exception:
                    pass
                raise
            else:
                return result
            finally:
                if result is not None or context is not None:
                    started2 = patch._cpu_now()
                    try:
                        with patch._lock:
                            if context is not None and context.get("inflight", 0) > 0:
                                try:
                                    identity = patch._identity(session)
                                    executed = isinstance(result, dict) and result.get("executed") is True
                                    changed = identity != context["identity"]
                                    if executed or changed:
                                        patch._invalidate(context, "action_executed")
                                        context["revision"] += 1
                                        try:
                                            if getattr(getattr(action, "id", None), "name", None) == "RESET":
                                                context["attempt"] += 1
                                        except Exception:
                                            pass
                                        context["identity"] = identity
                                        context["observation"] = patch._observation(context)
                                        patch._counts["executed_action_boundaries"] += 1
                                except Exception:
                                    try:
                                        patch._invalidate(context, "unavailable_observation")
                                    except Exception:
                                        pass
                                    patch._counts["action_observer_errors"] += 1
                                finally:
                                    context["inflight"] = max(0, context["inflight"] - 1)
                    except Exception:
                        pass
                    try:
                        with patch._lock:
                            patch._action_cpu += before_cpu + patch._cpu_elapsed(started2)
                    except Exception:
                        pass

        @wraps(self._original_ensure)
        def ensure(agent: Any, state_path: Any) -> Any:
            result = patch._original_ensure(agent, state_path)
            try:
                if NATIVE_NOTE not in agent._system_prompt:
                    agent._system_prompt += NATIVE_NOTE
            except Exception:
                pass
            return result

        @wraps(self._original_tool)
        def run_tool(agent: Any, state_path: Any, arguments: dict[str, Any]) -> Any:
            started = patch._cpu_now()
            ticket = None
            session = None
            try:
                callback = getattr(agent, "_step_env_callback", None)
                session = getattr(callback, "__self__", None)
            except Exception:
                session = None
            blob_str = ""
            observation = None
            if session is not None and hasattr(session, "game"):
                try:
                    with patch._lock:
                        context = patch._context(session)
                        patch._sync(session, context)
                        observation = patch._observation(context)
                        if observation != context.get("observation"):
                            patch._invalidate(context, "observation_changed_at_begin")
                            context["identity"] = patch._identity(session)
                            observation = patch._observation(context)
                        patch._serial += 1
                        ticket = _Ticket(serial=patch._serial,
                                         generation=int(context["generation"]),
                                         observation=observation)
                        context["pending"] = ticket
                        context["observation"] = observation
                        blob_str = context["blob"].decode("utf-8")
                        patch._counts["snippets"] += 1
                    patch._local.ticket = ticket
                    patch._local.session = session
                    patch._local.observation = observation
                except Exception:
                    ticket = None
            else:
                try:
                    patch._local.ticket = None
                    patch._local.session = None
                    patch._local.observation = None
                except Exception:
                    pass
            try:
                return patch._original_tool(agent, state_path, arguments)
            finally:
                try:
                    with patch._lock:
                        patch._tool_cpu += patch._cpu_elapsed(started)
                except Exception:
                    pass
                try:
                    patch._local.ticket = None
                except Exception:
                    pass

        @wraps(self._original_sandbox)
        def sandbox(**kwargs: Any) -> Any:
            ticket = getattr(patch._local, "ticket", None)
            session = getattr(patch._local, "session", None)
            state = dict(kwargs.get("initial_state") or {})
            if ticket is not None and session is not None:
                try:
                    with patch._lock:
                        context = patch._context(session)
                        state["_native_values"] = context["blob"].decode("utf-8")
                except Exception:
                    state["_native_values"] = ""
            else:
                state["_native_values"] = ""
            kwargs["initial_state"] = state
            result = wrapped_runner(**kwargs)
            if ticket is None or session is None:
                return result
            try:
                with patch._lock:
                    context = patch._context(session)
                    if context.get("pending") != ticket:
                        patch._counts["stale_ticket"] += 1
                        patch._events.append({"event": "stale_ticket"})
                        return result
                    context["pending"] = None
                    live_identity = patch._identity(session)
                    live_obs = _Observation(session_id=context["session_id"],
                                            attempt=int(context["attempt"]),
                                            action_num=int(live_identity["action_num"]),
                                            level=int(live_identity["level"]),
                                            frame_sha256=str(live_identity["frame_sha256"]),
                                            revision=int(context["revision"]))
                    action_results = result.get("action_results") or []
                    requested = len([r for r in action_results if isinstance(r, dict)])
                    error = str(result.get("error") or "")
                    snapshot = result.get("native_values") or {}
                    final_blob = snapshot.get("blob")
                    if live_obs != ticket.observation:
                        patch._invalidate(context, "observation_changed_during_snippet")
                        context["identity"] = live_identity
                        context["revision"] += 1
                        context["observation"] = patch._observation(context)
                        patch._counts["no_commit_observation_change"] += 1
                        patch._events.append({"event": "observation_change"})
                        return result
                    if ticket.generation != context["generation"]:
                        patch._counts["no_commit_generation_changed"] += 1
                        return result
                    if requested:
                        patch._counts["no_commit_action_requested"] += 1
                        patch._events.append({"event": "action_requested"})
                        return result
                    if error:
                        patch._counts["no_commit_snippet_failed"] += 1
                        return result
                    if type(final_blob) is not str or not final_blob:
                        patch._invalidate(context, "invalid_snapshot_cleared")
                        patch._counts["invalid_snapshot_cleared"] += 1
                        return result
                    try:
                        values = decode_values(final_blob.encode("utf-8"))
                    except (NativeValueError, TypeError, ValueError):
                        patch._invalidate(context, "invalid_snapshot_cleared")
                        patch._counts["invalid_snapshot_cleared"] += 1
                        return result
                    new_blob = encode_values(values)
                    store = patch._sessions.get(context["session_id"])
                    freed = store["bytes"] if store else 0
                    patch._bytes -= freed
                    if store is not None:
                        store["bytes"] = len(new_blob)
                        store["counts"]["commits"] += 1
                    patch._bytes += len(new_blob)
                    patch._peak_bytes = max(patch._peak_bytes, patch._bytes)
                    context["blob"] = new_blob
                    context["observation"] = live_obs
                    patch._counts["commits"] += 1
                    patch._counts["committed_bytes"] += len(new_blob)
                    patch._counts["committed_names"] += len(values)
                    if snapshot.get("rejected"):
                        patch._counts["rejected_names"] += len(snapshot["rejected"])
                    patch._events.append({"event": "commit", "names": len(values), "bytes": len(new_blob)})
            except Exception as exc:
                try:
                    with patch._lock:
                        patch._counts["finish_errors"] += 1
                except Exception:
                    pass
            return result

        self._sandbox_module._SANDBOX_BOOTSTRAP = modified
        self._agent_module.run_sandboxed_python = sandbox
        self.session_class._execute_action = execute
        self.tool_agent_class._ensure_session = ensure
        self.tool_agent_class._run_python_tool = run_tool
        self._wrapped_runner = wrapped_runner
        self._modified_bootstrap = modified

    def uninstall(self) -> None:
        import inference.agent.python_tool_sandbox as sandbox_module
        try:
            bootstrap = sandbox_module._SANDBOX_BOOTSTRAP
            if getattr(self, "_modified_bootstrap", None) is not None and bootstrap == self._modified_bootstrap:
                pass
        except Exception:
            pass
        self.tool_agent_class._run_python_tool = self._original_tool
        self.tool_agent_class._ensure_session = self._original_ensure
        self.session_class._execute_action = self._original_execute
        try:
            self._agent_module.run_sandboxed_python = self._original_sandbox
        except Exception:
            pass


def install_native_values(
    tool_agent_class: type | None = None, session_class: type | None = None, *,
    max_session_bytes: int = 64 * 1024, max_sessions: int = 128,
) -> NativeValuesPatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if session_class is None:
        session_class = importlib.import_module("inference.framework.solver")._HarnessGameSession
    limits = dict(max_session_bytes=max_session_bytes, max_sessions=max_sessions)
    existing = getattr(tool_agent_class, "_research_native_values_patch", None)
    if existing is not None:
        if existing.session_class is not session_class or existing.limits != limits:
            raise ValueError("Native values already installed with different settings.")
        return existing
    patch = NativeValuesPatch(tool_agent_class, session_class, **limits)
    patch.install()
    tool_agent_class._research_native_values_patch = patch
    return patch
