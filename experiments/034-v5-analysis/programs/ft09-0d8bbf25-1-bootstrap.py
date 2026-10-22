import math


def _grid(frame):
    raw = getattr(frame, "ascii", None)
    if raw is None:
        raw = getattr(frame, "text", "")
    rows = [list(r) for r in raw.splitlines() if r.strip()]
    return rows


def _cell_top_left(rows):
    best = None
    for r in range(len(rows) - 1):
        row = rows[r]
        for c in range(len(row) - 1):
            if row[c] != "O":
                continue
            if row[c + 1] != "O":
                continue
            if r + 1 >= len(rows) or len(rows[r + 1]) <= c + 1:
                continue
            if rows[r + 1][c] != "O" or rows[r + 1][c + 1] != "O":
                continue
            key = (r, c)
            if best is None or key < best:
                best = key
    return best


def _palette(rows):
    if not rows:
        return ("R", "O")
    top = rows[0]
    idx = None
    for i, ch in enumerate(top):
        if ch != top[0]:
            idx = i
            break
    if idx is None:
        return (top[0], "O")
    return (top[idx], "O")


def _clickable(rows, r, c):
    if r < 0 or c < 0 or r + 1 >= len(rows):
        return False
    if len(rows[r]) <= c + 1 or len(rows[r + 1]) <= c + 1:
        return False
    block = (rows[r][c], rows[r][c + 1], rows[r + 1][c], rows[r + 1][c + 1])
    return block[0] == block[1] == block[2] == block[3] and block[0] in ("R", "O")


def plan_program(frame):
    rows = _grid(frame)
    ev = []
    if not rows:
        return {"status": "abstain", "goal": "no board", "actions": [],
                "evidence_pixels": ev, "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
                "reason": "frame ascii unavailable"}
    tl = _cell_top_left(rows)
    if tl is None:
        return {"status": "abstain", "goal": "locate a paintable cell", "actions": [],
                "evidence_pixels": ev, "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
                "reason": "no 2x2 cell block found"}
    color = rows[tl[0]][tl[1]]
    other = "R" if color == "O" else "O"
    ev.append([tl[0], tl[1], color])
    ev.append([tl[0] + 1, tl[1] + 1, color])
    action = {"action": "MOUSE", "row": tl[0] + 1, "col": tl[1] + 1}
    return {"status": "ready",
            "goal": "toggle the 2x2 " + color + " cell block at (" + str(tl[0]) + "," + str(tl[1]) +
                    ") to " + other + " and confirm the click->block-repaint map still holds",
            "actions": [action],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
            "reason": "Both logged MOUSE clicks each repainted exactly one 6x6 pixel block between R and O and set one trailing palette pixel to Y, so the recovered map is click inside a uniform 2x2 cell -> whole cell flips color. Re-testing the map on a freshly recomputed cell block (not a stored coordinate) verifies the toggle rule before any target-driven painting."}


def predict(frame, action):
    rows = _grid(frame)
    if not rows or not isinstance(action, dict) or action.get("action") != "MOUSE":
        return {"mode": "unknown", "reason": "missing board or non-MOUSE action"}
    r = action.get("row")
    c = action.get("col")
    if not isinstance(r, int) or not isinstance(c, int):
        return {"mode": "unknown", "reason": "action lacks integer row/col"}
    if not _clickable(rows, r, c):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click lands outside a uniform R/O 2x2 cell block, so no cell owns that point and no repaint is due",
                "scope": "paintable-cell precondition"}
    top, left = None, None
    for dr in (0, -1):
        for dc in (0, -1):
            rr, cc = r + dr, c + dc
            if rr < 0 or cc < 0 or rr + 1 >= len(rows):
                continue
            if len(rows[rr]) <= cc + 1 or len(rows[rr + 1]) <= cc + 1:
                continue
            blk = (rows[rr][cc], rows[rr][cc + 1], rows[rr + 1][cc], rows[rr + 1][cc + 1])
            if blk[0] == blk[1] == blk[2] == blk[3] and blk[0] in ("R", "O"):
                if top is None or (rr, cc) < (top, left):
                    top, left = rr, cc
    color = rows[top][left]
    other = "R" if color == "O" else "O"
    obj = [[top, left, color], [top + 1, left + 1, color]]
    tgt = []
    for rr in (top, top + 1):
        for cc in (left, left + 1):
            tgt.append([rr, cc, color])
    exp = [[rr, cc, other] for (rr, cc, _) in tgt]
    return {"mode": "change", "action": action,
            "object_pixels": obj, "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "the click point lies inside a uniform " + color +
                            " cell block, and the logged transitions show such a click repaints that whole block to " + other,
            "scope": "the clicked cell object: its block must flip " + color + "->" + other + " and nothing else"}
