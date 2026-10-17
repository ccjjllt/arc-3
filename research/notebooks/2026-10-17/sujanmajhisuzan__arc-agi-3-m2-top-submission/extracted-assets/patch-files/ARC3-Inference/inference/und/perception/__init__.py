"""CONTRACT: Object-centric perception and frame difference tracking (Rules 02, 04)."""
from __future__ import annotations

from inference.und.perception.arga_lite import (
    ARGALiteSnapshot,
    PlanningObject,
    detect_background_color,
    evaluate_board_and_gameplay_delta,
    extract_arga_snapshot,
    extract_spatial_relations,
    is_only_peripheral_hud_delta,
)
from inference.und.perception.common_fate import (
    CommonFateConfig,
    CommonFateGroup,
    compute_pairwise_motion_similarity,
    group_tracks_by_common_fate,
    is_motion_rigid,
    merge_group_to_planning_object,
)
from inference.und.perception.frame_diff import (
    compute_grid_frame_diff,
)
from inference.und.perception.tracker import (
    PersistentObjectTracker,
    TrackedObject,
    jaccard_similarity,
    mask_jaccard,
)

__all__ = [
    "ARGALiteSnapshot",
    "CommonFateConfig",
    "CommonFateGroup",
    "PersistentObjectTracker",
    "PlanningObject",
    "TrackedObject",
    "compute_grid_frame_diff",
    "compute_pairwise_motion_similarity",
    "detect_background_color",
    "evaluate_board_and_gameplay_delta",
    "extract_arga_snapshot",
    "extract_spatial_relations",
    "group_tracks_by_common_fate",
    "is_motion_rigid",
    "is_only_peripheral_hud_delta",
    "jaccard_similarity",
    "mask_jaccard",
    "merge_group_to_planning_object",
]
