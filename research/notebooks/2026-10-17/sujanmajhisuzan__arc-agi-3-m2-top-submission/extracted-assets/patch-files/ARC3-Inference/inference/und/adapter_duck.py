"""CONTRACT: Adapter for Duck runtime structures into UND domain objects (Rules 03, 04, 05).

Bridges Duck FrameView, action inputs, and step transition records into pure UND
data structures (FrameDTO, TransitionRecord, ActionDeclaration).
In Duck, crop_offset = 0 (exact coordinates, no artificial 1-pixel border cropping).
"""
from __future__ import annotations

import hashlib
from typing import Any, Sequence

from inference.und.actions import normalize_duck_action
from inference.und.config.platform_facts import CROP_BORDER_PIXELS
from inference.und.types import (
    ActionCategory,
    ActionDeclaration,
    FrameDTO,
    Grid2D,
    TransitionRecord,
)

# Invariant: Duck runtime operates with exact coordinates (crop_offset = 0)
CROP_OFFSET: int = CROP_BORDER_PIXELS  # 0


def extract_grid(raw_frame: Any) -> Grid2D:
    """Extract a canonical 2D integer grid (cells in 0..15) from arbitrary Duck frame data.

    Handles:
    - Duck FrameView (via .grid property or ._grid)
    - Objects with .frame or .grid attribute
    - 2D list of integers
    - 3D list/sequence (temporal batch, takes the final frame)
    - Numpy ndarray or objects with .tolist()
    """
    if raw_frame is None:
        return []

    # Duck FrameView or objects with .grid property
    if hasattr(raw_frame, "grid"):
        grid_data = raw_frame.grid
        if callable(grid_data):
            grid_data = grid_data()
        return extract_grid(grid_data)

    # Objects with ._grid attribute
    if hasattr(raw_frame, "_grid"):
        return extract_grid(raw_frame._grid)

    # Objects with .frame attribute
    if hasattr(raw_frame, "frame"):
        return extract_grid(raw_frame.frame)

    # Objects with .data attribute (e.g. Frame)
    if hasattr(raw_frame, "data"):
        return extract_grid(raw_frame.data)

    # Convert numpy ndarray
    if hasattr(raw_frame, "ndim"):
        curr = raw_frame
        while int(getattr(curr, "ndim", 0)) > 2:
            if len(curr) == 0:
                return []
            curr = curr[-1]
        if hasattr(curr, "tolist"):
            raw_frame = curr.tolist()
        else:
            raw_frame = curr

    # If it's a list/tuple of frames (depth 3 or more), pick the latest
    if isinstance(raw_frame, (list, tuple)) and len(raw_frame) > 0:
        first = raw_frame[0]
        if isinstance(first, (list, tuple)) and len(first) > 0 and isinstance(first[0], (list, tuple)):
            raw_frame = raw_frame[-1]

    if not isinstance(raw_frame, (list, tuple)):
        return []

    # Normalize to Grid2D (list[list[int]]) clamped to 0..15
    out: Grid2D = []
    for row in raw_frame:
        if hasattr(row, "tolist"):
            row = row.tolist()
        if not isinstance(row, (list, tuple)):
            continue
        int_row: list[int] = []
        for cell in row:
            try:
                val = int(cell)
                int_row.append(max(0, min(15, val)))
            except (ValueError, TypeError):
                int_row.append(0)
        out.append(int_row)

    return out


def extract_frame_dto(
    raw_frame: Any,
    step: int = 0,
    level: int = 0,
    score: int = 0,
) -> FrameDTO:
    """Build a structured FrameDTO from Duck frame representation."""
    grid = extract_grid(raw_frame)

    # Extract metadata if available on object or dict
    if isinstance(raw_frame, dict):
        if "step" in raw_frame:
            step = int(raw_frame["step"])
        if "level" in raw_frame:
            level = int(raw_frame["level"])
        if "score" in raw_frame:
            score = int(raw_frame["score"])
    else:
        if hasattr(raw_frame, "step"):
            step = int(getattr(raw_frame, "step"))
        if hasattr(raw_frame, "level"):
            level = int(getattr(raw_frame, "level"))
        elif hasattr(raw_frame, "levels_completed"):
            level = int(getattr(raw_frame, "levels_completed"))
        if hasattr(raw_frame, "score"):
            score = int(getattr(raw_frame, "score"))

    return FrameDTO(grid=grid, level=level, step=step, score=score)



def extract_animation_sequence(raw_animation_data: Any) -> list[Grid2D]:
    """Extract ordered sequence of 2D grids from Duck animation data.

    Returns non-empty list of canonical grids.
    """
    if raw_animation_data is None:
        return []

    # Sequence of frames
    if isinstance(raw_animation_data, (list, tuple)):
        frames: list[Grid2D] = []
        for item in raw_animation_data:
            g = extract_grid(item)
            if g:
                frames.append(g)
        return frames

    # Single frame or 3D numpy
    single = extract_grid(raw_animation_data)
    return [single] if single else []


def collapse_animation_chain(
    before_grid: Grid2D,
    intermediate_frames: Sequence[Grid2D],
    after_grid: Grid2D | None = None,
) -> list[Grid2D]:
    """Build a non-redundant chronological frame chain collapsing consecutive duplicates."""
    chain: list[Grid2D] = []
    if before_grid:
        chain.append(before_grid)

    for f in intermediate_frames:
        if not f:
            continue
        if not chain or f != chain[-1]:
            chain.append(f)

    if after_grid and (not chain or after_grid != chain[-1]):
        chain.append(after_grid)

    return chain


def detect_transient_cells(frame_chain: Sequence[Grid2D]) -> list[tuple[int, int, list[int]]]:
    """Detect ephemeral cells that change >= 2 times across the micro-step chain.

    These represent projectiles, raycasts, or collision flashes that revert
    or disappear before the final frame.
    Returns: list of (row, col, trajectory_of_colors).
    """
    if len(frame_chain) < 3:
        return []

    h = len(frame_chain[0])
    w = len(frame_chain[0][0]) if h > 0 else 0
    transient: list[tuple[int, int, list[int]]] = []

    for r in range(h):
        for c in range(w):
            colors: list[int] = []
            for f in frame_chain:
                if r < len(f) and c < len(f[r]):
                    val = f[r][c]
                    if not colors or val != colors[-1]:
                        colors.append(val)
            # If cell value changed >= 2 times (length >= 3), it's transient
            if len(colors) >= 3:
                transient.append((r, c, colors))

    return transient


def adapt_action(action: Any) -> ActionDeclaration:
    """Normalize Duck action representation into an ActionDeclaration."""
    if isinstance(action, ActionDeclaration):
        return action

    if isinstance(action, int):
        from inference.und.actions import from_engine_action
        action = from_engine_action(action)
    elif hasattr(action, "id"):
        from inference.und.actions import from_engine_action
        act_id = getattr(action.id, "value", action.id)
        data = getattr(action, "data", {})
        action = from_engine_action(act_id, data=data if isinstance(data, dict) else None)

    norm_dict = normalize_duck_action(action)
    action_name = norm_dict.pop("action")
    return ActionDeclaration(
        action_id=action_name,
        data=norm_dict,
        reasoning={},
    )


def adapt_transition(
    before: Any,
    action: Any,
    after: Any,
    result: dict[str, Any] | None = None,
    category: str = ActionCategory.MANUAL.value,
    index: int = 0,
) -> TransitionRecord:
    """Build a validated TransitionRecord from Duck transition inputs and outputs."""
    before_grid = extract_grid(before)
    after_grid = extract_grid(after)
    decl = adapt_action(action)
    res_dict = dict(result or {})

    # Extract level
    level = 0
    if hasattr(after, "level"):
        level = int(after.level)
    elif hasattr(after, "levels_completed"):
        level = int(after.levels_completed)
    elif hasattr(before, "level"):
        level = int(before.level)
    elif hasattr(before, "levels_completed"):
        level = int(before.levels_completed)
    elif "level" in res_dict:
        level = int(res_dict["level"])

    # Determine gameplay changed flag
    if "gameplay_changed" not in res_dict:
        res_dict["gameplay_changed"] = (before_grid != after_grid)

    return TransitionRecord(
        index=index,
        level=level,
        before_grid=before_grid,
        action=decl,
        after_grid=after_grid,
        result_flags=res_dict,
        category=category,
    )


def grid_hash(grid: Grid2D) -> str:
    """Compute deterministic SHA-256 hash of grid cells."""
    rows = ["".join(format(cell, "x") for cell in row) for row in grid]
    canonical = "\n".join(rows)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def grid_diff(before: Grid2D, after: Grid2D) -> list[tuple[int, int, int, int]]:
    """Compute cell-level differences between two grids.

    Returns list of (row, col, old_val, new_val).
    """
    diffs: list[tuple[int, int, int, int]] = []
    h = max(len(before), len(after))
    w = max(
        len(before[0]) if before else 0,
        len(after[0]) if after else 0,
    )

    for r in range(h):
        for c in range(w):
            v_before = before[r][c] if r < len(before) and c < len(before[r]) else -1
            v_after = after[r][c] if r < len(after) and c < len(after[r]) else -1
            if v_before != v_after:
                diffs.append((r, c, v_before, v_after))

    return diffs
