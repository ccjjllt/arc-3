"""Bounded, passive observations at the original gate's actual heap operations.

Install after inference_timing. The timing patch's existing play-thread context
supplies session identity; no play, request, clock, Condition or heap wrapper is
added. Only two exact-source function code objects receive fail-open callbacks.
The original lock acquisition, heap operations, order and notifications remain.
"""
from __future__ import annotations

import __future__
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import itertools
import math
import os
import textwrap
import time
from typing import Any


_HOOK = "_research_scheduler_observer_emit_014"
_MARKER = "_research_scheduler_observer_patch"
_EXPECTED = {
    "_enqueue_and_wait": "2566cc1fbfe7ae3c1d9bd477f25c18c648b0b3abf275042994af350948d837c4",
    "_pump": "ba31553ddbd59e4f6613e7e6789d54484bbfe353bad67274fa8c5bdf4232cadc",
}
_SNAPSHOT_FIELDS = ("level", "actions", "tokens", "cost_multiplier", "total_levels")
_OWNER_FIELDS = ("session_id", "game_id", "game_index", "pass_index")
_CONFIG_FIELDS = (
    "ARC3_MAX_ACTIVE_STREAMS", "ARC3_PRIORITY_REFRESH_QUEUE", "ARC3_PRIORITY_PACE",
    "ARC3_PRIORITY_TAIL_LOOKUP", "ARC3_PRIORITY_TAIL_FADE",
    "ARC3_PRIORITY_TAIL_FADE_FRACTION", "ARC3_PRIORITY_SCORE_NORMALIZATION",
)


def _canonical_source(function: Any) -> str:
    return textwrap.dedent(inspect.getsource(function)).strip() + "\n"


def _sha(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


def _number(value: Any) -> int | float | None:
    return value if type(value) in (int, float) and math.isfinite(value) else None


def _callback(indent: str, kind: str, arguments: str = "") -> str:
    return (f"{indent}try:\n"
            f"{indent}    {_HOOK}(self, {kind!r}{arguments})\n"
            f"{indent}except BaseException:\n"
            f"{indent}    pass\n")


def _instrument(name: str, source: str) -> str:
    """Insert only callbacks, with exact anchors checked before any mutation."""
    anchors = {
        "_enqueue_and_wait": [
            ("    heapq.heappush(self._waiting, (-int(priority), token))\n",
             _callback("    ", "enqueue", ", token=token, priority=priority")),
        ],
        "_pump": [
            ("def _pump(self) -> None:\n", _callback("    ", "pump_begin")),
            ("        heapq.heapify(self._waiting)\n",
             _callback("        ", "reprice", ", scored_at=now")),
            ("        _, token = heapq.heappop(self._waiting)\n",
             _callback("        ", "selection", ", token=token, priority=-_")),
        ],
    }
    for before, addition in anchors[name]:
        if source.count(before) != 1:
            raise ValueError(f"Scheduler observer anchor mismatch: {name}: {before.strip()}")
        source = source.replace(before, before + addition, 1)
    return source


class SchedulerObserverPatch:
    def __init__(self, tool_agent_class: type, *, timing_patch: Any,
                 max_gates: int, max_events: int, max_candidates: int) -> None:
        if any(type(n) is not int or n < 1 for n in (max_gates, max_events, max_candidates)):
            raise ValueError("Scheduler observation limits must be positive integers.")
        self.tool_agent_class = tool_agent_class
        self.timing_patch = timing_patch
        self.limits = dict(max_gates=max_gates, max_events=max_events, max_candidates=max_candidates)
        self._module = importlib.import_module(tool_agent_class.__module__)
        self._gate_class = self._module._PriorityGate
        self._functions = {name: inspect.unwrap(getattr(self._gate_class, name)) for name in _EXPECTED}
        self._old_codes = {}
        self._new_codes = {}
        self._source_hashes = {}
        self._instrumented_hashes = {}
        # Preflight every function before changing any live function or global.
        if _HOOK in self._module.__dict__:
            raise ValueError("Scheduler observer hook global is already occupied.")
        for name, function in self._functions.items():
            if function.__globals__ is not self._module.__dict__ or function.__closure__:
                raise ValueError(f"Unexpected gate function globals/closure: {name}")
            source = _canonical_source(function)
            digest = _sha(source)
            if digest != _EXPECTED[name]:
                raise ValueError(f"Scheduler observer requires audited {name} source; got {digest}")
            instrumented = _instrument(name, source)
            namespace: dict[str, Any] = {}
            compiled = compile(instrumented, f"<arc3-scheduler-observer:{name}>", "exec",
                               flags=__future__.annotations.compiler_flag, dont_inherit=True)
            exec(compiled, function.__globals__, namespace)
            self._old_codes[name] = function.__code__
            self._new_codes[name] = namespace[name].__code__
            self._source_hashes[name] = digest
            self._instrumented_hashes[name] = _sha(instrumented)
        self._origin = time.monotonic()
        self._origin_utc = datetime.now(timezone.utc).isoformat()
        self._gate_serial = itertools.count(1)
        self._event_serial = itertools.count(1)
        self._gates: dict[int, dict[str, Any]] = {}
        self._events: deque = deque(maxlen=max_events)
        self._counts: Counter = Counter()
        self._record_errors = 0
        self._installed = False
        self._config = {key: os.environ.get(key) for key in _CONFIG_FIELDS}

    def _state(self, gate: Any) -> dict[str, Any] | None:
        key = id(gate)
        state = self._gates.get(key)
        if state is None:
            serial = next(self._gate_serial)
            if serial > self.limits["max_gates"]:
                return None
            state = {"gate": gate, "gate_id": f"g{serial:03d}", "owners": {},
                     "counts": Counter(), "max_waiting": 0, "owner_omissions": 0}
            self._gates[key] = state
        return state

    @staticmethod
    def _snapshot_values(value: Any) -> tuple | None:
        return None if value is None else tuple(_number(getattr(value, k, None)) for k in _SNAPSHOT_FIELDS)

    def _owner(self) -> tuple | None:
        context = getattr(getattr(self.timing_patch, "_local", None), "session", None)
        if context is None:
            return None
        return tuple(context.get(key) for key in _OWNER_FIELDS)

    def _candidate(self, gate: Any, state: dict, token: int, priority: int) -> tuple:
        return (token, _number(priority),
                self._snapshot_values(gate._snapshots.get(token)), state["owners"].get(token))

    def _record(self, gate: Any, kind: str, *, token: int | None = None,
                priority: int | None = None, scored_at: float | None = None) -> None:
        """Called only inside the original Condition. No added locks or I/O."""
        state = self._state(gate)
        if state is None:
            return
        if kind == "enqueue":
            if len(state["owners"]) < self.limits["max_candidates"]:
                state["owners"][token] = self._owner()
            else:
                state["owner_omissions"] += 1
        selected = self._candidate(gate, state, token, priority) if kind == "selection" else None
        # At selection the actual heappop has just happened. Prepend its result
        # to reconstruct the exact candidate membership before that pop. Heap
        # array order is not a sorted rank, and is never changed by observation.
        rows = [selected] if selected is not None else []
        total = len(gate._waiting) + len(rows)
        room = self.limits["max_candidates"] - len(rows)
        rows.extend(self._candidate(gate, state, t, -p)
                    for p, t in itertools.islice(gate._waiting, max(0, room)))
        stamp = time.monotonic()
        sequence = next(self._event_serial)
        self._events.append((sequence, stamp, kind, state["gate_id"], gate._free,
                             gate._seq, _number(gate._clock_start), _number(gate._clock_deadline),
                             _number(scored_at), total, tuple(rows), selected))
        state["counts"][kind] += 1
        state["max_waiting"] = max(state["max_waiting"], total)
        self._counts[kind] += 1
        if kind == "selection":
            state["owners"].pop(token, None)

    def _emit(self, *args: Any, **kwargs: Any) -> None:
        try:
            self._record(*args, **kwargs)
        except BaseException:
            # Callback faults never replace original scheduler errors/returns.
            # The injected call site also catches failures of this method itself.
            self._record_errors += 1

    def install(self) -> None:
        self._module.__dict__[_HOOK] = self._emit
        try:
            for name, function in self._functions.items():
                function.__code__ = self._new_codes[name]
        except BaseException:
            for name, function in self._functions.items():
                function.__code__ = self._old_codes[name]
            self._module.__dict__.pop(_HOOK, None)
            raise
        self._installed = True
        setattr(self.tool_agent_class, _MARKER, self)

    def uninstall(self) -> None:
        if not self._installed:
            return
        # Do not silently overwrite somebody else's later code replacement.
        for name, function in self._functions.items():
            if function.__code__ is not self._new_codes[name]:
                raise RuntimeError(f"Gate function changed after observer install: {name}")
        for name, function in self._functions.items():
            function.__code__ = self._old_codes[name]
        self._module.__dict__.pop(_HOOK, None)
        if getattr(self.tool_agent_class, _MARKER, None) is self:
            delattr(self.tool_agent_class, _MARKER)
        self._installed = False

    @staticmethod
    def _public_candidate(row: tuple | None) -> dict | None:
        if row is None:
            return None
        token, priority, snapshot, owner = row
        return {"token": token, "priority": priority,
                "snapshot": None if snapshot is None else dict(zip(_SNAPSHOT_FIELDS, snapshot)),
                "session": None if owner is None else dict(zip(_OWNER_FIELDS, owner))}

    def snapshot(self) -> dict[str, Any]:
        events = []
        for event in list(self._events):
            seq, stamp, kind, gate_id, free, gate_seq, start, deadline, scored_at, total, rows, selected = event
            events.append({
                "seq": seq, "monotonic": stamp, "t": stamp - self._origin,
                "kind": kind, "gate_id": gate_id, "free_slots_at_hook": free, "gate_seq": gate_seq,
                "clock_start_monotonic": start, "clock_deadline_monotonic": deadline,
                "scored_at_monotonic": scored_at, "candidate_count": total,
                "candidates_omitted": max(0, total - len(rows)),
                "candidates": [self._public_candidate(row) for row in rows],
                "selected": self._public_candidate(selected),
            })
        observed = self._event_serial.__reduce__()[1][0] - 1
        return {
            "observer": "scheduler-observer-v1", "installed": self._installed,
            "limits": dict(self.limits), "clock_origin_monotonic": self._origin,
            "clock_origin_utc": self._origin_utc,
            "timing_clock_origin_monotonic": getattr(self.timing_patch, "_origin", None),
            "timing_session_mapping_available": self.timing_patch is not None,
            "config_at_install": dict(self._config),
            "source_sha256": dict(self._source_hashes),
            "instrumented_source_sha256": dict(self._instrumented_hashes),
            "events_observed": observed, "events_dropped": max(0, observed - len(events)),
            "observer_record_errors": self._record_errors, "counts": dict(self._counts),
            "gates": [{"gate_id": state["gate_id"], "counts": dict(state["counts"]),
                       "max_waiting": state["max_waiting"],
                       "owner_mappings_omitted": state["owner_omissions"],
                       "currently_waiting": len(state["gate"]._waiting)} for state in list(self._gates.values())],
            "events": events,
            "semantics": {
                "enqueue": "Immediately after the original heappush, before pump; session mapping comes from the existing timing play scope.",
                "reprice": "Immediately after the original heapify; scored_at is the original common timestamp used for every refreshed snapshot.",
                "selection": "Immediately after the original heappop, before snapshot deletion, admitted.add, free decrement or notify. The selected row plus remaining heap reconstructs candidate membership at that decision, not caller-return order.",
                "priority": "Actual positive heap priority. Snapshot is the original immutable PrioritySnapshot, or null for initial admission without one. Candidate array is heap membership, not sorted rank.",
                "identity": "Waiting token ownership is captured at enqueue; selection may be performed by a different release/handover thread. Missing mappings stay null.",
                "limits": "Newest bounded events and bounded candidate prefix. Counts survive eviction; omissions are explicit. No added locks, file I/O, model requests, scoring calls or sorting.",
                "snapshot": "Call after worker drain for a consistent final report. Live snapshots are best-effort and do not acquire the gate lock.",
            },
        }


def install_scheduler_observer(tool_agent_class: type | None = None, *,
                               timing_patch: Any = None, max_gates: int = 4,
                               max_events: int = 4096, max_candidates: int = 128) -> SchedulerObserverPatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    if timing_patch is None:
        timing_patch = getattr(tool_agent_class, "_research_inference_timing_patch", None)
    existing = getattr(tool_agent_class, _MARKER, None)
    limits = dict(max_gates=max_gates, max_events=max_events, max_candidates=max_candidates)
    if existing is not None:
        if existing.timing_patch is not timing_patch or existing.limits != limits:
            raise ValueError("Scheduler observer already installed with different settings.")
        return existing
    patch = SchedulerObserverPatch(tool_agent_class, timing_patch=timing_patch, **limits)
    patch.install()
    return patch
