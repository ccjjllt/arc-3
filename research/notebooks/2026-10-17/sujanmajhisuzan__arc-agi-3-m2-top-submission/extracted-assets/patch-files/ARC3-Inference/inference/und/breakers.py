"""CONTRACT: Safety circuit breakers preventing search thrashing and budget exhaustion (Rules 01, 04, 05).

Provides deterministic trip mechanisms for:
1. BREAKER_CHECK_CALLS (6): maximum verification/check operations per level.
2. BREAKER_DIVERGED_PLANS (3): consecutive diverged plans before planning is severed.
3. MAX_REPLAN_PER_LEVEL (8): hard ceiling on in-memory pathfinding invocations.
4. COLLAPSE_NULL_STREAK (4): consecutive no-op/null transitions tripping context alert.

On trip: wm tools report 'disabled on this level, play normally' (Rule 04 В§7),
preserving knowledge base without raising exceptions or aborting gameplay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inference.und.config.thresholds import (
    BREAKER_CHECK_CALLS,
    BREAKER_DIVERGED_PLANS,
    COLLAPSE_NULL_STREAK,
    DEFAULT_THRESHOLDS,
    MAX_REPLAN_PER_LEVEL,
    ThresholdsConfig,
)
from inference.und.texts import CIRCUIT_BREAKER_TRIPPED_WARNING


@dataclass(frozen=True)
class BreakerStatus:
    """Immutable status snapshot of all circuit breakers for the active level."""

    level: int = 1
    is_tripped: bool = False
    tripped_breakers: list[str] = field(default_factory=list)
    check_calls: int = 0
    max_check_calls: int = BREAKER_CHECK_CALLS
    consecutive_diverged_plans: int = 0
    max_diverged_plans: int = BREAKER_DIVERGED_PLANS
    replan_calls: int = 0
    max_replan_calls: int = MAX_REPLAN_PER_LEVEL
    consecutive_nulls: int = 0
    max_null_streak: int = COLLAPSE_NULL_STREAK
    primary_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "is_tripped": self.is_tripped,
            "tripped_breakers": list(self.tripped_breakers),
            "check_calls": self.check_calls,
            "max_check_calls": self.max_check_calls,
            "consecutive_diverged_plans": self.consecutive_diverged_plans,
            "max_diverged_plans": self.max_diverged_plans,
            "replan_calls": self.replan_calls,
            "max_replan_calls": self.max_replan_calls,
            "consecutive_nulls": self.consecutive_nulls,
            "max_null_streak": self.max_null_streak,
            "primary_reason": self.primary_reason,
        }


class CircuitBreakerManager:
    """Monitors and trips execution circuit breakers on runaway loops or failures."""

    def __init__(self, config: ThresholdsConfig | None = None, level: int = 1) -> None:
        self.config = config or DEFAULT_THRESHOLDS
        self.level: int = level
        self.check_calls: int = 0
        self.consecutive_diverged_plans: int = 0
        self.replan_calls: int = 0
        self.consecutive_nulls: int = 0

    def on_level_start(self, new_level: int) -> None:
        """Reset level-scoped breaker counters on level rollover (Rule 04 В§4)."""
        self.level = new_level
        self.check_calls = 0
        self.consecutive_diverged_plans = 0
        self.replan_calls = 0
        self.consecutive_nulls = 0

    def record_check_call(self) -> int:
        """Increment and return verification check count."""
        self.check_calls += 1
        return self.check_calls

    def record_replan_call(self) -> int:
        """Increment and return in-memory replanning invocation count."""
        self.replan_calls += 1
        return self.replan_calls

    def record_plan_divergence(self) -> int:
        """Record a diverged plan execution (verdict MISMATCH) and increment streak."""
        self.consecutive_diverged_plans += 1
        return self.consecutive_diverged_plans

    def record_plan_match(self) -> None:
        """Reset consecutive diverged plans counter on verified plan match."""
        self.consecutive_diverged_plans = 0

    def record_transition(self, zero_delta: bool, is_null: bool = False) -> int:
        """Track consecutive idle / zero-delta / null transitions."""
        if zero_delta or is_null:
            self.consecutive_nulls += 1
        else:
            self.consecutive_nulls = 0
        return self.consecutive_nulls

    @property
    def max_check_calls(self) -> int:
        return getattr(self.config, "breaker_check_calls", BREAKER_CHECK_CALLS)

    @property
    def max_diverged_plans(self) -> int:
        return getattr(self.config, "breaker_diverged_plans", BREAKER_DIVERGED_PLANS)

    @property
    def max_replan_calls(self) -> int:
        return getattr(self.config, "max_replan_per_level", MAX_REPLAN_PER_LEVEL)

    @property
    def max_null_streak(self) -> int:
        return getattr(self.config, "collapse_null_streak", COLLAPSE_NULL_STREAK)

    @property
    def tripped_breakers(self) -> list[str]:
        """List all currently tripped circuit breakers."""
        tripped: list[str] = []
        if self.check_calls >= self.max_check_calls:
            tripped.append("check_calls")
        if self.consecutive_diverged_plans >= self.max_diverged_plans:
            tripped.append("diverged_plans")
        if self.replan_calls >= self.max_replan_calls:
            tripped.append("replan_calls")
        if self.consecutive_nulls >= self.max_null_streak:
            tripped.append("null_streak")
        return tripped

    @property
    def is_tripped(self) -> bool:
        """Return True if any circuit breaker is currently tripped."""
        return len(self.tripped_breakers) > 0

    @property
    def primary_tripped_reason(self) -> str:
        """Human-readable description of the primary tripped circuit breaker."""
        tripped = self.tripped_breakers
        if not tripped:
            return ""
        name = tripped[0]
        if name == "check_calls":
            return f"Check calls limit reached ({self.check_calls}/{self.max_check_calls})"
        if name == "diverged_plans":
            return f"Consecutive diverged plans reached ({self.consecutive_diverged_plans}/{self.max_diverged_plans})"
        if name == "replan_calls":
            return f"Replanning limit reached ({self.replan_calls}/{self.max_replan_calls})"
        if name == "null_streak":
            return f"Consecutive null/no-op streak reached ({self.consecutive_nulls}/{self.max_null_streak})"
        return f"Circuit breaker {name} tripped"

    def format_warning(self) -> str:
        """Format LLM-facing warning for diagnostic or prompt tail."""
        if not self.is_tripped:
            return ""
        tripped_name = self.tripped_breakers[0]
        curr, limit = 0, 0
        if tripped_name == "check_calls":
            curr, limit = self.check_calls, self.max_check_calls
        elif tripped_name == "diverged_plans":
            curr, limit = self.consecutive_diverged_plans, self.max_diverged_plans
        elif tripped_name == "replan_calls":
            curr, limit = self.replan_calls, self.max_replan_calls
        elif tripped_name == "null_streak":
            curr, limit = self.consecutive_nulls, self.max_null_streak

        return CIRCUIT_BREAKER_TRIPPED_WARNING.format(
            breaker_name=tripped_name,
            current=curr,
            limit=limit,
            level=self.level,
        )

    def get_status(self) -> BreakerStatus:
        """Return immutable snapshot of current breaker state."""
        return BreakerStatus(
            level=self.level,
            is_tripped=self.is_tripped,
            tripped_breakers=self.tripped_breakers,
            check_calls=self.check_calls,
            max_check_calls=self.max_check_calls,
            consecutive_diverged_plans=self.consecutive_diverged_plans,
            max_diverged_plans=self.max_diverged_plans,
            replan_calls=self.replan_calls,
            max_replan_calls=self.max_replan_calls,
            consecutive_nulls=self.consecutive_nulls,
            max_null_streak=self.max_null_streak,
            primary_reason=self.primary_tripped_reason,
        )


__all__ = [
    "BreakerStatus",
    "CircuitBreakerManager",
]
