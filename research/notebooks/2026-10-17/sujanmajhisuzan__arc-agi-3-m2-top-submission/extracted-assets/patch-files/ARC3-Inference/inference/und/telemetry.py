"""CONTRACT: Line-by-line JSONL telemetry and failure taxonomy for ARC-AGI-3 (Rules 01, 04, 05).

Provides structured event logging:
- Telemetry events streamed line-by-line in JSONL to the game artifacts directory (Rule 05 В§8 item 3).
- Zero emission to standard output of sandbox (preventing LLM context pollution).
- Detailed action consumption accounting and failure taxonomy mapping.
- Error event recording for host-side observation exceptions (Rule 05 В§4 item 1).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from inference.und.types import ActionCategory

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Failure Taxonomy & Mapping
# =============================================================================

class FailureTaxonomy(str, Enum):
    """Structured taxonomy of level and game terminations."""
    LEVEL_COMPLETED = "LEVEL_COMPLETED"
    ALL_LEVELS_COMPLETED = "ALL_LEVELS_COMPLETED"
    ACTION_CAP_LEVEL = "ACTION_CAP_LEVEL"
    ACTION_CAP_GAME = "ACTION_CAP_GAME"
    WALL_CLOCK_DEADLINE = "WALL_CLOCK_DEADLINE"
    CODER_FAILURE = "CODER_FAILURE"
    SOLVER_EXHAUSTION = "SOLVER_EXHAUSTION"
    FALLBACK_EXHAUSTION = "FALLBACK_EXHAUSTION"
    GAME_OVER_EXHAUSTED = "GAME_OVER_EXHAUSTED"
    CYCLE_DETECTED = "CYCLE_DETECTED"
    LLM_INFRA_ERROR = "LLM_INFRA_ERROR"
    PARALLEL_ABORT = "PARALLEL_ABORT"
    SUCCESS = "SUCCESS"
    UNKNOWN_TERMINATION = "UNKNOWN_TERMINATION"


def map_stop_reason_to_taxonomy(stop_reason: str) -> FailureTaxonomy:
    """Map external or solver stop reason string to canonical FailureTaxonomy."""
    sr = str(stop_reason).upper()
    if any(k in sr for k in ("WALL_CLOCK", "DEADLINE", "TIMEOUT")):
        return FailureTaxonomy.WALL_CLOCK_DEADLINE
    if "ACTIONS_PER_GAME" in sr or "ACTION_CAP_GAME" in sr:
        return FailureTaxonomy.ACTION_CAP_GAME
    if any(k in sr for k in ("ACTIONS_PER_LEVEL", "ACTION_CAP_LEVEL", "LEVEL_ACTIONS")):
        return FailureTaxonomy.ACTION_CAP_LEVEL
    if any(k in sr for k in ("RESET", "GAME_OVER")):
        return FailureTaxonomy.GAME_OVER_EXHAUSTED
    if any(k in sr for k in ("CODER", "DSL_SYNTHESIS")):
        return FailureTaxonomy.CODER_FAILURE
    if any(k in sr for k in ("SOLVER", "CANDIDATE", "CHAIN_ATTEMPTS", "LEVEL_ATTEMPTS")):
        return FailureTaxonomy.SOLVER_EXHAUSTION
    if "FALLBACK" in sr:
        return FailureTaxonomy.FALLBACK_EXHAUSTION
    if any(k in sr for k in ("CYCLE", "NOOP", "LOOP")):
        return FailureTaxonomy.CYCLE_DETECTED
    if any(k in sr for k in ("LLM", "INFRA", "API_ERROR", "RATE_LIMIT")):
        return FailureTaxonomy.LLM_INFRA_ERROR
    if "PARALLEL_ABORT" in sr or "ABORT" in sr:
        return FailureTaxonomy.PARALLEL_ABORT
    if any(k in sr for k in ("WIN", "WON", "VICTORY", "ALL_LEVELS_COMPLETED", "SUCCESS")):
        return FailureTaxonomy.SUCCESS
    return FailureTaxonomy.UNKNOWN_TERMINATION


# =============================================================================
# 2. Telemetry Events and Level Accounting
# =============================================================================

@dataclass(frozen=True)
class TelemetryEvent:
    """A single structured telemetry event serialized as one JSONL line."""
    ts: float
    game_id: str
    level: int
    step_index: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": round(self.ts, 4),
            "game_id": self.game_id,
            "level": self.level,
            "step_index": self.step_index,
            "event_type": self.event_type,
            "payload": self.payload,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class LevelActionRecord:
    """Resource consumption and termination metrics for a single level."""
    level: int
    action_counts: dict[str, int] = field(default_factory=dict)
    total_actions: int = 0
    wasted_actions: int = 0
    outcome: str = "IN_PROGRESS"
    stop_reason: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    def record_action(self, category: str) -> None:
        cat_key = str(category).lower()
        self.action_counts[cat_key] = self.action_counts.get(cat_key, 0) + 1
        self.total_actions += 1

    def record_wasted(self) -> None:
        self.wasted_actions += 1

    def finish(self, outcome: str, stop_reason: str) -> None:
        self.outcome = outcome
        self.stop_reason = stop_reason
        self.end_time = time.time()

    @property
    def duration_seconds(self) -> float:
        if self.end_time > 0:
            return max(0.0, self.end_time - self.start_time)
        return max(0.0, time.time() - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "total_actions": self.total_actions,
            "wasted_actions": self.wasted_actions,
            "action_counts": dict(self.action_counts),
            "outcome": self.outcome,
            "stop_reason": self.stop_reason,
            "duration_seconds": round(self.duration_seconds, 2),
        }


# =============================================================================
# 3. UndTelemetry Engine
# =============================================================================

class UndTelemetry:
    """Thread-safe JSONL telemetry engine writing line-by-line event traces."""

    def __init__(
        self,
        game_id: str = "",
        log_path: Path | str | None = None,
    ) -> None:
        self.game_id = game_id
        self.log_path: Path | None = Path(log_path) if log_path else None
        self._lock = threading.Lock()

        self.events: list[TelemetryEvent] = []
        self.total_action_counts: dict[str, int] = {cat.value: 0 for cat in ActionCategory}
        self.total_actions: int = 0
        self.total_wasted_actions: int = 0
        self.level_records: dict[int, LevelActionRecord] = {}
        self.game_stop_reason: str = ""
        self.game_start_time: float = time.time()
        self.game_end_time: float = 0.0

    def set_log_path(self, log_path: Path | str) -> None:
        """Configure or update the destination JSONL file path."""
        with self._lock:
            self.log_path = Path(log_path)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_level_record(self, level: int) -> LevelActionRecord:
        if level not in self.level_records:
            self.level_records[level] = LevelActionRecord(level=level)
        return self.level_records[level]

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        level: int = 0,
        step_index: int = 0,
    ) -> TelemetryEvent:
        """Append a structured event to in-memory history and write one line to JSONL."""
        evt = TelemetryEvent(
            ts=time.time(),
            game_id=self.game_id,
            level=level,
            step_index=step_index,
            event_type=event_type,
            payload=payload,
        )

        with self._lock:
            self.events.append(evt)
            if self.log_path is not None:
                try:
                    self.log_path.parent.mkdir(parents=True, exist_ok=True)
                    line = evt.to_json() + "\n"
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(line)
                except Exception as e:
                    logger.warning("Failed to append telemetry event to %s: %s", self.log_path, e)

        return evt

    def log_transition(
        self,
        level: int,
        step_index: int,
        action: str,
        category: str,
        before_hash: str,
        after_hash: str,
        result_flags: dict[str, Any] | None = None,
        zero_delta: bool = False,
    ) -> TelemetryEvent:
        """Record an observed execution transition."""
        cat_key = str(category).lower()
        rec = self._ensure_level_record(level)
        rec.record_action(cat_key)

        with self._lock:
            self.total_action_counts[cat_key] = self.total_action_counts.get(cat_key, 0) + 1
            self.total_actions += 1
            if zero_delta:
                self.total_wasted_actions += 1
                rec.record_wasted()

        payload = {
            "action": action,
            "category": cat_key,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "zero_delta": zero_delta,
            "result_flags": dict(result_flags or {}),
        }
        return self.log_event("transition", payload, level=level, step_index=step_index)

    def log_begin_step(
        self,
        level: int,
        step_index: int,
        action: str,
        category: str,
        predicted_hash: str | None = None,
    ) -> TelemetryEvent:
        """Record a pre-action simulation prediction hook call."""
        payload = {
            "action": action,
            "category": category,
            "predicted_hash": predicted_hash,
        }
        return self.log_event("begin_step", payload, level=level, step_index=step_index)

    def log_end_step(
        self,
        level: int,
        step_index: int,
        verdict: str,
        predicted_hash: str | None = None,
        actual_hash: str | None = None,
        source: str | None = None,
    ) -> TelemetryEvent:
        """Record a post-action simulation verification hook call."""
        payload = {
            "verdict": verdict,
            "predicted_hash": predicted_hash,
            "actual_hash": actual_hash,
            "source": source,
        }
        return self.log_event("end_step", payload, level=level, step_index=step_index)

    def log_level_start(
        self,
        level: int,
        step_index: int = 0,
        frame_shape: tuple[int, int] = (0, 0),
    ) -> TelemetryEvent:
        """Record level initialization."""
        self._ensure_level_record(level)
        payload = {
            "level": level,
            "frame_shape": list(frame_shape),
        }
        return self.log_event("level_start", payload, level=level, step_index=step_index)

    def log_level_finish(
        self,
        level: int,
        step_index: int,
        outcome: str = "WIN",
        stop_reason: str = "level_completed",
    ) -> TelemetryEvent:
        """Record level completion."""
        rec = self._ensure_level_record(level)
        rec.finish(outcome, stop_reason)
        payload = {
            "level": level,
            "outcome": outcome,
            "stop_reason": stop_reason,
            "total_actions": rec.total_actions,
            "duration_seconds": round(rec.duration_seconds, 2),
        }
        return self.log_event("level_finish", payload, level=level, step_index=step_index)

    def log_game_finish(
        self,
        level: int,
        step_index: int,
        reason: str | FailureTaxonomy,
    ) -> TelemetryEvent:
        tax = reason if isinstance(reason, FailureTaxonomy) else map_stop_reason_to_taxonomy(str(reason))

        if level in self.level_records and self.level_records[level].outcome == "IN_PROGRESS":
            lvl_out = "WIN" if tax in (FailureTaxonomy.SUCCESS, FailureTaxonomy.ALL_LEVELS_COMPLETED) else (
                "DEFEAT" if tax == FailureTaxonomy.GAME_OVER_EXHAUSTED else "ABORTED"
            )
            self.log_level_finish(level, step_index, outcome=lvl_out, stop_reason=tax.value)

        with self._lock:
            self.game_stop_reason = tax.value
            self.game_end_time = time.time()

        duration = max(0.0, self.game_end_time - self.game_start_time)
        payload = {
            "taxonomy": tax.value,
            "raw_reason": str(reason),
            "total_actions": self.total_actions,
            "wasted_actions": self.total_wasted_actions,
            "duration_seconds": round(duration, 2),
        }
        return self.log_event("game_finish", payload, level=level, step_index=step_index)

    def log_error(
        self,
        level: int,
        step_index: int,
        error_message: str,
        error_type: str = "Exception",
        details: dict[str, Any] | None = None,
    ) -> TelemetryEvent:
        """Record a non-fatal observation error for diagnostics (Rule 05 В§4 item 1)."""
        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "details": dict(details or {}),
        }
        return self.log_event("error", payload, level=level, step_index=step_index)

    def get_summary(self) -> dict[str, Any]:
        """Return structured summary for diagnostic reporting."""
        duration = max(0.0, (self.game_end_time or time.time()) - self.game_start_time)
        with self._lock:
            return {
                "game_id": self.game_id,
                "total_actions": self.total_actions,
                "total_wasted_actions": self.total_wasted_actions,
                "total_action_counts": dict(self.total_action_counts),
                "game_stop_reason": self.game_stop_reason,
                "game_duration_seconds": round(duration, 2),
                "levels": {lvl: rec.to_dict() for lvl, rec in self.level_records.items()},
                "events_count": len(self.events),
            }

    def format_markdown_report(self) -> str:
        """Format an action consumption markdown table for transcript diagnostics."""
        with self._lock:
            lines = [
                "### Action Consumption & Telemetry Summary",
                "",
                f"**Game:** `{self.game_id}` | **Total Actions:** {self.total_actions} | "
                f"**Wasted (Idle):** {self.total_wasted_actions} | **Stop Reason:** `{self.game_stop_reason or 'RUNNING'}`",
                "",
                "| Level | Total | Manual | Probe | Explore | Exec OK | Exec Fail | Wasted | Outcome |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for lvl, rec in sorted(self.level_records.items()):
                c = rec.action_counts
                lines.append(
                    f"| {lvl} | {rec.total_actions} | {c.get('manual', 0)} | {c.get('probe', 0)} | "
                    f"{c.get('explore', 0)} | {c.get('exec_ok', 0)} | {c.get('exec_failed', 0)} | "
                    f"{rec.wasted_actions} | `{rec.outcome}` |"
                )
            lines.append("")
            return "\n".join(lines)
