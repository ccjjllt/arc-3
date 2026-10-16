"""Read-only, frame-bound region representations; not installed in the agent.

Coordinates are inclusive (top, left, bottom, right). Foreground symbols are
explicit, and binary keys describe only their union in the *entire requested
rectangle*: no trimming, translation, rotation or reflection is implicit.
This module uses public FrameView fields only, never the numeric/private grid.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any, Callable, Iterable


ARC_SYMBOLS = "WwgGcBMPRbSYOrNp"


def _reference(frame: Any) -> tuple[dict[str, Any], list[str]]:
    rows = frame.ascii.splitlines()
    shape = tuple(frame.shape)
    if (len(shape) != 2 or not rows or not rows[0]
            or shape != (len(rows), len(rows[0]))
            or any(len(row) != shape[1] for row in rows)):
        raise ValueError("Frame ascii and declared rectangular shape disagree")
    if (type(frame.step) is not int or type(frame.level) is not int
            or frame.step < 0 or frame.level < 0):
        raise ValueError("Frame step and level must be nonnegative integers")
    return {
        "step": frame.step,
        "level": frame.level,
        "shape": list(shape),
        "ascii_sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
    }, rows


def _key(rows: list[str]) -> str:
    return f"{len(rows)}x{len(rows[0])}:" + "/".join(rows)


def _rotate(rows: list[str]) -> list[str]:
    return ["".join(row) for row in zip(*rows[::-1])]


def _transform_keys(rows: list[str]) -> dict[str, str]:
    rotations, mirrored_rotations = [], []
    current, mirror = rows, [row[::-1] for row in rows]
    for _ in range(4):
        rotations.append(_key(current))
        mirrored_rotations.append(_key(mirror))
        current, mirror = _rotate(current), _rotate(mirror)
    return {
        "rotation_canonical": min(rotations),
        "mirrored_exact": mirrored_rotations[0],
        "mirrored_rotation_canonical": min(mirrored_rotations),
        "dihedral_canonical": min(rotations + mirrored_rotations),
    }


def _components(mask: list[str], top: int, left: int) -> list[dict[str, Any]]:
    remaining = {(r, c) for r, row in enumerate(mask)
                 for c, value in enumerate(row) if value == "1"}
    result = []
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        stack, cells = [first], []
        while stack:
            r, c = stack.pop()
            cells.append((r, c))
            for candidate in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
                if candidate in remaining:
                    remaining.remove(candidate)
                    stack.append(candidate)
        r0, c0 = min(r for r, _ in cells), min(c for _, c in cells)
        r1, c1 = max(r for r, _ in cells), max(c for _, c in cells)
        result.append({"pixels": len(cells), "bbox": [r0+top, c0+left, r1+top, c1+left]})
    return result


class RegionReader:
    """Resolve the supplied current-frame getter on every read; cache nothing.

    The getter must resolve the live runtime global, e.g. lambda: current_frame,
    not close over a previously captured frame. Frame freshness cannot be proved
    outside that contract. expect_frame optionally binds a request to a prior
    reference; mismatches return no pixels or keys. from_node requires it because
    segmentation node IDs are frame-local. References are scoped to this game
    session, not global object IDs.
    """

    def __init__(self, current_frame: Callable[[], Any], *,
                 known_symbols: str = ARC_SYMBOLS, max_cells: int = 1024):
        if not callable(current_frame):
            raise TypeError("current_frame must be a getter, not a saved frame")
        if (not known_symbols or len(set(known_symbols)) != len(known_symbols)
                or any(char.isspace() for char in known_symbols)):
            raise ValueError("known_symbols must contain distinct non-whitespace symbols")
        if type(max_cells) is not int or max_cells < 1:
            raise ValueError("max_cells must be a positive integer")
        self._get_frame = current_frame
        self._known_symbols = frozenset(known_symbols)
        self._max_cells = max_cells

    def reference(self) -> dict[str, Any]:
        """Identify the getter's current frame without retaining a frame cache."""
        return _reference(self._get_frame())[0]

    def read(self, bbox: Iterable[int], *, foreground: Iterable[str],
             expect_frame: dict[str, Any] | None = None,
             include_transforms: bool = False) -> dict[str, Any]:
        frame = self._get_frame()
        ref, rows = _reference(frame)
        return self._read(ref, rows, bbox, foreground, expect_frame, include_transforms)

    def from_node(self, node_id: int, *, foreground: Iterable[str],
                  expect_frame: dict[str, Any], inset: int = 0,
                  include_transforms: bool = False) -> dict[str, Any]:
        """Read the bbox of a current segmentation node, optionally inset explicitly.

        A bounding rectangle may contain multiple components or symbols. This
        does not infer a semantic glyph, slot width, foreground, or game rule.
        No automatic inset is applied, even when the perimeter has one color.
        """
        frame = self._get_frame()
        ref, rows = _reference(frame)
        if expect_frame != ref:
            return self._failure(ref, "frame_reference_mismatch")
        if type(node_id) is not int or type(inset) is not int or inset < 0:
            return self._failure(ref, "invalid_node_or_inset")
        matches = [n for n in frame.segmentation["nodes"] if n.get("id") == node_id]
        if len(matches) != 1 or not matches[0].get("boundary"):
            return self._failure(ref, "node_not_found_or_missing_boundary")
        node = matches[0]
        boundary = node["boundary"]
        if any(len(p) != 2 or any(type(v) is not int for v in p) for p in boundary):
            return self._failure(ref, "invalid_node_boundary")
        t, l = min(p[0] for p in boundary), min(p[1] for p in boundary)
        b, r = max(p[0] for p in boundary), max(p[1] for p in boundary)
        if not (0 <= t <= b < len(rows) and 0 <= l <= r < len(rows[0])):
            return self._failure(ref, "node_boundary_out_of_bounds")
        perimeter = rows[t][l:r+1] + rows[b][l:r+1]
        perimeter += "".join(rows[y][l] + rows[y][r] for y in range(t+1, b))
        uniform_border = bool(perimeter) and set(perimeter) == {node.get("color")}
        result = self._read(ref, rows, (t+inset, l+inset, b-inset, r-inset),
                            foreground, ref, include_transforms)
        result["selection"] = {
            "kind": "current_segmentation_node_bbox", "node_id": node_id,
            "node_color": node.get("color"), "node_bbox": [t, l, b, r],
            "inset": inset, "uniform_node_color_perimeter": uniform_border,
        }
        if inset and not uniform_border:
            result["diagnostics"].append("inset_without_uniform_node_color_perimeter")
        return result

    @staticmethod
    def _failure(ref: dict[str, Any], reason: str, **details: Any) -> dict[str, Any]:
        return {"schema_version": 1, "frame": ref, "status": "unavailable",
                "diagnostics": [reason], "exact_key": None, **details}

    def _read(self, ref: dict[str, Any], rows: list[str], bbox: Iterable[int],
              foreground: Iterable[str], expect_frame: dict[str, Any] | None,
              include_transforms: bool) -> dict[str, Any]:
        if expect_frame is not None and expect_frame != ref:
            return self._failure(ref, "frame_reference_mismatch")
        try:
            bounds = list(bbox)
            symbols = list(foreground)
        except TypeError:
            return self._failure(ref, "bbox_or_foreground_not_iterable")
        if len(bounds) != 4 or any(type(v) is not int for v in bounds):
            return self._failure(ref, "bbox_requires_four_integers")
        top, left, bottom, right = bounds
        height, width = len(rows), len(rows[0])
        if not (0 <= top <= bottom < height and 0 <= left <= right < width):
            return self._failure(ref, "bbox_out_of_bounds_or_reversed", bbox=bounds)
        if (bottom-top+1)*(right-left+1) > self._max_cells:
            return self._failure(ref, "region_exceeds_max_cells", bbox=bounds)
        if not symbols or any(not isinstance(s, str) or len(s) != 1 for s in symbols):
            return self._failure(ref, "foreground_requires_explicit_single_character_symbols")
        selected = frozenset(symbols)
        unknown = sorted(selected - self._known_symbols)
        if unknown:
            return self._failure(ref, "unknown_foreground_symbol", unknown_symbols=unknown)
        raw = [row[left:right+1] for row in rows[top:bottom+1]]
        unknown = sorted(set("".join(raw)) - self._known_symbols)
        if unknown:
            return self._failure(ref, "unknown_observed_symbol", unknown_symbols=unknown)
        mask = ["".join("1" if char in selected else "0" for char in row) for row in raw]
        counts = Counter("".join(raw))
        pixels = sum(counts[s] for s in selected)
        components = _components(mask, top, left)
        touches, crossing = set(), Counter()
        # Only one-cell neighbours are inspected beyond the requested region.
        # Positive crossing confirms a connected foreground cut. Zero cannot
        # exclude a wholly omitted disconnected part or a wrong semantic region.
        for row in range(top, bottom+1):
            for col in range(left, right+1):
                if rows[row][col] not in selected:
                    continue
                edges = []
                if row == top: edges.append(("top", row-1, col))
                if row == bottom: edges.append(("bottom", row+1, col))
                if col == left: edges.append(("left", row, col-1))
                if col == right: edges.append(("right", row, col+1))
                for side, rr, cc in edges:
                    touches.add(side)
                    if 0 <= rr < height and 0 <= cc < width and rows[rr][cc] in selected:
                        crossing[side] += 1
        diagnostics = []
        if not pixels: diagnostics.append("empty_foreground_mask")
        if len(components) > 1: diagnostics.append("multiple_foreground_components")
        if crossing: diagnostics.append("foreground_continues_outside_region")
        frame_edges = [side for side, value in
                       (("top", top == 0), ("bottom", bottom == height-1),
                        ("left", left == 0), ("right", right == width-1)) if value]
        if frame_edges: diagnostics.append("region_reaches_frame_edge")
        result = {
            "schema_version": 1, "frame": ref, "status": "observed",
            "bbox_order": "top,left,bottom,right; zero_based; inclusive",
            "bbox": bounds, "foreground": sorted(selected),
            "raw_rows": raw, "mask_rows": mask, "foreground_pixels": pixels,
            "color_counts": dict(sorted(counts.items())),
            "components_4_connected": components,
            "edge_observations": {"foreground_touches": sorted(touches),
                                  "foreground_crossing_counts": dict(sorted(crossing.items())),
                                  "frame_edges": frame_edges},
            "diagnostics": diagnostics,
            "exact_key": _key(mask) if pixels else None,
        }
        if include_transforms:
            result["transform_keys"] = _transform_keys(mask) if pixels else None
        return result
