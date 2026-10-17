"""Animation awareness and transient cell detection for ARC-AGI-3 environments (Rules 01, 04).

Extracts micro-step animation frames returned by arcengine/Arcade.
Identifies transient cells (cells changing value >= 2 times across the action chain)
which carry ephemeral game mechanics (projectiles, lasers, raycasts, interaction flashes)
that vanish before or revert in the final static frame.

Adheres strictly to Anti-Specification Gaming rules:
- Zero hardcoded game identifiers.
- Scale-invariant across grid sizes (2x2 to 64x64).
- Palette-invariant across 16 ARC-AGI-3 colors (0..15).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from inference.und.types import Grid2D


def normalize_single_grid(raw_grid: Any) -> Grid2D:
    """Normalize a raw 2D array, tuple, or list into canonical Grid2D (0..15 integers)."""
    if raw_grid is None:
        return []
    if hasattr(raw_grid, "tolist"):
        raw_grid = raw_grid.tolist()
    if not isinstance(raw_grid, (list, tuple)):
        return []

    norm: Grid2D = []
    for row in raw_grid:
        if hasattr(row, "tolist"):
            row = row.tolist()
        if not isinstance(row, (list, tuple)):
            continue
        int_row: list[int] = []
        for cell in row:
            try:
                v = int(cell)
                int_row.append(max(0, min(15, v)))
            except (ValueError, TypeError):
                int_row.append(0)
        norm.append(int_row)
    return norm


def extract_raw_frame_sequence(raw_frame_data: Any) -> list[Grid2D]:
    """Extract ordered list of 2D grids from raw FrameData.frame or sequence."""
    if raw_frame_data is None:
        return []

    if hasattr(raw_frame_data, "ndim"):
        ndim = int(getattr(raw_frame_data, "ndim", 0))
        if ndim == 3:
            return [normalize_single_grid(raw_frame_data[t]) for t in range(len(raw_frame_data))]
        if ndim == 2:
            return [normalize_single_grid(raw_frame_data)]

    if isinstance(raw_frame_data, (list, tuple)):
        if not raw_frame_data:
            return []
        first = raw_frame_data[0]
        if hasattr(first, "ndim") and int(getattr(first, "ndim", 0)) == 2:
            return [normalize_single_grid(f) for f in raw_frame_data]
        if isinstance(first, (list, tuple)) and len(first) > 0 and isinstance(first[0], (list, tuple)):
            if len(first[0]) > 0 and isinstance(first[0][0], (int, float)):
                return [normalize_single_grid(f) for f in raw_frame_data]
        return [normalize_single_grid(raw_frame_data)]

    return [normalize_single_grid(raw_frame_data)]


def collapse_animation_chain(before_grid: Grid2D | None, frames: Sequence[Grid2D]) -> list[Grid2D]:
    """Prepend pre-action grid and collapse consecutive duplicate frames."""
    chain: list[Grid2D] = []
    if before_grid:
        chain.append(before_grid)
    for f in frames:
        if not f:
            continue
        if chain and chain[-1] == f:
            continue
        chain.append(f)
    return chain


def extract_transient_cells(
    chain: Sequence[Grid2D],
    ignore_peripheral_hud: bool = True,
) -> list[tuple[int, int]]:
    """Return coordinates of cells that change two or more times across the chain."""
    if len(chain) <= 1:
        return []

    changes: defaultdict[tuple[int, int], int] = defaultdict(int)
    for prev_grid, next_grid in zip(chain, chain[1:]):
        h = max(len(prev_grid), len(next_grid))
        for r in range(h):
            row_p = prev_grid[r] if r < len(prev_grid) else ()
            row_n = next_grid[r] if r < len(next_grid) else ()
            w = max(len(row_p), len(row_n))
            for c in range(w):
                v_p = row_p[c] if c < len(row_p) else None
                v_n = row_n[c] if c < len(row_n) else None
                if v_p != v_n:
                    changes[(r, c)] += 1

    transient = [cell for cell, count in changes.items() if count >= 2]
    if not transient:
        return []

    if ignore_peripheral_hud and chain:
        first_grid = chain[0]
        h = len(first_grid)
        w = len(first_grid[0]) if h > 0 else 0
        if h >= 6 and w >= 6:
            limit_thick = min(3, max(1, min(h, w) // 6))
            all_peripheral = all(
                (r < limit_thick or r >= h - limit_thick or c < limit_thick or c >= w - limit_thick)
                for r, c in transient
            )
            if all_peripheral:
                return []

    return sorted(transient)


def analyze_animation_trajectory(
    chain: Sequence[Grid2D],
    transient_cells: list[tuple[int, int]] | None = None,
    max_timeline_steps: int = 15,
    max_cells_per_step: int = 24,
) -> dict[str, Any] | None:
    """Analyze transient cells and return structured trajectory and animation metadata."""
    if len(chain) <= 1:
        return None

    if transient_cells is None:
        transient_cells = extract_transient_cells(chain)

    frame_count = len(chain) - 1
    if not transient_cells:
        return {
            "animated": True,
            "frame_count": frame_count,
            "transient_pixel_count": 0,
            "transient_cells": [],
            "transient_bbox": None,
            "trajectory_type": "permanent_motion",
            "transient_colors": [],
            "summary_phrase": f"Action animated across {frame_count} frames with permanent outcome.",
            "timeline": [],
        }

    rows = [r for r, _ in transient_cells]
    cols = [c for _, c in transient_cells]
    min_r, max_r = min(rows), max(rows)
    min_c, max_c = min(cols), max(cols)
    bbox = [min_r, min_c, max_r, max_c]
    h_span = max_r - min_r + 1
    w_span = max_c - min_c + 1

    if h_span == 1 and w_span >= 2:
        traj_type = "horizontal_beam"
    elif w_span == 1 and h_span >= 2:
        traj_type = "vertical_beam"
    elif h_span >= 3 and h_span > 2 * w_span:
        traj_type = "vertical_sweep"
    elif w_span >= 3 and w_span > 2 * h_span:
        traj_type = "horizontal_sweep"
    elif len(transient_cells) <= 4 and h_span <= 2 and w_span <= 2:
        traj_type = "localized_pulse"
    else:
        traj_type = "spatial_sweep"

    transient_set = set(transient_cells)
    ephemeral_colors: set[int] = set()
    first_seen_frame: dict[tuple[int, int], int] = {}
    last_active_color: dict[tuple[int, int], int] = {}

    for f_idx, grid in enumerate(chain):
        for r, c in transient_set:
            if r < len(grid) and c < len(grid[r]):
                val = grid[r][c]
                final_val = chain[-1][r][c] if r < len(chain[-1]) and c < len(chain[-1][r]) else 0
                if val != final_val:
                    ephemeral_colors.add(val)
                    last_active_color[(r, c)] = val
                    if (r, c) not in first_seen_frame:
                        first_seen_frame[(r, c)] = f_idx

    timeline: list[dict[str, Any]] = []
    for step_idx in range(1, min(len(chain), max_timeline_steps + 1)):
        prev_g, curr_g = chain[step_idx - 1], chain[step_idx]
        diffs: list[dict[str, Any]] = []
        for r, c in transient_set:
            if r < len(prev_g) and c < len(prev_g[r]) and r < len(curr_g) and c < len(curr_g[r]):
                old_val = prev_g[r][c]
                new_val = curr_g[r][c]
                if old_val != new_val:
                    diffs.append({"r": r, "c": c, "from_color": old_val, "to_color": new_val})
                    if len(diffs) >= max_cells_per_step:
                        break
        if diffs:
            timeline.append({"step": step_idx, "changed_count": len(diffs), "diffs": diffs})

    color_str = ", ".join(str(c) for c in sorted(ephemeral_colors)) if ephemeral_colors else "mixed"
    summary_phrase = (
        f"Action animated across {frame_count} frames: {len(transient_cells)} transient cells "
        f"({traj_type}, rows {min_r}-{max_r}, cols {min_c}-{max_c}, colors [{color_str}]). "
        "Ephemeral beam/scanner/projectile detected."
    )

    return {
        "animated": True,
        "frame_count": frame_count,
        "transient_pixel_count": len(transient_cells),
        "transient_cells": transient_cells,
        "transient_bbox": bbox,
        "trajectory_type": traj_type,
        "transient_colors": sorted(ephemeral_colors),
        "last_active_color": last_active_color,
        "summary_phrase": summary_phrase,
        "timeline": timeline,
    }


def build_transient_composite_grid(
    chain: Sequence[Grid2D],
    transient_cells: Sequence[tuple[int, int]],
    background_color: int = 0,
) -> Grid2D:
    """Build a composite grid with transient paths rendered in their active non-reverted colors."""
    if not chain:
        return []
    base = chain[-1]
    h = len(base)
    w = len(base[0]) if h > 0 else 0
    if h == 0 or w == 0:
        return []

    comp = [[background_color] * w for _ in range(h)]
    wanted = set(transient_cells)

    for grid in chain[:-1]:
        for r, c in wanted:
            if r < len(grid) and c < len(grid[r]):
                val = grid[r][c]
                final_val = base[r][c] if r < len(base) and c < len(base[r]) else background_color
                if val != final_val and val != background_color:
                    comp[r][c] = val

    return comp
