"""CONTRACT: Immutable platform facts and competition constants for ARC-AGI-3.

All values defined here are empirical facts or competition constants (Rule 03, Section 4).
The agent does not guess or adapt these constants at runtime.
"""
from __future__ import annotations

# Grid and Palette Constants
PALETTE_COLORS_COUNT: int = 16  # 0..15 discrete colors
MIN_GRID_DIM: int = 2
MAX_GRID_DIM: int = 64

# Note: Duck runtime uses crop_offset = 0 (exact coordinates),
# unlike legacy LCLD which applied a 1-pixel artificial boundary.
CROP_BORDER_PIXELS: int = 0

# Platform Action Channels
PLATFORM_ACTIONS: tuple[str, ...] = (
    "RESET",
    "ACTION1",
    "ACTION2",
    "ACTION3",
    "ACTION4",
    "ACTION5",
    "ACTION6",
    "ACTION7",
)
DISCRETE_ACTIONS: tuple[str, ...] = (
    "ACTION1",
    "ACTION2",
    "ACTION3",
    "ACTION4",
    "ACTION5",
)
COORDINATE_ACTIONS: tuple[str, ...] = ("ACTION6",)
UNDO_ACTIONS: tuple[str, ...] = ("ACTION7",)

# Empirical ground truth: games with ACTION7 engine support (from P0.4 audit)
GAMES_WITH_UNDO: frozenset[str] = frozenset({
    "ar25",
    "bp35",
    "lf52",
    "sb26",
    "sk48",
    "su15",
})

# Role taxonomy (Rule 03, Section 3)
ENTITY_ROLES: tuple[str, ...] = (
    "BACKGROUND",
    "ACTOR",
    "OBSTACLE",
    "HAZARD",
    "TARGET",
    "COLLECTIBLE",
    "PORTAL",
    "UNKNOWN",
)

# Runtime Environment Limits
MAX_KAGGLE_SESSION_HOURS: float = 9.0
MAX_LEVEL_STEPS_CAP: int = 80
SANDBOX_TIMEOUT_S: int = 30
DEFAULT_CONTEXT_WINDOW: int = 32768
