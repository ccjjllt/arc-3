"""CONTRACT: Action guards and interior state hashing preventing fatal loops and repeated deaths (Rule 01, 04, 05).

Ported from LCLD V10.8 (action_guards.py):
1. compute_interior_grid_hash: Deterministic SHA-256 interior hash, cropping border HUD / timers.
2. action_signature: Canonical string signature preserving coordinates for MOUSE/ACTION6.
3. DeathActionGuard: Intercepts fatal actions known to cause GAME_OVER from bit-identical states.
4. NoopRepeatGuard: Intercepts actions known to produce zero interior gameplay changes.
"""
from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any, Mapping, Sequence

_DISPLAY_COORDS_RE = re.compile(
    r"^([A-Z0-9_]+)\(\s*(?:ROW\s*=\s*)?(-?\d+)\s*,\s*(?:COL\s*=\s*)?(-?\d+)\s*\)$",
    re.IGNORECASE,
)


def action_signature(action: Any) -> str:
    """Compute stable string signature for an action.

    Coordinates for MOUSE / CLICK / ACTION6 are preserved in row, col or x, y format.
    Accepts dicts, strings, integers, and tuples.
    """
    if isinstance(action, Mapping):
        name = str(
            action.get("action")
            or action.get("action_id")
            or action.get("id")
            or action.get("name")
            or ""
        ).strip().upper()
        data = action.get("data")
        if isinstance(data, Mapping):
            row = data.get("row", data.get("y"))
            col = data.get("col", data.get("x"))
            if row is not None or col is not None:
                return f"{name}({row},{col})"
        row = action.get("row", action.get("y"))
        col = action.get("col", action.get("x"))
        if row is not None or col is not None:
            return f"{name}({row},{col})"
        return name or "ACTION1"

    act_str = str(action or "").strip().upper()
    match = _DISPLAY_COORDS_RE.match(act_str)
    if match:
        return f"{match.group(1).upper()}({match.group(2)},{match.group(3)})"
    return act_str or "ACTION1"


def compute_interior_grid_hash(grid: Sequence[Sequence[int]] | None, border_margin: int | None = None) -> str:
    """Compute deterministic SHA-256 hash of interior grid, cropping outer border HUD."""
    if not grid or not grid[0]:
        return hashlib.sha256(b"").hexdigest()

    h = len(grid)
    w = len(grid[0])
    if border_margin is not None:
        border = max(0, int(border_margin))
    else:
        border = max(0, min(4, h // 6, w // 6)) if (h >= 6 and w >= 6) else 0

    interior_rows = []
    for r in range(border, h - border):
        row = grid[r]
        interior_rows.append("".join(format(int(c), "x") for c in row[border:w - border]))

    content = "\n".join(interior_rows).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class NoopRepeatGuard:
    """Tracks state-action combinations that produced no interior gameplay change."""

    def __init__(self, max_states: int = 512) -> None:
        self.max_states = max_states
        self.current_level: Any = None
        self._noop_actions: OrderedDict[str, set[str]] = OrderedDict()

    def note_level(self, level: Any) -> None:
        """Reset records upon advancing to a new level layout."""
        if level != self.current_level:
            self.current_level = level
            self._noop_actions.clear()

    def record_noop(self, interior_hash: str, action_sig: str) -> None:
        """Record an action as an empirical no-op from this interior state."""
        if not interior_hash or not action_sig:
            return
        if interior_hash not in self._noop_actions:
            if len(self._noop_actions) >= self.max_states:
                self._noop_actions.popitem(last=False)
            self._noop_actions[interior_hash] = set()
        self._noop_actions[interior_hash].add(action_sig)

    def is_known_noop(self, interior_hash: str, action_sig: str) -> bool:
        """Check whether action is a confirmed no-op in this state."""
        if not interior_hash or not action_sig:
            return False
        return action_sig in self._noop_actions.get(interior_hash, ())

    def filter_available_actions(self, interior_hash: str, available_actions: Sequence[Any]) -> list[Any]:
        """Prune known no-ops, preserving at least one action if all would be pruned."""
        known = self._noop_actions.get(interior_hash, set())
        if not known:
            return list(available_actions)
        filtered = [a for a in available_actions if action_signature(a) not in known]
        return filtered if filtered else list(available_actions)


class DeathActionGuard:
    """Tracks state-action combinations that resulted in fatal GAME_OVER."""

    def __init__(self, max_states: int = 512) -> None:
        self.max_states = max_states
        self.current_level: Any = None
        self._fatal_actions: OrderedDict[str, set[str]] = OrderedDict()

    def note_level(self, level: Any) -> None:
        """Reset records upon advancing to a new level layout."""
        if level != self.current_level:
            self.current_level = level
            self._fatal_actions.clear()

    def record_death(self, interior_hash: str, action_sig: str) -> None:
        """Record an action as fatal from this interior state."""
        if not interior_hash or not action_sig:
            return
        if interior_hash not in self._fatal_actions:
            if len(self._fatal_actions) >= self.max_states:
                self._fatal_actions.popitem(last=False)
            self._fatal_actions[interior_hash] = set()
        self._fatal_actions[interior_hash].add(action_sig)

    def is_known_fatal(self, interior_hash: str, action_sig: str) -> bool:
        """Check whether action is confirmed fatal in this state."""
        if not interior_hash or not action_sig:
            return False
        return action_sig in self._fatal_actions.get(interior_hash, ())

    def filter_safe_actions(self, interior_hash: str, available_actions: Sequence[Any]) -> list[Any]:
        """Prune known fatal actions, preserving at least one action if all would be pruned."""
        fatal = self._fatal_actions.get(interior_hash, set())
        if not fatal:
            return list(available_actions)
        filtered = [a for a in available_actions if action_signature(a) not in fatal]
        return filtered if filtered else list(available_actions)
