"""025 candidate: 009 first-admission priority (research arm, no submission).

Scope: change ONLY the new-game first-entry priority. The base puts every
fresh game in the top band (``_PRIORITY_UNTRIMMED_BASE - queue_position``)
so admissions drain in dispatch order; every later requeue already uses a
snapshot estimate. This patch substitutes the 009 value for that single
first ``acquire()`` call:

    PrioritySnapshot(level=1, actions=0, tokens=0.0, cost_multiplier=1.0,
                     total_levels=N) through the gate's own
    ``_snapshot_priority(now)`` (remaining tail, normalized score,
    contemporaneous fade) — the identical call the base makes for started
    games, so no formula drift is possible.

Seam: ``_HarnessGameSession._queue_position`` (per-session, race-free under
16-stream concurrency; the shared gate is only read). Fail-safe: any error
returns the original position (2M band) and records a fallback. Install
before timing/observer patches, uninstall after them (reverse order).
"""
from __future__ import annotations

import threading
import time
from typing import Any


class AdmissionOrderPatch:
    """Wraps one method; no global hooks."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.substitutions: list[dict[str, Any]] = []
        self.fallbacks = 0
        self._original = None
        self._installed = None
        self._session_cls = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"patch": "admission-order-009-v1",
                    "substitutions": list(self.substitutions),
                    "fallbacks": self.fallbacks,
                    "rule": "first acquire only; later requeues unchanged; "
                            "fail-safe keeps 2M band"}

    def uninstall(self) -> None:
        if self._session_cls is not None and self._original is not None:
            if self._session_cls._queue_position is not self._installed:
                raise RuntimeError("AdmissionOrderPatch: seam changed under us")
            self._session_cls._queue_position = self._original
            self._original = None
            self._installed = None


def install_admission_order() -> AdmissionOrderPatch:
    from inference.agent.priority_scheduler import PrioritySnapshot
    from inference.framework.solver import (
        _HarnessGameSession, _priority_gate, _PRIORITY_UNTRIMMED_BASE,
    )
    patch = AdmissionOrderPatch()
    original = _HarnessGameSession._queue_position
    patch._original = original
    patch._session_cls = _HarnessGameSession

    def patched_queue_position(self) -> int:
        orig_position = original(self)
        try:
            gate = _priority_gate()
            run = self.game.game_run
            total = int(run.number_of_levels) if run is not None else 0
            if gate is None or total <= 0:
                raise ValueError("no gate or total_levels")
            value = gate._snapshot_priority(
                PrioritySnapshot(level=1, actions=0, tokens=0.0,
                                 cost_multiplier=1.0, total_levels=total),
                time.monotonic())
        except Exception:
            with patch._lock:
                patch.fallbacks += 1
            return orig_position
        with patch._lock:
            patch.substitutions.append({
                "game_id": self.game.game_run.game_id,
                "game_index": self.game_index,
                "total_levels": total,
                "orig_priority": _PRIORITY_UNTRIMMED_BASE - orig_position,
                "new_priority": int(value),
            })
        return _PRIORITY_UNTRIMMED_BASE - int(value)

    _HarnessGameSession._queue_position = patched_queue_position  # type: ignore[method-assign]
    patch._installed = patched_queue_position
    if _HarnessGameSession._queue_position is original:
        raise RuntimeError("Admission order did not wrap the queue position")
    return patch
