"""CONTRACT: Normalization and validation of actions across Duck and ARC-AGI-3 engines (Rules 04, 05).

Provides bidirectional mapping between semantic Duck action strings ('UP', 'DOWN', etc.)
and environment action identifiers ('ACTION1'..'ACTION7'), plus UNDO availability checks.
"""
from __future__ import annotations

import os
from typing import Any

from inference.und.config.platform_facts import GAMES_WITH_UNDO

RESET_ACTION_ID: str = "RESET"
COORDINATE_ACTION_ID: str = "ACTION6"
UNDO_ACTION_ID: str = "ACTION7"

VECTOR_ACTION_IDS: tuple[str, ...] = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
NON_VECTOR_ACTION_IDS: tuple[str, ...] = ("ACTION5", COORDINATE_ACTION_ID, UNDO_ACTION_ID)
LEGAL_ACTION_IDS: tuple[str, ...] = VECTOR_ACTION_IDS + NON_VECTOR_ACTION_IDS
DISCRETE_ACTION_IDS: tuple[str, ...] = tuple(
    action_id for action_id in LEGAL_ACTION_IDS if action_id != COORDINATE_ACTION_ID
)

ACTION_VECTORS: dict[str, tuple[int, int]] = {
    "ACTION1": (-1, 0),
    "ACTION2": (1, 0),
    "ACTION3": (0, -1),
    "ACTION4": (0, 1),
}

import re

# Semantic action mapping (Duck <-> Engine)
DUCK_TO_ENGINE_MAP: dict[str, str] = {
    "UP": "ACTION1",
    "DOWN": "ACTION2",
    "LEFT": "ACTION3",
    "RIGHT": "ACTION4",
    "SPACE": "ACTION5",
    "MOUSE": "ACTION6",
    "CLICK": "ACTION6",
    "ACTION7": "ACTION7",
    "UNDO": "ACTION7",
    "RESET": "RESET",
}

ENGINE_TO_DUCK_MAP: dict[str, str] = {
    "ACTION1": "UP",
    "ACTION2": "DOWN",
    "ACTION3": "LEFT",
    "ACTION4": "RIGHT",
    "ACTION5": "SPACE",
    "ACTION6": "MOUSE",
    "ACTION7": "ACTION7",
    "RESET": "RESET",
}

_ACTION_COORDS_RE = re.compile(
    r"^([A-Z0-9_]+)\s*\(\s*(.*)\s*\)$",
    re.IGNORECASE,
)


def parse_referenced_action_id(text: Any) -> str:
    """Return the first canonical action referenced by a description or identifier."""
    if not isinstance(text, str):
        return ""
    match = re.search(r"\bACTION[1-7]\b", text, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    match = re.search(r"\bRESET\b", text, re.IGNORECASE)
    if match:
        return "RESET"
    for duck_act in ("UP", "DOWN", "LEFT", "RIGHT", "SPACE", "MOUSE", "CLICK", "UNDO"):
        if re.search(rf"\b{duck_act}\b", text, re.IGNORECASE):
            return DUCK_TO_ENGINE_MAP.get(duck_act, "")
    match = re.search(r"\baction\s*([1-7])\b", text, re.IGNORECASE)
    if match:
        return f"ACTION{match.group(1)}"
    return ""


def is_undo_supported(game_id: str, expose_undo: bool | None = None) -> bool:
    """Check whether ACTION7 (UNDO) is supported for the given game.

    Requires BOTH:
    1. The game engine supports ACTION7 (one of the 6 audited games).
    2. The EXPOSE_UNDO environment flag is enabled (or explicitly passed as True).
    """
    if expose_undo is None:
        flag_val = os.getenv("EXPOSE_UNDO", "off").lower()
        expose_undo = flag_val in ("on", "1", "true")

    if not expose_undo:
        return False

    clean_game = game_id.split("-")[0].strip().lower()
    return clean_game in GAMES_WITH_UNDO


def normalize_duck_action(action: str | dict[str, Any]) -> dict[str, Any]:
    """Normalize arbitrary user/agent action input into canonical Duck action dictionary."""
    if isinstance(action, str):
        act_str = action.strip()
        coords_match = _ACTION_COORDS_RE.match(act_str)
        if coords_match:
            base_name = coords_match.group(1).upper()
            args_str = coords_match.group(2).strip()
            if base_name in ("MOUSE", "CLICK", "ACTION6"):
                canonical_name = "MOUSE"
            elif base_name in ENGINE_TO_DUCK_MAP:
                canonical_name = ENGINE_TO_DUCK_MAP[base_name]
            elif base_name in DUCK_TO_ENGINE_MAP:
                canonical_name = base_name
            else:
                raise ValueError(f"Unknown action string: {action!r}")

            res: dict[str, Any] = {"action": canonical_name}
            if canonical_name == "MOUSE":
                named = dict(re.findall(r"(row|col|r|c|x|y)\s*=\s*(-?\d+)", args_str, re.IGNORECASE))
                row = named.get("row") or named.get("r") or named.get("y")
                col = named.get("col") or named.get("c") or named.get("x")
                if row is None and col is None:
                    pos = re.findall(r"-?\d+", args_str)
                    if len(pos) >= 2:
                        row, col = pos[0], pos[1]
                if row is not None:
                    res["row"] = int(row)
                if col is not None:
                    res["col"] = int(col)
            return res

        act_name = act_str.upper()
        if act_name == "UNDO":
            act_name = "ACTION7"
        elif act_name == "CLICK":
            act_name = "MOUSE"

        if act_name in ENGINE_TO_DUCK_MAP:
            canonical_name = ENGINE_TO_DUCK_MAP[act_name]
        elif act_name in DUCK_TO_ENGINE_MAP:
            canonical_name = act_name
        else:
            raise ValueError(f"Unknown action string: {action!r}")
        return {"action": canonical_name}

    if isinstance(action, dict):
        raw_name = str(action.get("action") or action.get("id") or "").strip().upper()
        if not raw_name:
            raise ValueError("Action dict is missing an 'action' or 'id' field")
        if raw_name == "UNDO":
            raw_name = "ACTION7"
        elif raw_name == "CLICK":
            raw_name = "MOUSE"
        canonical_name = ENGINE_TO_DUCK_MAP.get(raw_name, raw_name)
        result: dict[str, Any] = {"action": canonical_name}

        # Normalize coordinate data for MOUSE / ACTION6
        if canonical_name == "MOUSE":
            row = action.get("row") if "row" in action else action.get("y")
            col = action.get("col") if "col" in action else action.get("x")
            if row is not None:
                result["row"] = int(row)
            if col is not None:
                result["col"] = int(col)
        return result

    raise TypeError(f"Action must be str or dict, got {type(action).__name__}")


def to_engine_action(action: str | dict[str, Any]) -> dict[str, Any]:
    """Convert Duck action representation to environment engine format (e.g., ACTION1..7)."""
    norm = normalize_duck_action(action)
    duck_name = norm["action"]
    engine_id = DUCK_TO_ENGINE_MAP.get(duck_name, duck_name)

    engine_data: dict[str, Any] = {}
    if engine_id == "ACTION6":
        # Engine expects x (col) and y (row)
        if "col" in norm:
            engine_data["x"] = norm["col"]
        if "row" in norm:
            engine_data["y"] = norm["row"]

    return {
        "id": engine_id,
        "data": engine_data,
    }


def from_engine_action(action_id: str | int, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert engine action format (ACTION1..7 or 0/RESET) to canonical Duck action dictionary."""
    if isinstance(action_id, int):
        if action_id == 0:
            return {"action": "RESET"}
        act_key = f"ACTION{action_id}"
    else:
        act_key = str(action_id).strip().upper()
        if act_key in ("0", "ACTION0"):
            return {"action": "RESET"}

    duck_name = ENGINE_TO_DUCK_MAP.get(act_key, act_key)
    res: dict[str, Any] = {"action": duck_name}
    if duck_name == "MOUSE" and data:
        if "x" in data:
            res["col"] = int(data["x"])
        if "y" in data:
            res["row"] = int(data["y"])
    return res
