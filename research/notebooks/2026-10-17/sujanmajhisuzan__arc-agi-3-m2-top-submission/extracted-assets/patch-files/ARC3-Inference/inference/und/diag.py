"""CONTRACT: Filtered counterexample and mismatch diagnostics (Rules 01, 04, 05).

Provides deterministic diagnostic formatting bounded by DIAG_MAX_LINES (<= 12 lines)
to protect the 32K context budget while delivering actionable discrepancy feedback.
"""
from __future__ import annotations

from typing import Any, Sequence

from inference.und.config.thresholds import DIAG_MAX_LINES
from inference.und.perception.frame_diff import compute_grid_frame_diff
from inference.und.texts import DIAGNOSTIC_COUNTEREXAMPLE_TEMPLATE


def filter_diagnostic_lines(text: str, max_lines: int = DIAG_MAX_LINES) -> str:
    """Ensure diagnostic text strictly adheres to max_lines bound."""
    lines = [line for line in text.strip().splitlines() if line]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    keep = max_lines - 1
    truncated = lines[:keep]
    truncated.append(f"[... truncated: {len(lines) - keep} additional line(s)]")
    return "\n".join(truncated)


def format_step_mismatch_diagnostic(
    action: str | int,
    pred_grid: Sequence[Sequence[int]],
    actual_grid: Sequence[Sequence[int]],
    step_index: int = 0,
    max_lines: int = DIAG_MAX_LINES,
) -> str:
    """Format structured simulation mismatch between predicted and actual grid states."""
    diff = compute_grid_frame_diff(
        [list(r) for r in pred_grid],
        [list(r) for r in actual_grid],
    ) if pred_grid and actual_grid else {}

    lines = [
        f"[SIMULATION MISMATCH at Step {step_index}]: Action {action}",
        f"  Total discrepancy cells: {diff.get('changed_cell_count', 0)}",
    ]

    # Sample cell differences
    sample_diffs: list[str] = []
    h = min(len(pred_grid), len(actual_grid))
    w = min(len(pred_grid[0]), len(actual_grid[0])) if h > 0 else 0
    for r in range(h):
        for c in range(w):
            if pred_grid[r][c] != actual_grid[r][c]:
                sample_diffs.append(
                    f"  Cell ({r}, {c}): predicted Color {pred_grid[r][c]}, observed Color {actual_grid[r][c]}"
                )
                if len(sample_diffs) >= 4:
                    break
        if len(sample_diffs) >= 4:
            break

    lines.extend(sample_diffs)

    # Note movements or appearance/disappearance
    if diff.get("moved"):
        lines.append(f"  Moved entities detected: {len(diff['moved'])}")
    if diff.get("disappeared"):
        lines.append(f"  Entities disappeared/absorbed: {len(diff['disappeared'])}")
    if diff.get("appeared"):
        lines.append(f"  Entities appeared/spawned: {len(diff['appeared'])}")

    lines.append("  Lesson: World model simulation diverged from reality. Re-evaluate action effect.")
    return filter_diagnostic_lines("\n".join(lines), max_lines=max_lines)


def format_counterexample_diagnostic(
    claim_id: str,
    predicate: Any,
    transition_idx: int,
    expected: Any,
    observed: Any,
    max_lines: int = DIAG_MAX_LINES,
) -> str:
    """Format structured claim falsification counterexample."""
    raw = DIAGNOSTIC_COUNTEREXAMPLE_TEMPLATE.format(
        claim_id=claim_id,
        predicate=predicate,
        transition_idx=transition_idx,
        expected=expected,
        observed=observed,
    )
    return filter_diagnostic_lines(raw, max_lines=max_lines)


def format_goal_violation_diagnostic(
    goal_id: str,
    kind: str,
    color: int | None = None,
    target: Any = None,
    step_index: int = 0,
    level: int = 0,
    prior_victory_diff: str = "",
    max_lines: int = DIAG_MAX_LINES,
) -> str:
    """Format structured goal insufficiency / violation diagnostic."""
    lines = [
        f"[GOAL INSUFFICIENT at Step {step_index} (Level {level})]: Goal {goal_id} ({kind})",
        f"  Target spec: color={color}, target={target}",
        "  Condition was satisfied, but level did NOT finish.",
    ]
    if prior_victory_diff:
        lines.append(f"  Comparison with prior victory: {prior_victory_diff}")
    lines.append("  Recommendation: Active hypothesis is insufficient to explain level victory.")
    return filter_diagnostic_lines("\n".join(lines), max_lines=max_lines)


def format_session_diagnostic(session: Any, max_lines: int = DIAG_MAX_LINES) -> str:
    """Format high-level state diagnostic from an active UndSession."""
    if session is None:
        return "DIAGNOSTIC: No active session."
    status = session.status() if hasattr(session, "status") else {}
    lines = [
        f"DIAGNOSTIC (Level {session.level}, Step {session.step_index}):",
        f"  History transitions: {len(session.history)}",
        f"  Claims confirmed: {status.get('confirmed_claims', 0)}, refuted: {status.get('refuted_claims', 0)}",
    ]
    if hasattr(session, "timer") and session.timer.has_timer:
        lines.append(f"  Timer steps remaining: ~{session.timer.steps_remaining}")
    if hasattr(session, "overlay") and hasattr(session.overlay, "_edges"):
        lines.append(f"  Observed edges in overlay: {len(session.overlay._edges)}")
    if hasattr(session, "shadow_verifier") and getattr(session.shadow_verifier, "divergences", None):
        shadow_msg = session.shadow_verifier.format_diagnostic(max_lines=3)
        if shadow_msg:
            lines.append(f"  {shadow_msg}")
    if hasattr(session, "breakers") and getattr(session.breakers, "is_tripped", False):
        warn_msg = session.breakers.format_warning()
        if warn_msg:
            lines.append(f"  {warn_msg}")
    return filter_diagnostic_lines("\n".join(lines), max_lines=max_lines)


# Convenient alias
build_bounded_diagnostic = format_session_diagnostic

