"""CONTRACT: Host-side RPC dispatcher for World Model operations (Rules 04, 05).

Coordinates incoming messages of type 'und' from the sandbox runner:
- Validates requests against schema specifications (inference.und.schema).
- Dispatches to active host-resident UndSession coordinator.
- Catches host exceptions safely without crashing the main solver loop.
- Enforces RPC_REPLY_MAX_BYTES wire size limits.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from inference.und.actions import is_undo_supported
from inference.und.claim_graph import Claim, ClaimStatus
from inference.und.config.thresholds import DEFAULT_THRESHOLDS
from inference.und.schema import (
    RPC_REPLY_MAX_BYTES,
    RPCReply,
    format_rpc_reply,
    make_error_reply,
    make_success_reply,
    validate_operation_args,
    validate_operation_result,
    validate_rpc_request,
)
from inference.und.session import UndSession, get_session
from inference.und.texts import CARD_HEADER_TEMPLATE

logger = logging.getLogger(__name__)


def _dispatch_op(session: UndSession, op: str, args: dict[str, Any]) -> Any:
    """Execute domain logic on UndSession for a validated operation."""
    if op == "digest":
        return session.digest(max_tokens=args.get("max_tokens"))

    if op == "card":
        return session.card(format=str(args.get("format", "text")), max_tokens=args.get("max_tokens"))

    if op == "status":
        return session.status()

    if op == "claim":
        return session.register_claim(
            law=str(args.get("law", "")),
            subject=args.get("subject"),
            predicate=args.get("predicate"),
            kind=args.get("kind"),
            expected=args.get("expected"),
        )

    if op == "goal":
        goal_kind = str(args.get("kind") or args.get("goal_type", "custom"))
        return session.set_goal(
            goal_type=goal_kind,
            color=args.get("color"),
            target=args.get("target"),
            criteria=args.get("criteria"),
        )

    if op == "plan":
        return session.plan(
            target=args.get("target"),
            color=args.get("color"),
            max_depth=int(args.get("max_depth", 20)),
            strategy=str(args.get("strategy", "astar")),
        )

    if op == "begin_step":
        act = str(args.get("action") or "")
        cat = str(args.get("category", "planned"))
        step_res = session.begin_step(action=act, category=cat)
        return {
            "accepted": step_res.get("accepted", True),
            "action": str(act),
            "category": cat,
            "step_index": session.step_index,
            "predicted_hash": step_res.get("predicted_hash"),
        }

    if op == "end_step":
        step_res = session.end_step()
        return {
            "ok": step_res.get("ok", True),
            "verdict": step_res.get("verdict", "MATCH"),
            "brusentsov_verdict": step_res.get("brusentsov_verdict", "FOLLOW" if step_res.get("verdict") == "MATCH" else "NULL"),
            "is_follow": step_res.get("is_follow", step_res.get("verdict") == "MATCH"),
            "is_null": step_res.get("is_null", step_res.get("verdict") == "MISMATCH"),
            "counterexample": step_res.get("counterexample"),
            "predicted_hash": step_res.get("predicted_hash"),
            "actual_hash": step_res.get("actual_hash"),
            "diagnostic": step_res.get("diagnostic", ""),
            "step_index": session.step_index,
        }

    if op == "probe":
        allowed, reason = session.can_probe()
        b_info = session.get_budget()
        return {
            "allowed": allowed,
            "probe_budget_remaining": b_info["probe_budget_remaining"],
            "action": str(args.get("action")),
            "reason": reason,
        }

    if op == "undo":
        supported = is_undo_supported(session.game_id, expose_undo=session.config.expose_undo)
        return {
            "supported": supported,
            "action": "ACTION7" if supported else "",
            "reason": "Supported by game engine" if supported else "Undo not supported or disabled",
        }

    if op == "budget":
        return session.get_budget()

    if op in ("hook_register", "hook"):
        h_name = str(args.get("hook_name", ""))
        h_code = str(args.get("code", ""))
        return session.register_hook(h_name, h_code)

    raise ValueError(f"Unhandled operation: {op!r}")


def handle_und_message(
    message: dict[str, Any],
    session: UndSession | None = None,
    max_bytes: int = RPC_REPLY_MAX_BYTES,
) -> dict[str, Any]:
    """Process an incoming RPC message and return wire-safe reply dictionary."""
    # 1. Validate envelope
    valid_env, err_env = validate_rpc_request(message)
    if not valid_env:
        logger.warning("Rejected invalid RPC request envelope: %s", err_env)
        return make_error_reply(str(err_env)).to_dict()

    op = str(message["op"])
    args = message.get("args") or {}

    # 2. Validate operation arguments
    valid_args, err_args = validate_operation_args(op, args)
    if not valid_args:
        logger.warning("Invalid args for op %s: %s", op, err_args)
        return make_error_reply(str(err_args), op=op).to_dict()

    # 3. Resolve active session
    resolved_session = session
    if resolved_session is None:
        game_id = str(args.get("game_id", ""))
        resolved_session = get_session(game_id)

    if resolved_session is None:
        logger.warning("No active UndSession found for op %s", op)
        return make_error_reply("No active UndSession found for game", op=op).to_dict()

    # 4. Dispatch with error isolation (Rule 05 В§5)
    try:
        raw_result = _dispatch_op(resolved_session, op, args)
        valid_res, err_res = validate_operation_result(op, raw_result)
        if not valid_res:
            logger.error("Operation %s produced invalid result: %s", op, err_res)
            return make_error_reply(f"Result validation failed: {err_res}", op=op).to_dict()

        reply = make_success_reply(raw_result, op=op)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error executing RPC operation %s: %s", op, exc)
        reply = make_error_reply(str(exc), op=op)

    # 5. Format to enforce max byte bounds
    wire_json = format_rpc_reply(reply, max_bytes=max_bytes)
    return json.loads(wire_json)
