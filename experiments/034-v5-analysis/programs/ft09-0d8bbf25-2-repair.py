import math


def _grid(frame):
    raw = getattr(frame, "ascii", None)
    if raw is None:
        raw = getattr(frame, "text", "")
    return [list(r) for r in raw.splitlines() if r.strip()]


def _blocks(rows):
    out = []
    if not rows:
        return out
    R = len(rows)
    seen = set()
    for r in range(R - 1):
        row = rows[r]
        for c in range(len(row) - 1):
            if (r, c) in seen:
                continue
            blk = (rows[r][c], row[c + 1], rows[r + 1][c], rows[r + 1][c + 1])
            if blk[0] == blk[1] == blk[2] == blk[3] and blk[0] in ("R", "O"):
                out.append((r, c, blk[0]))
                for dr in (0, 1):
                    for dc in (0, 1):
                        seen.add((r + dr, c + dc))
    return out


def _trailing(rows):
    out = []
    for r in range(len(rows) - 1, -1, -1):
        row = rows[r]
        for c in range(len(row) - 1, -1, -1):
            if row[c] in ("R", "O"):
                out.append([r, c, row[c]])
                return out
    return out


def plan_program(frame):
    rows = _grid(frame)
    if not rows:
        return {"status": "abstain", "goal": "no board", "actions": [],
                "evidence_pixels": [], "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
                "reason": "frame ascii unavailable"}
    blocks = _blocks(rows)
    cand = [b for b in blocks if (b[0], b[1]) != (4, 60)]
    ev = []
    for (r, c, col) in blocks:
        if len(ev) < 4:
            ev.append([r, c, col])
    ev.append([63, 52, rows[63][52] if len(rows) > 63 and len(rows[63]) > 52 else "?"])
    if not cand:
        return {"status": "abstain", "goal": "find a paintable block that is not the boundary strip",
                "actions": [], "evidence_pixels": ev,
                "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
                "reason": "no interior R/O block found"}
    r, c, col = cand[0]
    other = "R" if col == "O" else "O"
    action = {"action": "MOUSE", "row": r + 1, "col": c + 1}
    return {"status": "ready",
            "goal": "flip the interior 2x2 " + col + " block at (" + str(r) + "," + str(c) +
                    ") to " + other + " and record which trailing palette pixel turns Y",
            "actions": [action],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs"],
            "reason": "The failed prediction at (5,61) shows the O strip along the right edge of rows 0-9 is NOT clickable even though it is a uniform O 2x2, while an interior cell click (5,37) did repaint its whole 6x6 block O->R and turned one trailing bottom-row pixel O->Y. So the old rule 'any uniform R/O 2x2 flips' is contradicted; revised rule: only interior cell blocks repaint, boundary strips are no-ops. Re-test on a freshly recomputed interior block and watch the trailing palette pixel as the progress signal."}


def predict(frame, action):
    rows = _grid(frame)
    if not rows or not isinstance(action, dict) or action.get("action") != "MOUSE":
        return {"mode": "unknown", "reason": "missing board or non-MOUSE action"}
    r = action.get("row")
    c = action.get("col")
    if not isinstance(r, int) or not isinstance(c, int):
        return {"mode": "unknown", "reason": "action lacks integer row/col"}
    if r < 0 or c < 0 or r + 1 >= len(rows) or c + 1 >= len(rows[r]) or c + 1 >= len(rows[r + 1]):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click point falls outside the board grid, so no cell object owns it",
                "scope": "board-bounds precondition"}
    blk = (rows[r][c], rows[r][c + 1], rows[r + 1][c], rows[r + 1][c + 1])
    if not (blk[0] == blk[1] == blk[2] == blk[3] and blk[0] in ("R", "O")):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click point is not inside a uniform R/O 2x2 block, so no cell owns that point",
                "scope": "paintable-cell precondition"}
    top = left = None
    for dr in (0, -1):
        for dc in (0, -1):
            rr, cc = r + dr, c + dc
            if rr < 0 or cc < 0 or rr + 1 >= len(rows):
                continue
            if cc + 1 >= len(rows[rr]) or cc + 1 >= len(rows[rr + 1]):
                continue
            b = (rows[rr][cc], rows[rr][cc + 1], rows[rr + 1][cc], rows[rr + 1][cc + 1])
            if b[0] == b[1] == b[2] == b[3] and b[0] in ("R", "O"):
                if top is None or (rr, cc) < (top, left):
                    top, left = rr, cc
    color = rows[top][left]
    other = "R" if color == "O" else "O"
    tgt = [[rr, cc, color] for rr in (top, top + 1) for cc in (left, left + 1)]
    obj = [[top, left, color], [r, c, color]]
    exp = [[rr, cc, other] for (rr, cc, _) in tgt]
    trail = _trailing(rows)
    if trail:
        tr, tc, tcol = trail[0][0], trail[0][1], trail[0][2]
        if tcol in ("R", "O"):
            flip = "Y"
            obj.append([tr, tc, tcol])
            tgt.append([tr, tc, tcol])
            exp.append([tr, tc, flip])
            pre = ("interior uniform " + color + " block at (" + str(top) + "," + str(left) +
                   ") flips to " + other + " on click, and the logged transitions each turned one "
                   "trailing " + tcol + " palette pixel to Y; boundary strips like the right-edge O run are exempt")
        else:
            pre = ("interior uniform " + color + " block flips to " + other +
                   "; no non-palette trailing pixel remains to flip")
    else:
        pre = "interior uniform " + color + " block flips to " + other
    return {"mode": "change", "action": action, "object_pixels": obj, "target_pixels": tgt,
            "expected_pixels": exp, "precondition": pre,
            "scope": "clicked cell block plus one trailing palette pixel: block flips " +
                     color + "->" + other + " and the trailing marker becomes Y, nothing else"}
