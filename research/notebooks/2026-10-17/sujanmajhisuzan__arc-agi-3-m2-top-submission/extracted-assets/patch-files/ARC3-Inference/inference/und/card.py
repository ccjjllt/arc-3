"""CONTRACT: Knowledge Card generator for ARC-AGI-3 (Rules 01, 04, 05).

Generates human-readable and structured machine representations of the current
game understanding:
- Confirmed laws (kinematics, walls, hazards, player identity, collectibles).
- Active working hypotheses prioritized by empirical status.
- Refuted rules (counterexample summaries).
- Active goal focus, criteria, and exemplar counts (victories/defeats).
- Timer pressure and remaining exploration budget.
- Bounded to CARD_MAX_TOKENS with deterministic truncation.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from inference.und.claim_graph import Claim, ClaimStatus
from inference.und.config.thresholds import CARD_MAX_TOKENS
from inference.und.texts import (
    CARD_HEADER_TEMPLATE,
    CRITICAL_TIME_PRESSURE_WARNING,
)
from inference.und.timer import TimerStatus

__all__ = [
    "build_knowledge_card",
    "format_claim_summary",
    "format_confirmed_section",
    "format_goal_section",
    "format_hypotheses_section",
    "format_refuted_section",
    "format_timer_section",
]


def format_claim_summary(claim: Any) -> str:
    """Format a single claim into a readable, concise English statement."""
    kind = getattr(claim, "kind", "unknown")
    subj = getattr(claim, "subject", ())
    pred = getattr(claim, "predicate", {})
    if not isinstance(pred, dict):
        pred = {}

    if kind == "action_effect":
        act = subj[0] if subj else "?"
        dy, dx = pred.get("dy", 0), pred.get("dx", 0)
        return f"Action {act} shifts actor by (dy={dy}, dx={dx})"
    if kind == "passability":
        col = subj[0] if subj else "?"
        solid = not pred.get("passable", True) or bool(pred.get("solid", False))
        return f"Color {col} is {'solid wall / impassable' if solid else 'passable'}"
    if kind == "lethal":
        col = subj[0] if subj else "?"
        return f"Color {col} is lethal hazard (defeat on contact)"
    if kind == "controlled":
        col = subj[0] if subj else "?"
        return f"Color {col} is controllable player avatar"
    if kind == "collectible":
        col = subj[0] if subj else "?"
        return f"Color {col} is collectible item (disappears upon contact)"
    if kind == "undo_exact":
        return "ACTION7 (UNDO) perfectly reverts previous move"

    # Fallback to general predicate summary
    details = ", ".join(f"{k}={v}" for k, v in pred.items()) if pred else "active"
    return f"{kind} on {subj}: {details}"


def format_confirmed_section(confirmed: Sequence[Any], is_markdown: bool = False) -> list[str]:
    """Format confirmed laws section."""
    if not confirmed:
        return []
    header = "### Confirmed Laws:" if is_markdown else "[CONFIRMED LAWS]:"
    lines = [f"\n{header}"]
    for c in sorted(confirmed, key=lambda x: str(getattr(x, "id", ""))):
        cid = getattr(c, "id", "?")
        summary = format_claim_summary(c)
        lines.append(f"  + {cid}: {summary}")
    return lines


def format_hypotheses_section(
    hypotheses: Sequence[Any], max_items: int = 5, is_markdown: bool = False
) -> list[str]:
    """Format active hypotheses section bounded to max_items."""
    if not hypotheses:
        return []
    header = "### Active Hypotheses:" if is_markdown else "[ACTIVE HYPOTHESES]:"
    lines = [f"\n{header}"]
    for c in sorted(hypotheses, key=lambda x: str(getattr(x, "id", "")))[:max_items]:
        cid = getattr(c, "id", "?")
        summary = format_claim_summary(c)
        lines.append(f"  ? {cid}: {summary}")
    if len(hypotheses) > max_items:
        lines.append(f"  ... (+{len(hypotheses) - max_items} more unlisted hypotheses)")
    return lines


def format_refuted_section(
    refuted: Sequence[Any], max_items: int = 3, is_markdown: bool = False
) -> list[str]:
    """Format refuted claims section bounded to max_items."""
    if not refuted:
        return []
    header = "### Refuted Rules:" if is_markdown else "[REFUTED RULES]:"
    lines = [f"\n{header}"]
    for c in sorted(refuted, key=lambda x: str(getattr(x, "id", "")))[:max_items]:
        cid = getattr(c, "id", "?")
        summary = format_claim_summary(c)
        lines.append(f"  - {cid}: {summary} (contradicted)")
    if len(refuted) > max_items:
        lines.append(f"  ... (+{len(refuted) - max_items} refuted claims)")
    return lines


def format_goal_section(
    active_goal: dict[str, Any] | None,
    victory_count: int,
    defeat_count: int,
    is_markdown: bool = False,
) -> list[str]:
    """Format active goal and exemplars section."""
    lines: list[str] = []
    if active_goal:
        gtype = active_goal.get("goal_type") or active_goal.get("kind", "unknown")
        gcol = active_goal.get("color")
        gtgt = active_goal.get("target")
        col_str = f"color={gcol}" if gcol is not None else ""
        tgt_str = f"target={gtgt}" if gtgt is not None else ""
        spec = ", ".join(s for s in [col_str, tgt_str] if s)
        spec_info = f" ({spec})" if spec else ""
        if is_markdown:
            lines.append(f"\n### Active Goal: {gtype}{spec_info}")
        else:
            lines.append(f"\n[ACTIVE GOAL]: {gtype}{spec_info}")
    elif victory_count > 0 or defeat_count > 0:
        if is_markdown:
            lines.append("\n### Active Goal: [Undecided / Exploring]")
        else:
            lines.append("\n[ACTIVE GOAL]: [Undecided / Exploring]")

    if lines and (victory_count > 0 or defeat_count > 0):
        lines.append(f"  Exemplars: {victory_count} victory replay(s), {defeat_count} defeat replay(s)")
    return lines


def format_timer_section(timer_stat: TimerStatus, is_markdown: bool = False) -> list[str]:
    """Format timer and action budget section."""
    if not timer_stat.has_timer:
        return []
    header = "### Timer & Action Budget:" if is_markdown else "[TIMER & ACTION BUDGET]:"
    lines = [
        f"\n{header}",
        f"  Remaining Steps: {timer_stat.estimated_remaining_steps} | Probe Budget: {timer_stat.probe_budget_remaining}",
    ]
    if getattr(timer_stat, "is_critical", False):
        warn = CRITICAL_TIME_PRESSURE_WARNING.format(steps_remaining=timer_stat.estimated_remaining_steps)
        lines.append(f"  {warn}")
    return lines


def build_knowledge_card(
    session: Any,
    format: str = "text",
    max_tokens: int | None = None,
) -> str | dict[str, Any]:
    """Build a comprehensive, bounded knowledge card from active session state."""
    level = int(getattr(session, "level", 0))
    cg = getattr(session, "claim_graph", None)
    confirmed = list(cg.confirmed_claims()) if cg and hasattr(cg, "confirmed_claims") else []
    active = list(cg.active_claims()) if cg and hasattr(cg, "active_claims") else []
    hypotheses = [c for c in active if getattr(c, "status", None) == ClaimStatus.UNDECIDED or str(getattr(c, "status", "")) == "?"]
    all_claims: Mapping[str, Claim] = getattr(cg, "claims", {}) if cg else {}
    refuted = [c for c in all_claims.values() if getattr(c, "status", None) == ClaimStatus.MINUS or str(getattr(c, "status", "")) == "-"]

    goal_judge = getattr(session, "goal_judge", None)
    vic_count = len(getattr(goal_judge, "victory_exemplars", [])) if goal_judge else 0
    def_count = len(getattr(goal_judge, "defeat_exemplars", [])) if goal_judge else 0
    current_goal = getattr(session, "current_goal", None)

    timer_tracker = getattr(session, "timer", None)
    probes_used = int(getattr(session, "probes_used_on_level", 0))
    timer_stat = timer_tracker.status(level, probes_used=probes_used) if timer_tracker and hasattr(timer_tracker, "status") else TimerStatus(has_timer=False)
    shadow_verifier = getattr(session, "shadow_verifier", None)

    if format in ("json", "dict"):
        return {
            "level": level,
            "confirmed_count": len(confirmed),
            "hypo_count": len(hypotheses),
            "refuted_count": len(refuted),
            "confirmed_claims": [
                {"id": getattr(c, "id", ""), "kind": getattr(c, "kind", ""), "subject": list(getattr(c, "subject", ())), "predicate": getattr(c, "predicate", {}), "summary": format_claim_summary(c)}
                for c in confirmed
            ],
            "hypotheses": [
                {"id": getattr(c, "id", ""), "kind": getattr(c, "kind", ""), "subject": list(getattr(c, "subject", ())), "predicate": getattr(c, "predicate", {}), "summary": format_claim_summary(c)}
                for c in hypotheses
            ],
            "refuted_claims": [
                {"id": getattr(c, "id", ""), "kind": getattr(c, "kind", ""), "subject": list(getattr(c, "subject", ())), "predicate": getattr(c, "predicate", {}), "summary": format_claim_summary(c)}
                for c in refuted
            ],
            "current_goal": current_goal,
            "victory_exemplars_count": vic_count,
            "defeat_exemplars_count": def_count,
            "timer": timer_stat.to_dict() if hasattr(timer_stat, "to_dict") else {},
            "shadow": shadow_verifier.get_summary() if shadow_verifier is not None and hasattr(shadow_verifier, "get_summary") else {},
        }

    is_md = (format == "markdown")
    if is_md:
        header = f"## ARC-AGI-3 Knowledge Card (Level {level})\nConfirmed Laws: {len(confirmed)} | Active Hypotheses: {len(hypotheses)} | Refuted: {len(refuted)}"
    else:
        header = CARD_HEADER_TEMPLATE.format(level=level, confirmed_count=len(confirmed), hypo_count=len(hypotheses), refuted_count=len(refuted)).strip()

    body_lines = [header]
    body_lines.extend(format_confirmed_section(confirmed, is_markdown=is_md))
    body_lines.extend(format_hypotheses_section(hypotheses, max_items=5, is_markdown=is_md))
    body_lines.extend(format_refuted_section(refuted, max_items=3, is_markdown=is_md))
    body_lines.extend(format_goal_section(current_goal, vic_count, def_count, is_markdown=is_md))
    body_lines.extend(format_timer_section(timer_stat, is_markdown=is_md))

    shadow_verifier = getattr(session, "shadow_verifier", None)
    if shadow_verifier and getattr(shadow_verifier, "divergences", None):
        div_header = "### Shadow Verification Alerts:" if is_md else "[SHADOW VERIFICATION ALERTS]:"
        body_lines.append(f"\n{div_header}")
        for div in shadow_verifier.divergences[:2]:
            body_lines.append(f"  ! {div.claim_id}: {div.kind} contradicted on Level {level}")

    card_text = "\n".join(body_lines)
    budget = max_tokens or CARD_MAX_TOKENS
    char_limit = budget * 4
    if len(card_text) > char_limit:
        card_text = card_text[:char_limit - 30] + "\n[... truncated]"
    return card_text
