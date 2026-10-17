"""CONTRACT: Context Collapse & Checkpointing for ARC-AGI-3 Hybrid Agent (Rules 01, 04, 05).

Provides atomic context collapse (_collapse_to_checkpoint):
- Replaces runaway turn history with distilled checkpoint at level transition or NULL streak.
- Preserves prompt prefix / system prompt immutability for KV-cache reuse.
- Bounded token footprint: Knowledge Card (<= 400 tok), Mechanics Digest (<= 500 tok),
  Diagnostic (<= 12 lines).
- Idempotent: repeated collapses without intervening actions produce identical state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inference.und.config.thresholds import COLLAPSE_NULL_STREAK
from inference.und.diag import build_bounded_diagnostic
from inference.und.session import UndSession


@dataclass
class CollapseResult:
    """Result of context collapse evaluation and transformation."""

    collapsed: bool
    reason: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    history_dropped_count: int = 0
    card_text: str = ""
    digest_text: str = ""
    diag_text: str = ""


def is_checkpoint_message(msg: dict[str, Any]) -> bool:
    """Determine if a message is an UND checkpoint marker."""
    if not isinstance(msg, dict):
        return False
    if msg.get("_und_checkpoint") or msg.get("_control_kind") == "checkpoint":
        return True
    content = msg.get("content", "")
    if isinstance(content, str):
        if "[WORLD MODEL CHECKPOINT" in content:
            return True
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and "[WORLD MODEL CHECKPOINT" in str(part.get("text", "")):
                return True
    return False


def should_collapse(
    level_changed: bool,
    null_streak: int,
    streak_threshold: int = COLLAPSE_NULL_STREAK,
    already_collapsed: bool = False,
) -> tuple[bool, str]:
    """Evaluate whether context history should collapse to a checkpoint."""
    if already_collapsed:
        return False, "idempotent_skip"
    if level_changed:
        return True, "level_transition"
    if null_streak >= streak_threshold:
        return True, "null_streak"
    return False, "no_trigger"


def build_checkpoint_messages(
    session: UndSession | None = None,
    current_frame: Any = None,
    level: int = 0,
    reason: str = "",
) -> list[dict[str, Any]]:
    """Build atomic 2-turn [user, assistant] checkpoint representation."""
    lvl = level if level != 0 else (session.level if session is not None else 0)
    if session is not None and level != 0 and session.level != level:
        session.level = level

    if session is not None:
        card_text = session.card(format="text")
        digest_text = session.digest()
        diag_text = build_bounded_diagnostic(session)
    else:
        card_text = "### KNOWLEDGE CARD\n(No active world model session)"
        digest_text = "=== MECHANICS DIGEST ===\n(No mechanics observed)"
        diag_text = "DIAGNOSTIC: None"

    user_req = (
        f"[WORLD MODEL CHECKPOINT REQUEST]\n"
        f"Level: {lvl}. Trigger reason: {reason or 'checkpoint'}.\n"
        f"Consolidate verified knowledge card, mechanics digest, and state diagnostics."
    )
    asst_resp = (
        f"[WORLD MODEL CHECKPOINT RESTORED]\n\n"
        f"{card_text}\n\n"
        f"{digest_text}\n\n"
        f"{diag_text}"
    )

    user_msg: dict[str, Any] = {
        "role": "user",
        "content": user_req,
        "_und_checkpoint": True,
        "_control_kind": "checkpoint",
    }
    asst_msg: dict[str, Any] = {
        "role": "assistant",
        "content": asst_resp,
        "_und_checkpoint": True,
        "_control_kind": "checkpoint",
    }
    return [user_msg, asst_msg]


def collapse_history(
    history_messages: list[dict[str, Any]],
    session: UndSession | None = None,
    reason: str = "",
    current_frame: Any = None,
    level: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Atomic collapse of history messages into checkpoint pair.

    Returns:
        (new_history_messages, dropped_message_count)
    """
    # Check idempotence: if history already contains ONLY this checkpoint, don't duplicate
    if (
        len(history_messages) == 2
        and is_checkpoint_message(history_messages[0])
        and is_checkpoint_message(history_messages[1])
    ):
        return list(history_messages), 0

    checkpoint_msgs = build_checkpoint_messages(
        session=session,
        current_frame=current_frame,
        level=level,
        reason=reason,
    )

    dropped_count = len(history_messages)
    if session is not None:
        session.telemetry.log_event(
            "context_collapse",
            {
                "reason": reason,
                "dropped_messages": dropped_count,
                "level": level or session.level,
            },
            level=session.level,
            step_index=session.step_index,
        )
    return checkpoint_msgs, dropped_count
