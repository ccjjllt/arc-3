"""CONTRACT: Pure and empirical UNDO primitives for ARC-AGI-3 Hybrid Agent (Rules 01, 03, 04, 05).

Provides:
- UndoProfile: Grounded game capability tracking (available, board_restored, depth, empty_history).
- probe: Empirical single-step probe on level 1 to verify board restoration.
- determinism_check: Verified transition determinism testing via action-undo-reexecute cycle.
- recover: Backward state recovery chain up to UNDO_MAX_DEPTH.
- Routing cost model integration when EXPOSE_UNDO=on and ARC3_UND_UNDO enabled.
- INVARIANT: UNDO never appears in SimulationPlanner or wm.plan search paths.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from inference.und.actions import UNDO_ACTION_ID, is_undo_supported
from inference.und.adapter_duck import grid_hash
from inference.und.config.thresholds import UNDO_MAX_DEPTH, UNDO_PROBE_MAX_PER_LEVEL
from inference.und.core_model import RouteCandidate
from inference.und.types import ActionCategory, ActionDeclaration, Grid2D, TransitionRecord

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Undo Profile (Rule 03 В§1 item 6)
# =============================================================================

@dataclass
class UndoProfile:
    """Grounded profile of UNDO capabilities for the current game session."""

    game_id: str = ""
    available: bool = False
    board_restored: bool = False
    depth: int = UNDO_MAX_DEPTH
    empty_history: str = "noop"
    verified_at: int | None = None
    step_cost: int = 1
    affects_timer: bool = True
    probes_used_on_level: int = 0
    max_probes_per_level: int = UNDO_PROBE_MAX_PER_LEVEL

    def can_probe(self) -> bool:
        """Check whether an empirical probe is permitted on current level."""
        return bool(self.available and not self.board_restored and self.probes_used_on_level < self.max_probes_per_level)

    def can_route(self) -> bool:
        """Check whether UNDO can be used in routing and recovery."""
        return bool(self.available and self.board_restored)

    def record_probe(self, board_restored: bool, step_index: int) -> None:
        """Record outcome of an empirical probe."""
        self.probes_used_on_level += 1
        self.board_restored = board_restored
        if board_restored:
            self.verified_at = step_index
        else:
            self.available = False  # Rule 03 В§1 item 6: disabled if board_restored is false

    def on_level_start(self, new_level: int) -> None:
        """Handle level transition: reset per-level probe quota while preserving verified status."""
        self.probes_used_on_level = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id, "available": self.available, "board_restored": self.board_restored,
            "depth": self.depth, "empty_history": self.empty_history, "verified_at": self.verified_at,
            "step_cost": self.step_cost, "affects_timer": self.affects_timer,
            "probes_used_on_level": self.probes_used_on_level, "max_probes_per_level": self.max_probes_per_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UndoProfile:
        return cls(
            game_id=data.get("game_id", ""), available=bool(data.get("available", False)),
            board_restored=bool(data.get("board_restored", False)), depth=int(data.get("depth", UNDO_MAX_DEPTH)),
            empty_history=str(data.get("empty_history", "noop")), verified_at=data.get("verified_at"),
            step_cost=int(data.get("step_cost", 1)), affects_timer=bool(data.get("affects_timer", True)),
            probes_used_on_level=int(data.get("probes_used_on_level", 0)),
            max_probes_per_level=int(data.get("max_probes_per_level", UNDO_PROBE_MAX_PER_LEVEL)),
        )


def create_undo_profile(game_id: str, expose_undo: bool = False, max_depth: int = UNDO_MAX_DEPTH) -> UndoProfile:
    """Factory creating an initial UndoProfile for the given game."""
    if not is_undo_supported(game_id, expose_undo=expose_undo):
        return UndoProfile(game_id=game_id, available=False, board_restored=False, depth=0, empty_history="unavailable")
    return UndoProfile(game_id=game_id, available=True, board_restored=False, depth=max_depth, empty_history="noop")


# =============================================================================
# 2. Probe Primitives (Rule 03 В§1 item 6)
# =============================================================================

@dataclass(frozen=True)
class UndoProbeResult:
    """Result of an empirical single-step UNDO probe."""
    success: bool
    board_restored: bool
    action: str = UNDO_ACTION_ID
    step_index: int = 0
    detail: str = ""


def evaluate_undo_transition(
    undo_after_grid: Grid2D, expected_grid: Grid2D, profile: UndoProfile, step_index: int = 0,
) -> UndoProbeResult:
    """Evaluate whether an observed UNDO transition restored the expected grid."""
    restored = (undo_after_grid == expected_grid)
    profile.record_probe(board_restored=restored, step_index=step_index)
    detail = "Board restored perfectly" if restored else "Board restoration mismatch"
    return UndoProbeResult(success=True, board_restored=restored, action=UNDO_ACTION_ID, step_index=step_index, detail=detail)


def execute_undo_probe(
    env_runner: Callable[[str, str], tuple[Grid2D, dict[str, Any]]],
    current_grid: Grid2D, expected_grid: Grid2D, profile: UndoProfile, step_index: int = 0,
) -> UndoProbeResult:
    """Execute an empirical single-step UNDO probe in the environment."""
    if not profile.can_probe():
        raise RuntimeError(f"Probe budget exceeded or UNDO unavailable on level (used={profile.probes_used_on_level}, max={profile.max_probes_per_level})")
    after_grid, _ = env_runner(UNDO_ACTION_ID, ActionCategory.UNDO.value)
    return evaluate_undo_transition(after_grid, expected_grid, profile, step_index)


# =============================================================================
# 3. Determinism Check (Rule 04 В§1, ActionCategory.DETERMINISM)
# =============================================================================

@dataclass(frozen=True)
class DeterminismCheckResult:
    """Outcome of testing transition determinism via UNDO and re-execution."""
    is_deterministic: bool
    action: str
    before_hash: str
    first_after_hash: str
    second_after_hash: str
    undone_successfully: bool
    steps_spent: int
    detail: str = ""


def check_transition_determinism(first_tr: TransitionRecord, second_tr: TransitionRecord) -> DeterminismCheckResult:
    """Compare two observed transitions offline for deterministic identity."""
    b1_h, b2_h = grid_hash(first_tr.before_grid), grid_hash(second_tr.before_grid)
    a1_h, a2_h = grid_hash(first_tr.after_grid), grid_hash(second_tr.after_grid)
    det = (first_tr.action.action_id == second_tr.action.action_id) and (b1_h == b2_h) and (a1_h == a2_h)
    return DeterminismCheckResult(
        is_deterministic=det, action=first_tr.action.action_id, before_hash=b1_h,
        first_after_hash=a1_h, second_after_hash=a2_h, undone_successfully=(b1_h == b2_h),
        steps_spent=0, detail="Deterministic" if det else "Non-deterministic or input mismatch",
    )


def determinism_check(
    env_runner: Callable[[str, str], tuple[Grid2D, dict[str, Any]]],
    current_grid: Grid2D, initial_grid: Grid2D, action: str | ActionDeclaration, profile: UndoProfile,
) -> DeterminismCheckResult:
    """Empirically verify transition determinism by undoing and re-executing action."""
    act_id = action.action_id if isinstance(action, ActionDeclaration) else str(action)
    b_hash, a1_hash = grid_hash(initial_grid), grid_hash(current_grid)
    if not profile.can_route():
        return DeterminismCheckResult(
            is_deterministic=False, action=act_id, before_hash=b_hash, first_after_hash=a1_hash,
            second_after_hash="", undone_successfully=False, steps_spent=0, detail="UNDO not verified or unavailable",
        )
    undone_grid, _ = env_runner(UNDO_ACTION_ID, ActionCategory.UNDO.value)
    if grid_hash(undone_grid) != b_hash:
        return DeterminismCheckResult(
            is_deterministic=False, action=act_id, before_hash=b_hash, first_after_hash=a1_hash,
            second_after_hash="", undone_successfully=False, steps_spent=1, detail="UNDO failed to revert to initial state",
        )
    re_grid, _ = env_runner(act_id, ActionCategory.DETERMINISM.value)
    a2_hash = grid_hash(re_grid)
    det = (a1_hash == a2_hash)
    return DeterminismCheckResult(
        is_deterministic=det, action=act_id, before_hash=b_hash, first_after_hash=a1_hash,
        second_after_hash=a2_hash, undone_successfully=True, steps_spent=2,
        detail="Transition deterministic" if det else "Transition non-deterministic",
    )


# =============================================================================
# 4. Recovery Chain Primitives (Rule 04 В§4)
# =============================================================================

@dataclass(frozen=True)
class RecoveryResult:
    """Outcome of attempting to recover a past state via an UNDO chain."""
    success: bool
    target_reached: bool
    steps_executed: int
    actions: tuple[str, ...]
    final_hash: str
    detail: str = ""


def plan_recovery_chain(
    current_hash: str, target_hash: str, history_hashes: Sequence[str], profile: UndoProfile,
) -> RouteCandidate | None:
    """Plan an UNDO recovery chain to target_hash within profile depth."""
    if not profile.can_route():
        return None
    if current_hash == target_hash:
        return RouteCandidate(route_type="undo", cost=0, actions=())
    hist = list(history_hashes)
    if hist and hist[-1] == current_hash:
        hist.pop()
    for k, past_h in enumerate(reversed(hist[-profile.depth:]), start=1):
        if past_h == target_hash:
            return RouteCandidate(route_type="undo", cost=k, actions=tuple(UNDO_ACTION_ID for _ in range(k)))
    return None


def execute_recovery(
    env_runner: Callable[[str, str], tuple[Grid2D, dict[str, Any]]],
    current_hash: str, target_hash: str, history_hashes: Sequence[str], profile: UndoProfile,
) -> RecoveryResult:
    """Execute a planned UNDO recovery chain."""
    route = plan_recovery_chain(current_hash, target_hash, history_hashes, profile)
    if not route or not route.actions:
        return RecoveryResult(
            success=False, target_reached=False, steps_executed=0, actions=(),
            final_hash=current_hash, detail="No recovery route found within depth",
        )
    curr_h, steps = current_hash, 0
    for act in route.actions:
        new_grid, _ = env_runner(act, ActionCategory.RECOVER.value)
        curr_h = grid_hash(new_grid)
        steps += 1
        if curr_h == target_hash:
            break
    reached = (curr_h == target_hash)
    return RecoveryResult(
        success=reached, target_reached=reached, steps_executed=steps, actions=route.actions[:steps],
        final_hash=curr_h, detail="Target reached" if reached else "Recovery interrupted",
    )


def is_undo_routing_eligible(profile: UndoProfile, arc3_und_undo: bool = True) -> bool:
    """Global check for whether symbolic UNDO routing may be considered in cost model."""
    return bool(arc3_und_undo and profile.can_route())
