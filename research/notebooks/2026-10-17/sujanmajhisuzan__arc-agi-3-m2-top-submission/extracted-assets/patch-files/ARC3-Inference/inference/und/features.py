"""CONTRACT: Deterministic feature extraction and context-splitting hints (Rules 02, 04, 06).

Provides the canonical feature vocabulary and priority ordering for Brusentsov logic
contradiction resolution (Rule 02 В§3) and diagnostic hints for unexplained laws.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from inference.und.actions import ACTION_VECTORS, DUCK_TO_ENGINE_MAP

# Canonical features ordered by descending physical relevance priority:
# 1. Physical target affordances (target cell color and bounds)
# 2. Neighborhood affordances (cardinal adjacent cells)
# 3. Spatial boundary properties (grid edges)
# 4. Movement dynamics (action, delta, block)
# 5. Temporal parity and cyclical step indices
CANONICAL_FEATURES: tuple[str, ...] = (
    "target_color",
    "target_is_zero",
    "target_in_bounds",
    "adj_north",
    "adj_south",
    "adj_west",
    "adj_east",
    "at_border_top",
    "at_border_bottom",
    "at_border_left",
    "at_border_right",
    "blocked",
    "zero_delta",
    "undo_exact",
    "action_id",
    "dy",
    "dx",
    "step_parity",
    "step_mod_3",
    "step_index",
)

__all__ = [
    "CANONICAL_FEATURES",
    "extract_transition_features",
    "find_separating_features",
    "select_best_splitting_feature",
    "generate_splitting_hints",
]


def _feature_priority_key(cand: tuple[str, Any]) -> tuple[int, str, str]:
    """Sort key enforcing canonical feature prioritization with lexicographical tie-break."""
    feat, val = cand
    try:
        p_idx = CANONICAL_FEATURES.index(feat)
    except ValueError:
        p_idx = len(CANONICAL_FEATURES)
    return (p_idx, str(feat), repr(val))


def extract_transition_features(
    before_grid: Sequence[Sequence[int]],
    action: str | int | Mapping[str, Any],
    after_grid: Sequence[Sequence[int]] | None = None,
    step_index: int = 0,
    actor_pos: tuple[int, int] | None = None,
    actor_color: int | None = None,
    result_flags: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically extract canonical observation features from a transition step."""
    if isinstance(action, int):
        act_id = f"ACTION{action}"
    elif isinstance(action, Mapping):
        raw = action.get("action_id", action.get("action", ""))
        act_id = str(raw).upper()
    else:
        act_id = str(action).upper()
    act_id = DUCK_TO_ENGINE_MAP.get(act_id, act_id)
    dy, dx = ACTION_VECTORS.get(act_id, (0, 0))

    h = len(before_grid) if before_grid else 0
    w = len(before_grid[0]) if h > 0 and before_grid[0] else 0
    pos = actor_pos
    if pos is None and actor_color is not None and h > 0 and w > 0:
        for r in range(h):
            for c in range(w):
                if before_grid[r][c] == actor_color:
                    pos = (r, c)
                    break
            if pos is not None:
                break

    if pos is not None:
        ar, ac = pos
        at_top = (ar == 0)
        at_bottom = (ar == h - 1 if h > 0 else False)
        at_left = (ac == 0)
        at_right = (ac == w - 1 if w > 0 else False)
        adj_n = before_grid[ar - 1][ac] if (0 <= ar - 1 < h and 0 <= ac < w) else -1
        adj_s = before_grid[ar + 1][ac] if (0 <= ar + 1 < h and 0 <= ac < w) else -1
        adj_w = before_grid[ar][ac - 1] if (0 <= ar < h and 0 <= ac - 1 < w) else -1
        adj_e = before_grid[ar][ac + 1] if (0 <= ar < h and 0 <= ac + 1 < w) else -1
        tr_r, tr_c = ar + dy, ac + dx
        in_bounds = (0 <= tr_r < h and 0 <= tr_c < w)
        tgt_col = int(before_grid[tr_r][tr_c]) if in_bounds else -1
        tgt_zero = (tgt_col == 0) if in_bounds else False
    else:
        at_top = at_bottom = at_left = at_right = False
        adj_n = adj_s = adj_w = adj_e = -1
        in_bounds = False
        tgt_col = -1
        tgt_zero = False

    zero_delta = (before_grid == after_grid) if (before_grid is not None and after_grid is not None) else False

    feats: dict[str, Any] = {
        "action_id": act_id,
        "dy": dy,
        "dx": dx,
        "target_in_bounds": in_bounds,
        "target_color": tgt_col,
        "target_is_zero": tgt_zero,
        "at_border_top": at_top,
        "at_border_bottom": at_bottom,
        "at_border_left": at_left,
        "at_border_right": at_right,
        "adj_north": adj_n,
        "adj_south": adj_s,
        "adj_west": adj_w,
        "adj_east": adj_e,
        "step_parity": "even" if (step_index % 2 == 0) else "odd",
        "step_mod_3": step_index % 3,
        "zero_delta": zero_delta,
        "blocked": zero_delta,
    }
    if actor_color is not None:
        feats["actor_color"] = actor_color
    if result_flags:
        feats.update(result_flags)
    return feats


def find_separating_features(
    support_contexts: Sequence[Mapping[str, Any]],
    counter_contexts: Sequence[Mapping[str, Any]],
) -> list[tuple[str, Any]]:
    """Identify features holding consistently across support and failing on counter examples."""
    if not support_contexts or not counter_contexts:
        return []

    cands: list[tuple[str, Any]] = []
    all_keys = sorted({k for ctx in support_contexts for k in ctx.keys()})
    for f in all_keys:
        values = {ctx[f] for ctx in support_contexts if f in ctx}
        for v in values:
            if all(ctx.get(f) == v for ctx in support_contexts) and all(
                ctx.get(f) != v for ctx in counter_contexts
            ):
                cands.append((f, v))

    cands.sort(key=_feature_priority_key)
    return cands


def select_best_splitting_feature(
    candidates: Sequence[tuple[str, Any]],
) -> tuple[str, Any] | None:
    """Select the highest-priority splitting feature deterministically."""
    if not candidates:
        return None
    return min(candidates, key=_feature_priority_key)


def generate_splitting_hints(
    claim_id: str,
    kind: str,
    candidates: Sequence[tuple[str, Any]],
    unexplained: bool = False,
) -> list[str]:
    """Generate diagnostic hints explaining context split or unexplained contradiction."""
    hints: list[str] = []
    if unexplained or not candidates:
        hints.append(
            f"Contradiction in claim '{claim_id}' ({kind}) is unexplained by canonical features."
        )
        return hints

    best = select_best_splitting_feature(candidates)
    if best is None:
        hints.append(
            f"Contradiction in claim '{claim_id}' ({kind}) is unexplained by canonical features."
        )
        return hints

    f, v = best
    hints.append(f"Split claim '{claim_id}' ({kind}) by context condition: {f}=={v}")
    alts = [c for c in candidates if c != best]
    if alts:
        alt_str = ", ".join(f"{cf}=={cv}" for cf, cv in alts[:3])
        hints.append(f"Alternative candidate features: {alt_str}")
    return hints
