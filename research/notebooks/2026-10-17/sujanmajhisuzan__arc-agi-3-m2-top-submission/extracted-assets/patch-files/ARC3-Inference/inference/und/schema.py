"""CONTRACT: Single source of truth for RPC wire schemas and serializable types (Rules 04, 05).

All messages crossing the sandbox host boundary must adhere to the definitions
in this file. Both host and sandbox-client import these structures.
Contains complete JSON schemas and validators for all 12 registered operations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from inference.und.config.thresholds import (
    RPC_REPLY_MAX_BYTES as _CFG_RPC_REPLY_MAX_BYTES,
    SANDBOX_CALL_DEADLINE_S as _CFG_SANDBOX_CALL_DEADLINE_S,
)

SCHEMA_VERSION: str = "1.0.0"
RPC_REPLY_MAX_BYTES: int = _CFG_RPC_REPLY_MAX_BYTES
RPC_REQUEST_MAX_BYTES: int = 32768
SANDBOX_CALL_DEADLINE_S: float = _CFG_SANDBOX_CALL_DEADLINE_S

# Registered RPC operations (Rule 05, Section 3)
REGISTERED_OPERATIONS: frozenset[str] = frozenset({
    "digest",
    "card",
    "status",
    "claim",
    "goal",
    "plan",
    "begin_step",
    "end_step",
    "probe",
    "undo",
    "budget",
    "hook_register",
})

# Complete JSON Schemas for each operation's args and result
OPERATION_SCHEMAS: dict[str, dict[str, Any]] = {
    "digest": {
        "args": {
            "type": "object",
            "properties": {"max_tokens": {"type": ["integer", "null"], "minimum": 50, "maximum": 4000}},
            "additionalProperties": False,
        },
        "result": {"type": ["string", "object"]},
    },
    "card": {
        "args": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["text", "json", "markdown", "dict"]},
                "max_tokens": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        "result": {"type": ["string", "object"]},
    },
    "status": {
        "args": {"type": "object", "properties": {}, "additionalProperties": False},
        "result": {"type": "object", "required": ["game_id", "level", "step_index"]},
    },
    "claim": {
        "args": {
            "type": "object",
            "properties": {
                "law": {"type": "string"},
                "subject": {"type": ["array", "null"]},
                "predicate": {"type": ["object", "null"]},
                "kind": {"type": ["string", "null"]},
                "expected": {},
            },
            "required": ["law"],
            "additionalProperties": True,
        },
        "result": {"type": "object", "required": ["registered", "claim_id"]},
    },
    "goal": {
        "args": {
            "type": "object",
            "properties": {
                "goal_type": {"type": "string", "enum": ["target_color", "reach_exit", "eliminate_color", "collect_all", "touch", "reach", "clear_all", "click_all", "custom"]},
                "kind": {"type": "string", "enum": ["target_color", "reach_exit", "eliminate_color", "collect_all", "touch", "reach", "clear_all", "click_all", "custom"]},
                "color": {"type": ["integer", "null"], "minimum": 0, "maximum": 15},
                "target": {},
                "criteria": {"type": ["object", "null"]},
            },
            "additionalProperties": True,
        },
        "result": {"type": "object", "required": ["registered", "goal_id"]},
    },
    "plan": {
        "args": {
            "type": "object",
            "properties": {
                "target": {},
                "color": {"type": ["integer", "null"]},
                "max_depth": {"type": "integer", "minimum": 1, "maximum": 50},
                "strategy": {"type": "string", "enum": ["bfs", "dfs", "greedy", "astar"]},
            },
            "additionalProperties": True,
        },
        "result": {"type": "object", "required": ["actions", "cost"]},
    },
    "begin_step": {
        "args": {
            "type": "object",
            "properties": {
                "action": {"type": ["string", "object"]},
                "category": {"type": "string", "enum": ["manual", "planned", "probe", "recovery", "fallback", "evidence_probe"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        "result": {"type": "object", "required": ["accepted"]},
    },
    "end_step": {
        "args": {"type": "object", "properties": {}, "additionalProperties": False},
        "result": {"type": "object", "required": ["ok", "verdict"]},
    },
    "probe": {
        "args": {
            "type": "object",
            "properties": {
                "action": {"type": ["string", "object"]},
                "hypothesis": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        "result": {"type": "object", "required": ["allowed", "probe_budget_remaining"]},
    },
    "undo": {
        "args": {"type": "object", "properties": {}, "additionalProperties": False},
        "result": {"type": "object", "required": ["supported", "action"]},
    },
    "budget": {
        "args": {"type": "object", "properties": {}, "additionalProperties": False},
        "result": {"type": "object", "required": ["probe_budget_remaining", "timer_present"]},
    },
    "hook_register": {
        "args": {
            "type": "object",
            "properties": {
                "hook_name": {"type": "string"},
                "code": {"type": "string"},
            },
            "required": ["hook_name", "code"],
            "additionalProperties": False,
        },
        "result": {"type": "object", "required": ["registered", "hook_name"]},
    },
}


@dataclass(frozen=True)
class RPCRequest:
    """Wire representation of an RPC request from sandbox to host."""

    op: str
    args: dict[str, Any] = field(default_factory=dict)
    type: str = "und"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "op": self.op, "args": dict(self.args)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass(frozen=True)
class RPCReply:
    """Wire representation of an RPC reply from host to sandbox."""

    ok: bool
    result: Any = None
    error: str | None = None
    type: str = "und_reply"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "ok": self.ok, "result": self.result, "error": self.error}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def validate_rpc_request(data: Any) -> tuple[bool, str | None]:
    """Validate top-level envelope of an RPCRequest."""
    if not isinstance(data, dict):
        return False, "RPC request must be a JSON object"
    if data.get("type") != "und":
        return False, f"Expected request type 'und', got {data.get('type')!r}"
    op = data.get("op")
    if not isinstance(op, str) or not op:
        return False, "RPC request missing non-empty 'op' field"
    if op not in REGISTERED_OPERATIONS:
        return False, f"Unknown RPC operation {op!r}. Must be one of {sorted(REGISTERED_OPERATIONS)}"
    args = data.get("args")
    if args is not None and not isinstance(args, dict):
        return False, "RPC request 'args' must be a JSON object"
    return True, None


def validate_operation_args(op: str, args: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate operation-specific argument types and required properties."""
    schema_info = OPERATION_SCHEMAS.get(op)
    if not schema_info:
        return False, f"No schema registered for operation {op!r}"
    args_schema = schema_info["args"]
    for req in args_schema.get("required", []):
        if req not in args:
            return False, f"Operation {op!r} missing required argument {req!r}"
    if not args_schema.get("additionalProperties", True):
        props = set(args_schema.get("properties", {}).keys())
        for k in args:
            if k not in props:
                return False, f"Operation {op!r} received unexpected argument {k!r}"
    # Value type checks
    if op == "begin_step" and not isinstance(args["action"], (str, dict)):
        return False, "begin_step 'action' must be string or dict"
    if op == "probe" and not isinstance(args["action"], (str, dict)):
        return False, "probe 'action' must be string or dict"
    if op == "goal" and ("goal_type" not in args and "kind" not in args):
        return False, "Operation 'goal' requires 'goal_type' or 'kind'"
    if op == "hook_register" and (not isinstance(args["hook_name"], str) or not isinstance(args["code"], str)):
        return False, "hook_register requires string 'hook_name' and string 'code'"
    return True, None


def validate_operation_result(op: str, result: Any) -> tuple[bool, str | None]:
    """Validate operation-specific result format."""
    schema_info = OPERATION_SCHEMAS.get(op)
    if not schema_info:
        return True, None
    res_schema = schema_info["result"]
    allowed_types = res_schema.get("type")
    if allowed_types:
        types_list = [allowed_types] if isinstance(allowed_types, str) else list(allowed_types)
        valid = False
        for t in types_list:
            if t == "string" and isinstance(result, str):
                valid = True
            elif t == "object" and isinstance(result, dict):
                valid = True
        if not valid:
            return False, f"Operation {op!r} result must match types {types_list}, got {type(result).__name__}"
    if isinstance(result, dict):
        for req in res_schema.get("required", []):
            if req not in result:
                return False, f"Operation {op!r} result missing required key {req!r}"
    return True, None


def validate_rpc_reply(data: Any) -> tuple[bool, str | None]:
    """Validate top-level envelope of an RPCReply."""
    if not isinstance(data, dict):
        return False, "RPC reply must be a JSON object"
    if data.get("type") != "und_reply":
        return False, f"Expected reply type 'und_reply', got {data.get('type')!r}"
    if "ok" not in data or not isinstance(data["ok"], bool):
        return False, "RPC reply missing boolean 'ok' field"
    if not data["ok"] and not data.get("error"):
        return False, "RPC reply with ok=false must provide an 'error' message"
    return True, None


def parse_rpc_request(raw_json: str | bytes) -> RPCRequest:
    """Safely parse wire JSON string into a validated RPCRequest."""
    if len(raw_json) > RPC_REQUEST_MAX_BYTES:
        raise ValueError(f"RPC request size {len(raw_json)} bytes exceeds limit {RPC_REQUEST_MAX_BYTES}")
    data = json.loads(raw_json)
    valid_env, err_env = validate_rpc_request(data)
    if not valid_env:
        raise ValueError(f"Invalid RPC envelope: {err_env}")
    op = str(data["op"])
    args = data.get("args") or {}
    valid_args, err_args = validate_operation_args(op, args)
    if not valid_args:
        raise ValueError(f"Invalid arguments for {op!r}: {err_args}")
    return RPCRequest(op=op, args=args)


def format_rpc_reply(reply: RPCReply, max_bytes: int = RPC_REPLY_MAX_BYTES) -> str:
    """Serialize RPCReply into JSON wire format enforcing byte bounds."""
    text = reply.to_json()
    encoded_len = len(text.encode("utf-8"))
    if encoded_len <= max_bytes:
        return text
    # Size overflow fallback error reply
    fallback = RPCReply(
        ok=False,
        error=f"RPC reply size ({encoded_len} bytes) exceeds limit ({max_bytes} bytes)",
    )
    return fallback.to_json()


def make_error_reply(error: str, op: str | None = None) -> RPCReply:
    """Create an error RPCReply with optional operation context."""
    prefix = f"[{op}] " if op else ""
    return RPCReply(ok=False, error=f"{prefix}{error}".strip())


def make_success_reply(result: Any, op: str | None = None) -> RPCReply:
    """Create a successful RPCReply and validate its structure if operation given."""
    if op:
        valid, err = validate_operation_result(op, result)
        if not valid:
            return RPCReply(ok=False, error=f"Result validation failed for {op!r}: {err}")
    return RPCReply(ok=True, result=result)
