"""CONTRACT: HUD timer detection, remaining step estimation, and probe budget gating (Rules 01, 04, 05).

Provides deterministic tracking of peripheral timer and step-counter progress bars.
Enforces TIMER_PROBE_FRACTION (0.25) to protect against game loss on step-limited games.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from inference.und.config.thresholds import DEFAULT_THRESHOLDS, ThresholdsConfig
from inference.und.perception.arga_lite import (
    extract_arga_snapshot,
    is_hud_progress_bar_mutation,
    is_peripheral_hud_strip,
)
from inference.und.types import Grid2D


class TimerType(str, Enum):
    """Classification of detected game countdown mechanisms."""

    NONE = "none"
    HUD_PROGRESS_BAR = "hud_progress_bar"
    HUD_STEP_COUNTER = "hud_step_counter"
    STEP_LIMIT = "step_limit"


@dataclass(frozen=True)
class TimerStatus:
    """Snapshot of current timer / step limit status for the active level."""

    has_timer: bool = False
    timer_type: TimerType = TimerType.NONE
    estimated_remaining_steps: int | None = None
    initial_steps_estimated: int | None = None
    steps_observed: int = 0
    burn_rate: float = 1.0
    probe_budget_remaining: int = 0
    is_critical: bool = False
    probes_used: int = 0
    probe_budget_total: int = 0
    probing_allowed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_timer": self.has_timer,
            "timer_type": self.timer_type.value,
            "estimated_remaining_steps": self.estimated_remaining_steps,
            "initial_steps_estimated": self.initial_steps_estimated,
            "steps_observed": self.steps_observed,
            "burn_rate": round(self.burn_rate, 2),
            "probe_budget_remaining": self.probe_budget_remaining,
            "is_critical": self.is_critical,
            "probes_used": self.probes_used,
            "probe_budget_total": self.probe_budget_total,
            "probing_allowed": self.probing_allowed,
        }


@dataclass(frozen=True)
class BudgetStatus:
    """Snapshot of action and probe exploration budgets for the active level (Rule 01 В§4, Rule 04 В§7)."""

    level: int = 1
    probe_budget_total: int = 12
    probes_used: int = 0
    probe_budget_remaining: int = 12
    probing_allowed: bool = True
    reason: str = "Probe allowed"
    timer_present: bool = False
    steps_remaining: int | None = None
    is_critical: bool = False
    burn_rate: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "probe_budget_total": self.probe_budget_total,
            "probes_used": self.probes_used,
            "probe_budget_remaining": self.probe_budget_remaining,
            "probing_allowed": self.probing_allowed,
            "reason": self.reason,
            "timer_present": self.timer_present,
            "steps_remaining": self.steps_remaining,
            "is_critical": self.is_critical,
            "burn_rate": round(self.burn_rate, 2),
        }


def detect_hud_bar_step_count(
    before_grid: Grid2D,
    after_grid: Grid2D,
) -> tuple[bool, int | None, int | None]:
    """Inspect peripheral HUD mutations between frames to detect progress bar steps.

    Returns: (is_timer_bar, remaining_steps_after, delta_steps_burned).
    """
    if not before_grid or not after_grid or not before_grid[0] or not after_grid[0]:
        return False, None, None

    h = min(len(before_grid), len(after_grid))
    w = min(len(before_grid[0]), len(after_grid[0]))
    grid_dims = (h, w)

    b_snap = extract_arga_snapshot(before_grid)
    a_snap = extract_arga_snapshot(after_grid)

    for b_o in b_snap.objects:
        if not is_peripheral_hud_strip(b_o, grid_dims):
            continue
        for a_o in a_snap.objects:
            if is_hud_progress_bar_mutation(b_o, a_o, grid_dims):
                delta_cells = b_o.area - a_o.area
                if delta_cells > 0:
                    # Bar is shrinking -> countdown in progress
                    # Remaining bar length/area corresponds directly to remaining steps
                    remaining = a_o.area
                    return True, remaining, delta_cells

    return False, None, None


class TimerTracker:
    """Maintains active timer telemetry, estimates remaining actions, and gates probe budgets."""

    def __init__(self, config: ThresholdsConfig | None = None) -> None:
        self.config = config or DEFAULT_THRESHOLDS
        self.has_timer: bool = False
        self.timer_type: TimerType = TimerType.NONE
        self.estimated_remaining: int | None = None
        self.initial_steps: int | None = None
        self.steps_observed: int = 0
        self.total_delta_burned: int = 0
        self.burn_rate: float = 1.0

    def reset(self) -> None:
        """Reset timer state for a new level or game restart."""
        self.has_timer = False
        self.timer_type = TimerType.NONE
        self.estimated_remaining = None
        self.initial_steps = None
        self.steps_observed = 0
        self.total_delta_burned = 0
        self.burn_rate = 1.0

    def observe_transition(
        self,
        before_grid: Grid2D,
        after_grid: Grid2D,
    ) -> TimerStatus:
        """Update timer state following an observed state transition."""
        self.steps_observed += 1

        is_bar, rem, delta = detect_hud_bar_step_count(before_grid, after_grid)
        if is_bar and rem is not None:
            self.has_timer = True
            self.timer_type = TimerType.HUD_PROGRESS_BAR
            self.estimated_remaining = rem
            if self.initial_steps is None and delta is not None:
                self.initial_steps = rem + delta
            if delta is not None and delta > 0:
                self.total_delta_burned += delta
                self.burn_rate = self.total_delta_burned / max(1, self.steps_observed)
        elif self.has_timer and self.estimated_remaining is not None:
            # If timer was previously detected, decrement by burn_rate on regular step
            self.estimated_remaining = max(0, int(self.estimated_remaining - self.burn_rate))

        return self.status(level=1)

    @property
    def steps_remaining(self) -> int | None:
        """Convenience property for estimated remaining countdown steps."""
        return self.estimated_remaining

    @property
    def is_critical(self) -> bool:
        """Check if countdown timer is in critical regime (<= 4 steps)."""
        return bool(
            self.has_timer
            and self.config.arc3_und_timer
            and self.estimated_remaining is not None
            and self.estimated_remaining <= 4
        )

    def compute_probe_budget(self, level: int = 1) -> int:
        """Calculate maximum allowable exploratory probes given timer constraints."""
        max_base = (
            self.config.probe_budget_level1
            if level <= 1
            else self.config.probe_budget_level_n
        )
        max_base = min(max_base, self.config.max_explorer_probes_per_level)
        if not self.config.arc3_und_timer or not self.has_timer or self.estimated_remaining is None:
            return max_base

        # Rule 01, В§4: TIMER_PROBE_FRACTION (0.25)
        fractional_budget = int(self.estimated_remaining * self.config.timer_probe_fraction)
        return max(0, min(max_base, fractional_budget))

    def evaluate_probing(self, probes_used: int = 0, level: int = 1) -> tuple[bool, str]:
        """Evaluate probe suppression status and detailed rationale (Rule 01 В§4, Rule 04 В§7).

        Returns: (is_suppressed: bool, reason: str).
        """
        if (
            self.config.arc3_und_timer
            and self.has_timer
            and self.estimated_remaining is not None
            and self.estimated_remaining <= 4
        ):
            return True, f"Critical timer pressure ({self.estimated_remaining} steps remaining <= 4): probing suppressed to conserve moves"

        total_budget = self.compute_probe_budget(level)
        if probes_used >= total_budget:
            return True, f"Probe budget exhausted ({probes_used}/{total_budget} probes used on level {level})"

        remaining = max(0, total_budget - probes_used)
        return False, f"Probe allowed ({remaining} probe(s) remaining on level {level})"

    def should_suppress_probing(self, probes_used: int, level: int = 1) -> bool:
        """Determine if exploratory probes should be suppressed to conserve step ceiling."""
        suppressed, _ = self.evaluate_probing(probes_used, level)
        return suppressed

    def status(self, level: int = 1, probes_used: int = 0) -> TimerStatus:
        """Return current immutable TimerStatus."""
        total_budget = self.compute_probe_budget(level)
        is_crit = self.is_critical
        remaining = 0 if is_crit else max(0, total_budget - probes_used)
        suppressed, _ = self.evaluate_probing(probes_used, level)
        return TimerStatus(
            has_timer=self.has_timer,
            timer_type=self.timer_type,
            estimated_remaining_steps=self.estimated_remaining,
            initial_steps_estimated=self.initial_steps,
            steps_observed=self.steps_observed,
            burn_rate=self.burn_rate,
            probe_budget_remaining=remaining,
            is_critical=is_crit,
            probes_used=probes_used,
            probe_budget_total=total_budget,
            probing_allowed=not suppressed,
        )

    def budget_status(self, level: int = 1, probes_used: int = 0) -> BudgetStatus:
        """Return complete exploration budget status for level."""
        t_stat = self.status(level, probes_used=probes_used)
        _, reason = self.evaluate_probing(probes_used, level)
        return BudgetStatus(
            level=level,
            probe_budget_total=t_stat.probe_budget_total,
            probes_used=probes_used,
            probe_budget_remaining=t_stat.probe_budget_remaining,
            probing_allowed=t_stat.probing_allowed,
            reason=reason,
            timer_present=t_stat.has_timer,
            steps_remaining=t_stat.estimated_remaining_steps,
            is_critical=t_stat.is_critical,
            burn_rate=t_stat.burn_rate,
        )


class ExplorationPolicy:
    """Exploration policy gating exploratory probes and step budgets (Rules 01, 04, 07)."""

    def __init__(
        self,
        config: ThresholdsConfig | None = None,
        timer: TimerTracker | None = None,
    ) -> None:
        self.config = config or DEFAULT_THRESHOLDS
        self.timer = timer or TimerTracker(self.config)

    def can_probe(self, probes_used: int, level: int = 1) -> tuple[bool, str]:
        """Check if exploratory probing is currently allowed by the exploration policy."""
        suppressed, reason = self.timer.evaluate_probing(probes_used, level=level)
        return not suppressed, reason

    def get_budget(self, probes_used: int, level: int = 1) -> BudgetStatus:
        """Return complete exploration and action budget status for level."""
        return self.timer.budget_status(level=level, probes_used=probes_used)


__all__ = [
    "BudgetStatus",
    "ExplorationPolicy",
    "TimerStatus",
    "TimerTracker",
    "TimerType",
    "detect_hud_bar_step_count",
]
