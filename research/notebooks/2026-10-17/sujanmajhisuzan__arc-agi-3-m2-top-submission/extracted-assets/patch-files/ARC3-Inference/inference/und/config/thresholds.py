"""CONTRACT: Unified thresholds configuration for ARC-AGI-3 Hybrid Agent (Rules 01, 04, 05).

All numeric thresholds, feature flags, evidence quotas, and resource budgets
must be defined here. Logic modules are strictly forbidden from hardcoding numbers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# 1. Brusentsov ClaimGraph Truth Thresholds (Rule 02, Section 3)
# =============================================================================

DEFAULT_N_DIRECT: dict[str, int] = {
    "action_effect": 2,
    "controlled": 2,
    "passability": 2,
    "lethal": 1,
    "collectible": 1,
    "trigger": 2,
    "click_effect": 2,
    "undo_exact": 2,
}

DEFAULT_N_LEVELS: dict[str, int] = {
    "action_effect": 1,
    "controlled": 1,
    "passability": 1,
    "lethal": 1,
    "collectible": 1,
    "trigger": 1,
    "click_effect": 1,
    "undo_exact": 1,
}

DEFAULT_N_MINUS: int = 2  # Counterexamples needed to refute an unconfirmed claim


# =============================================================================
# 2. Limits, Budgets, and Convergence Thresholds
# =============================================================================

UNDO_MAX_DEPTH: int = 5
UNDO_PROBE_MAX_PER_LEVEL: int = 1
MAX_REPLAN_PER_LEVEL: int = 8
MAX_EXPLORER_PROBES_PER_LEVEL: int = 16
MAX_CHAIN_ATTEMPTS_PER_LEVEL: int = 5
CONVERGENCE_K: int = 3
PREDICTED_TRANSITIONS_CONVERGENCE_K: int = CONVERGENCE_K
CODER_CONTAINER_MAX_ELEMENTS: int = 64
PLAN_MAX_STATES: int = 4000
ENABLE_CORE_MODEL_SIMULATION: bool = True
ENABLE_OBSERVED_EDGES_OVERLAY: bool = True
ENABLE_SYMBOLIC_UNDO: bool = True

# Perception and tracking thresholds (Rule 01, Section 4; Rule 04)
TRACK_MIN_AREA: int = 1
TRACK_MATCH_THRESHOLD: float = 0.45
TRACK_MAX_AGE: int = 5
OCCLUSION_RADIUS: int = 3
CUMULATIVE_WINDOW: int = 3
MATCHING_AMBIGUITY_THRESHOLD: float = 0.15

# Timer and probe budgets (Rule 01, Section 4)
TIMER_PROBE_FRACTION: float = 0.25
PROBE_BUDGET_LEVEL1: int = 12
PROBE_BUDGET_LEVEL_N: int = 4

# Context and RPC limits (Rule 05)
DIGEST_MAX_TOKENS: int = 800
CARD_MAX_TOKENS: int = 600
DIAG_MAX_LINES: int = 25
RPC_REPLY_MAX_BYTES: int = 32768
SANDBOX_CALL_DEADLINE_S: float = 25.0
PLAN_TIME_BUDGET_S: float = 4.0
COLLAPSE_NULL_STREAK: int = 4
SHADOW_WINDOW_STEPS: int = 5
STATE_JSON_MAX_BYTES: int = 65536
BREAKER_CHECK_CALLS: int = 6
BREAKER_DIVERGED_PLANS: int = 3


# =============================================================================
# 3. Dynamic Thresholds Container & Feature Flags (Rule 01, Section 4; Rule 05)
# =============================================================================

@dataclass
class ThresholdsConfig:
    """Configurable thresholds instance reading defaults from module constants or environment."""

    # Logic quotas
    n_direct: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_N_DIRECT))
    n_levels: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_N_LEVELS))
    n_minus: int = DEFAULT_N_MINUS

    # Budgets & depths
    undo_max_depth: int = UNDO_MAX_DEPTH
    undo_probe_max_per_level: int = UNDO_PROBE_MAX_PER_LEVEL
    max_replan_per_level: int = MAX_REPLAN_PER_LEVEL
    max_explorer_probes_per_level: int = MAX_EXPLORER_PROBES_PER_LEVEL
    max_chain_attempts_per_level: int = MAX_CHAIN_ATTEMPTS_PER_LEVEL
    convergence_k: int = CONVERGENCE_K
    coder_container_max_elements: int = CODER_CONTAINER_MAX_ELEMENTS
    plan_max_states: int = PLAN_MAX_STATES
    breaker_check_calls: int = BREAKER_CHECK_CALLS
    breaker_diverged_plans: int = BREAKER_DIVERGED_PLANS

    # Perception & tracking
    track_min_area: int = TRACK_MIN_AREA
    track_match_threshold: float = TRACK_MATCH_THRESHOLD
    track_max_age: int = TRACK_MAX_AGE
    occlusion_radius: int = OCCLUSION_RADIUS
    cumulative_window: int = CUMULATIVE_WINDOW
    matching_ambiguity_threshold: float = MATCHING_AMBIGUITY_THRESHOLD

    # Timer & exploration budget
    timer_probe_fraction: float = TIMER_PROBE_FRACTION
    probe_budget_level1: int = PROBE_BUDGET_LEVEL1
    probe_budget_level_n: int = PROBE_BUDGET_LEVEL_N

    # RPC & context bounds
    digest_max_tokens: int = DIGEST_MAX_TOKENS
    card_max_tokens: int = CARD_MAX_TOKENS
    diag_max_lines: int = DIAG_MAX_LINES
    rpc_reply_max_bytes: int = RPC_REPLY_MAX_BYTES
    sandbox_call_deadline_s: float = SANDBOX_CALL_DEADLINE_S
    plan_time_budget_s: float = PLAN_TIME_BUDGET_S
    collapse_null_streak: int = COLLAPSE_NULL_STREAK
    shadow_window_steps: int = SHADOW_WINDOW_STEPS
    state_json_max_bytes: int = STATE_JSON_MAX_BYTES

    # Feature flags (disabled by default per Rule 05, В§2, В§9)
    arc3_und: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND", "0") in ("1", "true", "True")
    )
    arc3_und_observe: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_OBSERVE", "0") in ("1", "true", "True")
    )
    arc3_und_tools: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_TOOLS", "0") in ("1", "true", "True")
    )
    arc3_und_collapse: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_COLLAPSE", "0") in ("1", "true", "True")
    )
    arc3_und_undo: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_UNDO", "0") in ("1", "true", "True")
    )
    arc3_und_timer: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_TIMER", "0") in ("1", "true", "True")
    )
    arc3_und_hooks: bool = field(
        default_factory=lambda: os.getenv("ARC3_UND_HOOKS", "0") in ("1", "true", "True")
    )
    expose_undo: bool = field(
        default_factory=lambda: os.getenv("EXPOSE_UNDO", "off").lower() in ("on", "1", "true")
    )

    def resolve(self, key: str, default: Any = None) -> Any:
        """Resolve a configuration parameter by key with fallback default."""
        return getattr(self, key, default)


# Singleton default configuration
DEFAULT_THRESHOLDS = ThresholdsConfig()

