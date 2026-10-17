"""CONTRACT: Gestalt common fate grouping for object-centric perception (Rules 02, 04, 06).

Provides deterministic clustering of objects moving synchronously with shared motion vectors,
evaluates motion rigidity across frame histories, and synthesizes composite planning entities.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from inference.und.perception.arga_lite import PlanningObject
from inference.und.perception.tracker import TrackedObject
from inference.und.types import BoundingBox, Centroid


@dataclass(frozen=True)
class CommonFateConfig:
    """Configuration thresholds for common fate grouping."""
    velocity_tolerance: float = 0.15
    min_group_size: int = 2
    include_static: bool = False
    static_velocity_threshold: float = 0.05
    max_spatial_distance: float | None = None


@dataclass(frozen=True)
class CommonFateGroup:
    """Group of entities sharing synchronized motion dynamics (common fate)."""
    group_id: str
    member_ids: tuple[str, ...]
    motion_vector: tuple[float, float]
    bbox: BoundingBox
    centroid: Centroid
    total_area: int
    colors: tuple[int, ...]
    persistence_frames: int = 1
    is_rigid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "member_ids": list(self.member_ids),
            "motion_vector": self.motion_vector,
            "bbox": self.bbox.to_dict(),
            "centroid": self.centroid.to_dict(),
            "total_area": self.total_area,
            "colors": list(self.colors),
            "persistence_frames": self.persistence_frames,
            "is_rigid": self.is_rigid,
        }


def compute_pairwise_motion_similarity(
    obj_a: Any,
    obj_b: Any,
    tolerance: float = 0.15,
) -> float:
    """Compute normalized motion similarity in [0, 1] between two tracked entities."""
    va = getattr(obj_a, "velocity", (0.0, 0.0))
    vb = getattr(obj_b, "velocity", (0.0, 0.0))
    vya, vxa = float(va[0]), float(va[1])
    vyb, vxb = float(vb[0]), float(vb[1])

    mag_a = math.sqrt(vya * vya + vxa * vxa)
    mag_b = math.sqrt(vyb * vyb + vxb * vxb)

    if mag_a < 1e-4 and mag_b < 1e-4:
        return 1.0
    if mag_a < 1e-4 or mag_b < 1e-4:
        return 0.0

    dot = (vya * vyb + vxa * vxb)
    cos_sim = max(0.0, dot / (mag_a * mag_b))
    mag_sim = min(mag_a, mag_b) / max(mag_a, mag_b)

    # Combine directional alignment and magnitude ratio
    return round(cos_sim * mag_sim, 4)


def is_motion_rigid(
    tracks: Sequence[TrackedObject],
    tolerance: float = 0.15,
) -> bool:
    """Return True if pairwise distances between all tracks remain invariant across history."""
    if len(tracks) < 2:
        return True

    for i in range(len(tracks)):
        for j in range(i + 1, len(tracks)):
            ti = tracks[i]
            tj = tracks[j]
            hi_dict = {f_idx: c for f_idx, c in ti.history}
            hj_dict = {f_idx: c for f_idx, c in tj.history}
            shared_frames = sorted(set(hi_dict.keys()) & set(hj_dict.keys()))
            if len(shared_frames) < 2:
                continue

            distances: list[float] = []
            for f_idx in shared_frames:
                ci = hi_dict[f_idx]
                cj = hj_dict[f_idx]
                dr = ci.row - cj.row
                dc = ci.col - cj.col
                distances.append(math.sqrt(dr * dr + dc * dc))

            if (max(distances) - min(distances)) > tolerance:
                return False

    return True


def group_tracks_by_common_fate(
    tracks: Sequence[TrackedObject],
    config: CommonFateConfig | None = None,
) -> list[CommonFateGroup]:
    """Group tracked objects exhibiting shared velocity dynamics into CommonFateGroup instances."""
    cfg = config or CommonFateConfig()
    candidates: list[TrackedObject] = []
    for t in tracks:
        mag = math.sqrt(t.velocity[0] ** 2 + t.velocity[1] ** 2)
        if mag >= cfg.static_velocity_threshold or cfg.include_static:
            candidates.append(t)

    n = len(candidates)
    if n < cfg.min_group_size:
        return []

    # Disjoint-set union structure
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            sim = compute_pairwise_motion_similarity(candidates[i], candidates[j], cfg.velocity_tolerance)
            if sim >= (1.0 - cfg.velocity_tolerance):
                if cfg.max_spatial_distance is not None:
                    ci = candidates[i].centroid
                    cj = candidates[j].centroid
                    dist = math.sqrt((ci.row - cj.row) ** 2 + (ci.col - cj.col) ** 2)
                    if dist > cfg.max_spatial_distance:
                        continue
                union(i, j)

    # Collect connected components
    clusters: dict[int, list[TrackedObject]] = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(candidates[i])

    groups: list[CommonFateGroup] = []
    for root, cluster in sorted(clusters.items()):
        if len(cluster) < cfg.min_group_size:
            continue
        member_ids = tuple(sorted(t.persistent_id for t in cluster))
        avg_vy = sum(t.velocity[0] for t in cluster) / len(cluster)
        avg_vx = sum(t.velocity[1] for t in cluster) / len(cluster)
        min_r = min(t.bbox.min_row for t in cluster)
        min_c = min(t.bbox.min_col for t in cluster)
        max_r = max(t.bbox.max_row for t in cluster)
        max_c = max(t.bbox.max_col for t in cluster)
        centroid_r = sum(t.centroid.row for t in cluster) / len(cluster)
        centroid_c = sum(t.centroid.col for t in cluster) / len(cluster)
        area = sum(t.area for t in cluster)
        colors = tuple(sorted({t.color for t in cluster}))
        frames = min(len(t.history) for t in cluster)
        rigid = is_motion_rigid(cluster, cfg.velocity_tolerance)
        gid = f"cfg_{member_ids[0]}_{len(member_ids)}"

        groups.append(
            CommonFateGroup(
                group_id=gid,
                member_ids=member_ids,
                motion_vector=(round(avg_vy, 3), round(avg_vx, 3)),
                bbox=BoundingBox(min_row=min_r, min_col=min_c, max_row=max_r, max_col=max_c),
                centroid=Centroid(row=centroid_r, col=centroid_c),
                total_area=area,
                colors=colors,
                persistence_frames=frames,
                is_rigid=rigid,
            )
        )

    return sorted(groups, key=lambda g: g.group_id)


def merge_group_to_planning_object(
    group: CommonFateGroup,
    members: Sequence[Any],
) -> PlanningObject:
    """Synthesize a unified PlanningObject from grouped sub-entities."""
    all_pixels: set[tuple[int, int]] = set()
    hist: Counter[int] = Counter()

    for m in members:
        px = getattr(m, "pixels", [])
        all_pixels.update(px)
        m_hist = getattr(m, "color_histogram", {})
        if m_hist:
            hist.update(m_hist)
        else:
            col = getattr(m, "color", 0)
            area = getattr(m, "area", len(px) or 1)
            hist[col] += area

    if not all_pixels and group.bbox:
        for r in range(group.bbox.min_row, group.bbox.max_row + 1):
            for c in range(group.bbox.min_col, group.bbox.max_col + 1):
                all_pixels.add((r, c))

    sorted_pixels = sorted(all_pixels)
    primary_color = hist.most_common(1)[0][0] if hist else 0
    is_single = (len(hist) <= 1)

    return PlanningObject(
        id=group.group_id,
        color=primary_color,
        color_histogram=dict(hist),
        area=group.total_area,
        bbox=group.bbox,
        centroid=group.centroid,
        pixels=sorted_pixels,
        is_single_color=is_single,
        role="compound_entity",
        children_ids=list(group.member_ids),
    )


__all__ = [
    "CommonFateConfig",
    "CommonFateGroup",
    "compute_pairwise_motion_similarity",
    "group_tracks_by_common_fate",
    "is_motion_rigid",
    "merge_group_to_planning_object",
]
