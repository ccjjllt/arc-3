"""CPU-only native-value lifecycle plus an isolated copy of the real runner.

No production monkey-patch is installed. The caller supplies synthetic action
feedback and host observation identities. Full ToolAgent/SDK integration is a
separate, unimplemented step.
"""
from dataclasses import dataclass
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

from codec import NV_LIMITS, NativeValueError, capture_namespace, decode_values, encode_values


@dataclass(frozen=True)
class Observation:
    session: str
    attempt: int
    action: int
    level: int
    frame_sha256: str
    revision: int = 0

    def __post_init__(self):
        if type(self.session) is not str or not self.session or len(self.session) > 128:
            raise ValueError("invalid session")
        if any(type(v) is not int or v < 0 for v in (self.attempt, self.action, self.level, self.revision)):
            raise ValueError("invalid observation counter")
        if (type(self.frame_sha256) is not str or len(self.frame_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.frame_sha256)):
            raise ValueError("invalid frame digest")


@dataclass(frozen=True)
class Ticket:
    serial: int
    generation: int
    observation: Observation


class NativeStore:
    """One host session, one committed immutable blob, one active snippet."""
    def __init__(self):
        self.observation = None
        self.blob = encode_values({})
        self.generation = 0
        self.serial = 0
        self.pending = None

    def invalidate(self, observation=None):
        self.blob = encode_values({})
        self.observation = observation
        self.generation += 1

    def begin(self, observation):
        if self.pending is not None:
            raise RuntimeError("overlapping snippets unsupported")
        if observation != self.observation:
            self.invalidate(observation)
        self.serial += 1
        self.pending = Ticket(self.serial, self.generation, observation)
        return self.pending, self.blob

    def finish(self, ticket, observation, *, successful, blob=None,
               action_requests=0, executed_actions=0, action_uncertain=False):
        if ticket != self.pending:
            return {"committed": False, "reason": "stale_ticket"}
        self.pending = None
        if executed_actions or action_uncertain or observation != ticket.observation:
            self.invalidate(observation)
            return {"committed": False, "reason": "action_or_observation_change"}
        if ticket.generation != self.generation:
            return {"committed": False, "reason": "generation_changed"}
        if action_requests:
            return {"committed": False, "reason": "action_requested"}
        if not successful:
            return {"committed": False, "reason": "snippet_failed"}
        try:
            values = decode_values(blob)
        except (NativeValueError, TypeError):
            # The snippet succeeded, so prior bindings may have been deleted
            # or rebound. Keeping the old snapshot would resurrect old values.
            self.invalidate(observation)
            return {"committed": False, "reason": "invalid_snapshot_cleared"}
        self.blob = encode_values(values)
        self.observation = observation
        return {"committed": True, "reason": "successful_no_action",
                "names": list(values), "bytes": len(self.blob)}


def copied_runner(root):
    """Compile an in-memory runner copy with narrow, counted source anchors."""
    runtime = Path(root) / "research/runtime-bundle/src/ARC3-Inference"
    sys.path.insert(0, str(runtime))
    # Avoid inference.agent.__init__, which imports the whole ToolAgent stack.
    # This probe needs only the real stdlib sandbox and its stdlib helpers.
    name = "_native015_original_sandbox"
    spec = importlib.util.spec_from_file_location(name, runtime / "inference/agent/python_tool_sandbox.py")
    original = importlib.util.module_from_spec(spec)
    sys.modules[name] = original
    spec.loader.exec_module(original)
    import codec
    bootstrap = original._SANDBOX_BOOTSTRAP
    codec_source = inspect.getsource(codec)
    before = "    def _collect_retention_payload():\n"
    restore = '''    _nv_reserved = set(runtime_globals) | set(runtime_globals["__builtins__"])
    _nv_restored = decode_values(initial.get("state", {}).get("_native_values", "").encode("utf-8"))
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
    if bootstrap.count(before) != 1:
        raise RuntimeError("retention anchor changed")
    bootstrap = codec_source + "\n" + bootstrap.replace(before, restore + before)
    anchor = '                "type": "final",\n'
    if bootstrap.count(anchor) != 1:
        raise RuntimeError("successful final anchor changed")
    bootstrap = bootstrap.replace(anchor, anchor + '                "native_values": _native_snapshot(),\n')
    compile(bootstrap, "<015_sandbox_copy>", "exec")
    source = inspect.getsource(original.run_sandboxed_python)
    anchor = '                    "result": message.get("result"),\n'
    if source.count(anchor) != 1:
        raise RuntimeError("host final anchor changed")
    source = source.replace(anchor, anchor + '                    "native_values": message.get("native_values"),\n')
    namespace = dict(vars(original))
    namespace["_SANDBOX_BOOTSTRAP"] = bootstrap
    exec(compile(source, "<015_runner_copy>", "exec"), namespace)
    return namespace["run_sandboxed_python"], {
        "original_bootstrap_sha256": hashlib.sha256(original._SANDBOX_BOOTSTRAP.encode()).hexdigest(),
        "copied_bootstrap_sha256": hashlib.sha256(bootstrap.encode()).hexdigest(),
        "original_runner_unchanged": original.run_sandboxed_python is not namespace["run_sandboxed_python"],
    }


class SyntheticSession:
    """Manual-probe carrier; this class is deliberately not a live SDK patch."""
    def __init__(self, runner, session="synthetic-015"):
        self.runner = runner
        self.store = NativeStore()
        self.current = Observation(session, 0, 0, 1, "0" * 64)
        self.functions = []
        self.action_calls = 0

    def run(self, code, *, action_mode="execute", timeout=3):
        ticket, blob = self.store.begin(self.current)
        requested, executed, uncertain = 0, 0, False
        state = {"current_frame": {"ascii": "WW\nWW", "grid": [[0, 0], [0, 0]],
                                   "shape": [2, 2], "step": self.current.action, "level": 1},
                 "history": [], "valid_actions": ["ACTION1", "RESET"],
                 "_native_values": blob.decode("utf-8")}

        def handler(actions, **kwargs):
            nonlocal requested, executed, uncertain
            requested += 1
            self.action_calls += 1
            if action_mode == "refuse":
                return {"action_result": {"executed": False}, "state": state}
            if action_mode == "uncertain":
                uncertain = True
                self.store.invalidate(self.current)
                raise RuntimeError("synthetic post-execution failure")
            executed += 1
            reset = any(a.get("action") == "RESET" for a in actions)
            self.current = Observation(self.current.session, self.current.attempt + int(reset),
                                       self.current.action + 1, self.current.level,
                                       self.current.frame_sha256, self.current.revision + 1)
            # Invalidated at the real execution boundary, before final/timeout.
            self.store.invalidate(self.current)
            return {"action_result": {"executed": True, "gameplay_changed": False}, "state": state}

        result = self.runner(code=code, timeout_seconds=timeout, initial_state=state,
                             action_handler=handler, kept_functions=self.functions,
                             retain_imports=True, repair_hints=True)
        self.functions = [v["source"] for v in result.get("keepable_functions", [])]
        snapshot = result.get("native_values") or {}
        final_blob = snapshot.get("blob")
        outcome = self.store.finish(ticket, self.current, successful=not bool(result.get("error")),
                                    blob=final_blob.encode("utf-8") if type(final_blob) is str else None,
                                    action_requests=requested, executed_actions=executed,
                                    action_uncertain=uncertain)
        return {"result": result, "commit": outcome,
                "action_requests": requested, "executed_actions": executed}
