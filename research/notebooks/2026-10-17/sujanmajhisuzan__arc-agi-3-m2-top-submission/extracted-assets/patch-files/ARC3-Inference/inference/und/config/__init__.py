"""Configuration package for ARC-AGI-3 Hybrid UND Agent.

Exports normative platform facts and configurable thresholds.
"""
from __future__ import annotations

from inference.und.config.platform_facts import (
    CROP_BORDER_PIXELS,
    DEFAULT_CONTEXT_WINDOW,
    DISCRETE_ACTIONS,
    ENTITY_ROLES,
    GAMES_WITH_UNDO,
    MAX_GRID_DIM,
    MIN_GRID_DIM,
    PALETTE_COLORS_COUNT,
    PLATFORM_ACTIONS,
    SANDBOX_TIMEOUT_S,
    UNDO_ACTIONS,
)
from inference.und.config.thresholds import (
    DEFAULT_THRESHOLDS,
    ThresholdsConfig,
)

__all__ = [
    "CROP_BORDER_PIXELS",
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_THRESHOLDS",
    "DISCRETE_ACTIONS",
    "ENTITY_ROLES",
    "GAMES_WITH_UNDO",
    "MAX_GRID_DIM",
    "MIN_GRID_DIM",
    "PALETTE_COLORS_COUNT",
    "PLATFORM_ACTIONS",
    "SANDBOX_TIMEOUT_S",
    "ThresholdsConfig",
    "UNDO_ACTIONS",
]
