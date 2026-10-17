"""Object-level Hungarian frame difference engine for ARC-AGI-3.

Pure-Python implementation with zero third-party dependencies.
Provides Hungarian bipartite matching for connected components,
classifying state transitions into moved, rotated, appeared, disappeared,
changed_color, and resized.

Also distinguishes whole-board changes from interior gameplay changes
to prevent peripheral timer/HUD changes from masquerading as game progress.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

_ORTH = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _extract_components(grid: list[list[int]]) -> list[dict[str, Any]]:
    """Segment a 2D integer grid into 4-connected same-color components."""
    if not grid or not grid[0]:
        return []
    h = len(grid)
    w = len(grid[0])
    visited = [[False] * w for _ in range(h)]
    nodes: list[dict[str, Any]] = []

    for r in range(h):
        for c in range(w):
            if visited[r][c]:
                continue
            color = grid[r][c]
            cells: list[tuple[int, int]] = []
            queue = [(r, c)]
            visited[r][c] = True

            while queue:
                cr, cc = queue.pop()
                cells.append((cr, cc))
                for dr, dc in _ORTH:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr][nc]:
                        if grid[nr][nc] == color:
                            visited[nr][nc] = True
                            queue.append((nr, nc))

            min_r = min(cr for cr, _ in cells)
            max_r = max(cr for cr, _ in cells)
            min_c = min(cc for _, cc in cells)
            max_c = max(cc for _, cc in cells)
            norm_cells = sorted((cr - min_r, cc - min_c) for cr, cc in cells)

            # Rotation-sensitive pose signature
            pose_payload = repr((color, norm_cells)).encode("utf-8")
            pose_hash = hashlib.sha1(pose_payload).hexdigest()[:16]

            # Color-independent shape signature
            shape_payload = repr(norm_cells).encode("utf-8")
            shape_hash = hashlib.sha1(shape_payload).hexdigest()[:16]

            # Rotation-invariant canonical shape signature
            rot_variants = [norm_cells]
            curr = norm_cells
            for _ in range(3):
                max_nr = max(pr for pr, _ in curr)
                curr = sorted((pc, max_nr - pr) for pr, pc in curr)
                rot_variants.append(curr)
            canonical = min(rot_variants)
            canon_payload = repr((color, canonical)).encode("utf-8")
            canon_hash = hashlib.sha1(canon_payload).hexdigest()[:16]

            nodes.append({
                "color": color,
                "pixels": len(cells),
                "cells": cells,
                "at": [min_r, min_c],
                "bbox": [min_r, min_c, max_r, max_c],
                "center2": (min_r + max_r, min_c + max_c),
                "hash": canon_hash,
                "pose_hash": pose_hash,
                "shape_hash": shape_hash,
            })

    return nodes


def _hungarian(cost: list[list[float]]) -> list[int]:
    """Minimum-cost assignment (Jonker-Volgenant style with potentials).

    cost: n x m matrix with n <= m. Returns list mapping row -> column.
    """
    n = len(cost)
    m = len(cost[0]) if n else 0
    inf = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    assignment = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            assignment[p[j] - 1] = j - 1
    return assignment


def _bbox_area(b: list[int]) -> int:
    return max(0, b[2] - b[0] + 1) * max(0, b[3] - b[1] + 1)


def _overlap_ratio(b1: list[int], b2: list[int]) -> float:
    inter_r = min(b1[2], b2[2]) - max(b1[0], b2[0]) + 1
    inter_c = min(b1[3], b2[3]) - max(b1[1], b2[1]) + 1
    if inter_r <= 0 or inter_c <= 0:
        return 0.0
    smaller = min(_bbox_area(b1), _bbox_area(b2))
    return (inter_r * inter_c) / smaller if smaller else 0.0


def compute_grid_frame_diff(
    grid_a: list[list[int]],
    grid_b: list[list[int]],
    border_margin: int | None = None,
    max_group_match: int | None = 64,
) -> dict[str, Any]:
    """Compute structured object-level diff between grid_a and grid_b.

    Returns dictionary with:
    - changed_cell_count: int
    - interior_changed_cell_count: int
    - gameplay_changed: bool
    - moved: list[dict]
    - rotated: list[dict]
    - appeared: list[dict]
    - disappeared: list[dict]
    - changed_color: list[dict]
    - resized: list[dict]
    """
    if not grid_a or not grid_b:
        return {
            "changed_cell_count": 0,
            "interior_changed_cell_count": 0,
            "gameplay_changed": False,
            "moved": [],
            "rotated": [],
            "appeared": [],
            "disappeared": [],
            "changed_color": [],
            "resized": [],
        }

    h = min(len(grid_a), len(grid_b))
    w = min(len(grid_a[0]), len(grid_b[0]))

    # Border calculation: explicit margin if provided, otherwise physical HUD detection
    if border_margin is not None and border_margin > 0:
        border = max(0, int(border_margin))
    else:
        border = 0

    changed: set[tuple[int, int]] = set()
    interior_changed: set[tuple[int, int]] = set()

    for r in range(h):
        row_a = grid_a[r]
        row_b = grid_b[r]
        for c in range(w):
            if row_a[c] != row_b[c]:
                changed.add((r, c))
                if border <= r < (h - border) and border <= c < (w - border):
                    interior_changed.add((r, c))

    gameplay_changed = len(interior_changed) > 0

    if border_margin is None and changed:
        from inference.und.perception.arga_lite import is_only_peripheral_hud_delta
        if is_only_peripheral_hud_delta(grid_a, grid_b):
            gameplay_changed = False
            interior_changed = set()

    if not changed:
        return {
            "changed_cell_count": 0,
            "interior_changed_cell_count": 0,
            "gameplay_changed": False,
            "moved": [],
            "rotated": [],
            "appeared": [],
            "disappeared": [],
            "changed_color": [],
            "resized": [],
        }

    nodes_a = _extract_components(grid_a)
    nodes_b = _extract_components(grid_b)

    # Filter to touched components only (with 1-cell dilation)
    def touched_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        touched: list[dict[str, Any]] = []
        for node in nodes:
            b = node["bbox"]
            r0, c0, r1, c1 = b[0], b[1], b[2], b[3]
            if any(r0 - 1 <= cr <= r1 + 1 and c0 - 1 <= cc <= c1 + 1 for cr, cc in changed):
                touched.append(node)
        return touched

    before_nodes = touched_nodes(nodes_a)
    after_nodes = touched_nodes(nodes_b)

    moved: list[dict[str, Any]] = []
    rotated: list[dict[str, Any]] = []
    appeared: list[dict[str, Any]] = []
    disappeared: list[dict[str, Any]] = []

    groups_before: dict[str, list[dict[str, Any]]] = {}
    for node in before_nodes:
        groups_before.setdefault(node["hash"], []).append(node)

    groups_after: dict[str, list[dict[str, Any]]] = {}
    for node in after_nodes:
        groups_after.setdefault(node["hash"], []).append(node)

    for key, group_a in groups_before.items():
        group_b = groups_after.pop(key, [])
        if max_group_match is not None and max(len(group_a), len(group_b)) > max_group_match:
            for na in group_a:
                disappeared.append({
                    "color": na["color"],
                    "pixels": na["pixels"],
                    "hash": na["hash"],
                    "shape_hash": na["shape_hash"],
                    "at": list(na["at"]),
                    "bbox": list(na["bbox"]),
                })
            for nb in group_b:
                appeared.append({
                    "color": nb["color"],
                    "pixels": nb["pixels"],
                    "hash": nb["hash"],
                    "shape_hash": nb["shape_hash"],
                    "at": list(nb["at"]),
                    "bbox": list(nb["bbox"]),
                })
            continue

        if not group_b:
            for na in group_a:
                disappeared.append({
                    "color": na["color"],
                    "pixels": na["pixels"],
                    "hash": na["hash"],
                    "shape_hash": na["shape_hash"],
                    "at": list(na["at"]),
                    "bbox": list(na["bbox"]),
                })
            continue

        transposed = len(group_a) > len(group_b)
        rows, cols = (group_b, group_a) if transposed else (group_a, group_b)
        cost = []
        for row_node in rows:
            cr = row_node["center2"]
            cost.append([
                abs(cr[0] - col_node["center2"][0]) + abs(cr[1] - col_node["center2"][1])
                for col_node in cols
            ])

        assignment = _hungarian(cost)
        matched_cols: set[int] = set()
        for row_index, col_index in enumerate(assignment):
            if col_index < 0:
                continue
            matched_cols.add(col_index)
            na, nb = (cols[col_index], rows[row_index]) if transposed else (rows[row_index], cols[col_index])
            pa, pb = na["at"], nb["at"]
            if pa != pb:
                moved.append({
                    "color": na["color"],
                    "pixels": na["pixels"],
                    "hash": na["hash"],
                    "from": list(pa),
                    "to": list(pb),
                    "dr": pb[0] - pa[0],
                    "dc": pb[1] - pa[1],
                })
            elif na["pose_hash"] != nb["pose_hash"]:
                rotated.append({
                    "color": na["color"],
                    "pixels": na["pixels"],
                    "hash": na["hash"],
                    "at": list(pb),
                })

        if transposed:
            for col_index, na in enumerate(cols):
                if col_index not in matched_cols:
                    disappeared.append({
                        "color": na["color"],
                        "pixels": na["pixels"],
                        "hash": na["hash"],
                        "shape_hash": na["shape_hash"],
                        "at": list(na["at"]),
                        "bbox": list(na["bbox"]),
                    })
        else:
            for col_index, nb in enumerate(cols):
                if col_index not in matched_cols:
                    appeared.append({
                        "color": nb["color"],
                        "pixels": nb["pixels"],
                        "hash": nb["hash"],
                        "shape_hash": nb["shape_hash"],
                        "at": list(nb["at"]),
                        "bbox": list(nb["bbox"]),
                    })

    for group_b in groups_after.values():
        for nb in group_b:
            appeared.append({
                "color": nb["color"],
                "pixels": nb["pixels"],
                "hash": nb["hash"],
                "shape_hash": nb["shape_hash"],
                "at": list(nb["at"]),
                "bbox": list(nb["bbox"]),
            })

    # Exact color changes (same shape, same location, different color)
    changed_color: list[dict[str, Any]] = []
    used_gone: set[int] = set()
    used_new: set[int] = set()

    for gi, gone in enumerate(disappeared):
        for ni, new in enumerate(appeared):
            if ni in used_new:
                continue
            if (
                gone["at"] == new["at"]
                and gone.get("shape_hash")
                and gone.get("shape_hash") == new.get("shape_hash")
                and gone["color"] != new["color"]
            ):
                changed_color.append({
                    "at": list(gone["at"]),
                    "pixels": gone["pixels"],
                    "before_color": gone["color"],
                    "after_color": new["color"],
                    "before_hash": gone.get("hash"),
                    "after_hash": new.get("hash"),
                })
                used_gone.add(gi)
                used_new.add(ni)
                break

    disappeared = [e for idx, e in enumerate(disappeared) if idx not in used_gone]
    appeared = [e for idx, e in enumerate(appeared) if idx not in used_new]

    # Resized objects (overlapping footprint with changed area)
    resized: list[dict[str, Any]] = []
    candidates: list[tuple[float, float, int, int]] = []
    for gi, gone in enumerate(disappeared):
        for ni, new in enumerate(appeared):
            if gone["color"] != new["color"]:
                continue
            bg = gone.get("bbox", [0, 0, -1, -1])
            bn = new.get("bbox", [0, 0, -1, -1])
            ratio = _overlap_ratio(bg, bn)
            if ratio >= 0.5:
                ag, an = _bbox_area(bg), _bbox_area(bn)
                similarity = (min(ag, an) / max(ag, an)) if max(ag, an) else 0.0
                candidates.append((ratio, similarity, gi, ni))

    candidates.sort(key=lambda it: (-it[0], -it[1]))
    used_gone_re: set[int] = set()
    used_new_re: set[int] = set()
    for _, _, gi, ni in candidates:
        if gi in used_gone_re or ni in used_new_re:
            continue
        used_gone_re.add(gi)
        used_new_re.add(ni)
        gone, new = disappeared[gi], appeared[ni]
        resized.append({
            "at_before": list(gone["at"]),
            "at_after": list(new["at"]),
            "color": gone["color"],
            "before_pixels": gone["pixels"],
            "after_pixels": new["pixels"],
            "before_hash": gone.get("hash"),
            "after_hash": new.get("hash"),
        })

    disappeared = [e for idx, e in enumerate(disappeared) if idx not in used_gone_re]
    appeared = [e for idx, e in enumerate(appeared) if idx not in used_new_re]

    return {
        "changed_cell_count": len(changed),
        "interior_changed_cell_count": len(interior_changed),
        "gameplay_changed": gameplay_changed,
        "moved": moved,
        "rotated": rotated,
        "appeared": appeared,
        "disappeared": disappeared,
        "changed_color": changed_color,
        "resized": resized,
    }
