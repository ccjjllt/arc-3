"""World model simulator utilities for ARC-AGI-3 sandbox.

Stdlib-only pure Python module. Embedded into the isolated sandbox runner.
Provides:
- compare_grids: Compares frames/grids excluding outer HUD/timer border.
- check_sim: Verifies sim_fn against past transition history.
- search: Performs breadth-first search in simulator state space.
- SimFrame: Lightweight frame view for simulated boards.
"""
import collections
from typing import Any, Callable, Optional, Sequence

ARC_COLOR_CHARS = "WwgGcBMPRbSYOrNp"
_CHAR_TO_INDEX = {c: i for i, c in enumerate(ARC_COLOR_CHARS)}


class SimFrame:
    """Lightweight frame representation for simulated states."""

    def __init__(self, grid: Sequence[Sequence[Any]], *, step: int = 0, level: int = 0):
        self._grid = [list(row) for row in grid]
        self.shape = (len(self._grid), len(self._grid[0])) if self._grid else (0, 0)
        self.step = step
        self.level = level
        self._ascii: Optional[str] = None
        self._segmentation: Optional[dict[str, Any]] = None

    @property
    def grid(self) -> list[list[Any]]:
        return self._grid

    @property
    def ascii(self) -> str:
        if self._ascii is None:
            lines = []
            for row in self._grid:
                chars = []
                for val in row:
                    if isinstance(val, int) and 0 <= val < len(ARC_COLOR_CHARS):
                        chars.append(ARC_COLOR_CHARS[val])
                    elif isinstance(val, str) and val:
                        chars.append(val[0])
                    else:
                        chars.append("?")
                lines.append("".join(chars))
            self._ascii = "\n".join(lines)
        return self._ascii

    def get(self, row: int, col: int, default: Any = None) -> Any:
        if 0 <= row < self.shape[0] and 0 <= col < self.shape[1]:
            return self._grid[row][col]
        return default

    def copy(self) -> "SimFrame":
        return SimFrame([list(r) for r in self._grid], step=self.step, level=self.level)

    def __str__(self) -> str:
        return f"SimFrame(level={self.level}, step={self.step}, shape={self.shape[0]}x{self.shape[1]})"

    __repr__ = __str__


def extract_grid(obj: Any) -> list[list[Any]]:
    """Extract a 2D list from a FrameView, SimFrame, string, or list of lists/strings."""
    if obj is None:
        return []
    if hasattr(obj, "_grid") and obj._grid is not None:
        return [list(r) for r in obj._grid]
    if hasattr(obj, "grid") and obj.grid is not None:
        return [list(r) for r in obj.grid]
    if isinstance(obj, str):
        lines = [line.strip() for line in obj.strip().splitlines() if line.strip()]
        return [list(line) for line in lines]
    if isinstance(obj, (list, tuple)):
        if not obj:
            return []
        if isinstance(obj[0], str):
            return [list(line) for line in obj]
        if isinstance(obj[0], (list, tuple)):
            return [list(r) for r in obj]
    return []


def _cell_equal(c1: Any, c2: Any) -> bool:
    if c1 == c2:
        return True
    if isinstance(c1, int) and isinstance(c2, str) and len(c2) == 1:
        idx = _CHAR_TO_INDEX.get(c2)
        return idx is not None and idx == c1
    if isinstance(c2, int) and isinstance(c1, str) and len(c1) == 1:
        idx = _CHAR_TO_INDEX.get(c1)
        return idx is not None and idx == c2
    return False


def _hash_grid_interior(grid: Sequence[Sequence[Any]], border: int = 4) -> tuple:
    """Create a hashable tuple representation of grid interior."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    if rows <= 2 * border or cols <= 2 * border:
        r_start, r_end = 0, rows
        c_start, c_end = 0, cols
    else:
        r_start, r_end = border, rows - border
        c_start, c_end = border, cols - border

    result = []
    for r in range(r_start, r_end):
        row_vals = []
        for c in range(c_start, c_end):
            val = grid[r][c]
            # normalize int/str
            if isinstance(val, int) and 0 <= val < len(ARC_COLOR_CHARS):
                val = ARC_COLOR_CHARS[val]
            row_vals.append(val)
        result.append(tuple(row_vals))
    return tuple(result)


def compare_grids(
    actual: Any,
    predicted: Any,
    border: int = 4,
    max_diffs: int = 5,
    base_frame: Any = None,
) -> dict[str, Any]:
    """Compare actual frame/grid with predicted frame/grid.

    Ignores border cells (default 4) where timer/HUD bars typically change.
    Supports predicted as FrameView, 2D grid, ASCII string, or dict of {(r, c): val}.
    """
    act_grid = extract_grid(actual)
    if not act_grid:
        return {"match": False, "error": "Actual frame has empty grid."}

    # Handle sparse changes dict: {(r, c): color} or {"(r, c)": color}
    if isinstance(predicted, dict) and not hasattr(predicted, "_grid"):
        base_grid = extract_grid(base_frame) if base_frame is not None else [list(r) for r in act_grid]
        pred_grid = [list(r) for r in base_grid]
        for key, val in predicted.items():
            if isinstance(key, (tuple, list)) and len(key) == 2:
                r, c = int(key[0]), int(key[1])
            elif isinstance(key, str):
                parts = key.strip("()[] ").split(",")
                if len(parts) == 2:
                    try:
                        r, c = int(parts[0]), int(parts[1])
                    except ValueError:
                        continue
                else:
                    continue
            else:
                continue
            if 0 <= r < len(pred_grid) and 0 <= c < len(pred_grid[0]):
                pred_grid[r][c] = val
    else:
        pred_grid = extract_grid(predicted)

    if not pred_grid:
        return {"match": False, "error": "Predicted state produced empty grid."}

    rows_a, cols_a = len(act_grid), len(act_grid[0])
    rows_p, cols_p = len(pred_grid), len(pred_grid[0])

    if rows_a != rows_p or cols_a != cols_p:
        return {
            "match": False,
            "diff_count": -1,
            "note": f"Grid shapes differ: actual ({rows_a}x{cols_a}) vs predicted ({rows_p}x{cols_p})",
            "sample_diffs": [],
        }

    if rows_a <= 2 * border or cols_a <= 2 * border:
        r_start, r_end = 0, rows_a
        c_start, c_end = 0, cols_a
    else:
        r_start, r_end = border, rows_a - border
        c_start, c_end = border, cols_a - border

    diff_count = 0
    diff_samples: list[dict[str, Any]] = []

    for r in range(r_start, r_end):
        for c in range(c_start, c_end):
            act_val = act_grid[r][c]
            pred_val = pred_grid[r][c]
            if not _cell_equal(act_val, pred_val):
                diff_count += 1
                if len(diff_samples) < max_diffs:
                    diff_samples.append({
                        "pos": [r, c],
                        "expected": pred_val,
                        "actual": act_val,
                    })

    return {
        "match": diff_count == 0,
        "diff_count": diff_count,
        "sample_diffs": diff_samples,
    }


def check_sim(
    sim_fn: Callable[[Any, str], Any],
    transitions: Sequence[Any],
    border: int = 4,
    max_transitions: int = 25,
    max_diffs: int = 3,
) -> dict[str, Any]:
    """Test sim_fn against past transition history.

    Filters out resets, automatic transitions, and cross-level transitions.
    Returns accuracy and compact details of mismatches.
    """
    valid_transitions = []
    for t in transitions or []:
        action = getattr(t, "action", None)
        if not action or action == "RESET":
            continue
        result = getattr(t, "result", None)
        if isinstance(result, dict) and result.get("automatic"):
            continue
        before = getattr(t, "before_frame", None)
        after = getattr(t, "after_frame", None)
        if before is None or after is None:
            continue
        if getattr(before, "level", None) != getattr(after, "level", None):
            continue
        valid_transitions.append(t)

    if not valid_transitions:
        return {"checked": 0, "note": "No applicable transitions found to verify."}

    # Evaluate the most recent valid transitions
    recent = valid_transitions[-max_transitions:]
    matches = 0
    mismatches: list[dict[str, Any]] = []

    for t in recent:
        action_name = getattr(t, "action", "")
        before = t.before_frame
        after = t.after_frame
        step_num = getattr(after, "step", None)
        try:
            pred = sim_fn(before, action_name)
        except Exception as exc:
            mismatches.append({
                "action": action_name,
                "step": step_num,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        cmp = compare_grids(after, pred, border=border, max_diffs=max_diffs, base_frame=before)
        if cmp.get("match"):
            matches += 1
        else:
            mismatches.append({
                "action": action_name,
                "step": step_num,
                "diff_count": cmp.get("diff_count", 0),
                "samples": cmp.get("sample_diffs", []),
            })

    total = len(recent)
    accuracy = round(matches / total, 3) if total > 0 else 1.0

    return {
        "checked": total,
        "matches": matches,
        "accuracy": accuracy,
        "mismatches": mismatches[:5],
    }


def search(
    start_frame: Any,
    sim_fn: Callable[[Any, str], Any],
    goal_fn: Callable[[Any], bool],
    valid_actions: Optional[Sequence[str]] = None,
    max_depth: int = 15,
    max_states: int = 1500,
    is_dead_fn: Optional[Callable[[Any], bool]] = None,
    border: int = 4,
) -> dict[str, Any]:
    """Breadth-first search in simulator state space.

    Returns the shortest sequence of actions leading to goal_fn(state) == True.
    """
    actions_to_try = list(valid_actions) if valid_actions else ["UP", "DOWN", "LEFT", "RIGHT", "SPACE"]

    try:
        if goal_fn(start_frame):
            return {"found": True, "actions": [], "depth": 0, "visited": 1}
    except Exception:
        pass

    start_grid = extract_grid(start_frame)
    if not start_grid:
        return {"found": False, "reason": "invalid_start_frame", "actions": []}

    start_hash = _hash_grid_interior(start_grid, border=border)
    queue = collections.deque([(start_frame, [])])
    visited = {start_hash}

    while queue:
        curr_frame, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for act in actions_to_try:
            try:
                next_state = sim_fn(curr_frame, act)
            except Exception:
                continue

            if next_state is None:
                continue

            if is_dead_fn is not None:
                try:
                    if is_dead_fn(next_state):
                        continue
                except Exception:
                    pass

            next_grid = extract_grid(next_state)
            if not next_grid:
                continue

            h = _hash_grid_interior(next_grid, border=border)
            if h in visited:
                continue
            visited.add(h)

            new_path = path + [act]

            try:
                if goal_fn(next_state):
                    return {
                        "found": True,
                        "actions": new_path,
                        "depth": len(new_path),
                        "visited": len(visited),
                    }
            except Exception:
                pass

            if len(visited) >= max_states:
                return {
                    "found": False,
                    "reason": "max_states_reached",
                    "actions": [],
                    "visited": len(visited),
                    "max_depth": max_depth,
                }

            # Wrap in SimFrame if it's a raw grid/dict so subsequent steps have frame interface
            if isinstance(next_state, (list, tuple, str)):
                state_for_queue = SimFrame(next_grid, step=len(new_path))
            else:
                state_for_queue = next_state

            queue.append((state_for_queue, new_path))

    return {
        "found": False,
        "reason": "exhausted",
        "actions": [],
        "visited": len(visited),
        "max_depth": max_depth,
    }
