import math


def _grid(frame):
    raw = getattr(frame, "ascii", None)
    if raw is None:
        raw = getattr(frame, "ascii_map", None)
    lines = str(raw).splitlines()
    return [list(r) for r in lines]


def _majority(cells):
    counts = {}
    for ch in cells:
        counts[ch] = counts.get(ch, 0) + 1
    best = None
    bestn = -1
    for ch in sorted(counts):
        if counts[ch] > bestn:
            bestn = counts[ch]
            best = ch
    return best


def _blocks(grid):
    nr = len(grid)
    nc = len(grid[0]) if nr else 0
    out = []
    for r0 in range(0, nr - 5, 6):
        for c0 in range(0, nc - 5, 6):
            cells = []
            for rr in range(r0, r0 + 6):
                for cc in range(c0, c0 + 6):
                    cells.append(grid[rr][cc])
            col = _majority(cells)
            n = sum(1 for x in cells if x == col)
            out.append({"r0": r0, "c0": c0, "color": col, "n": n, "cells": cells})
    return out


def _obj_count(blocks):
    return sum(1 for b in blocks if b["n"] >= 30 and b["color"] != "c")


def _board_distinct(blocks):
    s = set()
    for b in blocks:
        if b["n"] >= 30 and b["color"] != "c":
            s.add(b["color"])
    return len(s)


def _relief(blocks, r0, c0, nr, nc):
    gain = 0
    for b in blocks:
        if b["r0"] == r0 and b["c0"] == c0:
            continue
        rr = max(0, b["r0"] - 6)
        cc = max(0, b["c0"] - 6)
        hit = 0
        tot = 0
        for i in range(rr, min(rr + 12, nr)):
            for j in range(cc, min(cc + 12, nc)):
                tot += 1
                if b["r0"] <= i < b["r0"] + 6 and b["c0"] <= j < b["c0"] + 6:
                    hit += 1
                else:
                    if grid_at(blocks, i, j, nr, nc) == b["color"]:
                        hit += 1
        frac = hit / max(1, tot)
        if frac >= 0.9:
            gain += 1
    return gain


def grid_at(blocks, i, j, nr, nc):
    b = blocks[(i // 6) * 6 * 1000 + (j // 6) * 6] if False else None
    return None


def _index(blocks):
    return {(b["r0"], b["c0"]): b for b in blocks}


def _uniform(blocks, r0, c0):
    b = _index(blocks).get((r0, c0))
    if b is None:
        return False
    return b["n"] == 36 and b["color"] != "c"


def _mixed(blocks, r0, c0):
    b = _index(blocks).get((r0, c0))
    if b is None:
        return False
    return 10 <= b["n"] < 36 and b["color"] != "c"


def _rescue(blocks, r0, c0, nr, nc):
    idx = _index(blocks)
    b = idx.get((r0, c0))
    if b is None:
        return 0
    col = b["color"]
    gain = 0
    for dr, dc in ((-6, 0), (6, 0), (0, -6), (0, 6)):
        nb = idx.get((r0 + dr, c0 + dc))
        if nb is None:
            continue
        same = 0
        for rr in range(nb["r0"], min(nb["r0"] + 6, nr)):
            for cc in range(nb["c0"], min(nb["c0"] + 6, nc)):
                if grid_cell(idx, rr, cc, nr, nc) == col:
                    same += 1
        if same >= 20:
            gain += 1
    return gain


def grid_cell(idx, r, c, nr, nc):
    b = idx.get((min(max((r // 6) * 6, 0), 60), min(max((c // 6) * 6, 0), 60)))
    if b is None:
        return "c"
    return b["color"]


def _choose(frame):
    grid = _grid(frame)
    nr = len(grid)
    nc = len(grid[0]) if nr else 0
    blocks = _blocks(grid)
    best = None
    for b in blocks:
        if not _mixed(blocks, b["r0"], b["c0"]):
            continue
        if _uniform(blocks, b["r0"] - 6, b["c0"]):
            key = (2, _obj_count(blocks), -b["r0"] - b["c0"])
        elif _uniform(blocks, b["r0"] + 6, b["c0"]):
            key = (1, _obj_count(blocks), -b["r0"] - b["c0"])
        elif _uniform(blocks, b["r0"], b["c0"] - 6):
            key = (1, _obj_count(blocks), -b["r0"] - b["c0"])
        elif _uniform(blocks, b["r0"], b["c0"] + 6):
            key = (1, _obj_count(blocks), -b["r0"] - b["c0"])
        else:
            continue
        if best is None or key > best[0]:
            best = (key, b)
    if best is not None:
        b = best[1]
        return grid, nr, nc, blocks, b, "rescue"
    for b in blocks:
        if _uniform(blocks, b["r0"], b["c0"]):
            return grid, nr, nc, blocks, b, "plain"
    return grid, nr, nc, blocks, None, "none"


def plan_program(frame):
    grid, nr, nc, blocks, b, kind = _choose(frame)
    if b is None:
        return {"status": "abstain",
                "goal": "no removable uniform 6x6 object block found on this board",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "every 6x6 cell region is background or too fragmented to be a task object"}
    r = min(b["r0"] + 3, nr - 1)
    c = min(b["c0"] + 3, nc - 1)
    ev = []
    for rr in (b["r0"], b["r0"] + 5):
        for cc in (b["c0"], b["c0"] + 5):
            if 0 <= rr < nr and 0 <= cc < nc:
                ev.append([rr, cc, grid[rr][cc]])
    if kind == "rescue":
        goal = ("click the mixed 6x6 region at rows %d-%d cols %d-%d (majority %s, %d/36 matching) "
                "because a same-color uniform 6x6 block sits adjacent to it; that click repaints the "
                "mixed region to %s and restores the board to all-uniform blocks"
                % (b["r0"], b["r0"] + 5, b["c0"], b["c0"] + 5, b["color"], b["n"], b["color"]))
        reason = ("Frozen prediction wrongly assumed only uniform blocks are clickable. Real transitions "
                  "show MOUSE(6,22) and MOUSE(15,21) each repainted a MIXED 6x6 region entirely to its "
                  "majority color (O->R), i.e. clicking a mixed region resolves it to its majority color "
                  "rather than clearing it. So the target is a mixed region adjacent to a same-color block, "
                  "which repairs the fragmentation instead of stranding that block.")
    else:
        goal = ("click the uniform %s 6x6 block at rows %d-%d cols %d-%d to resolve that task object"
                % (b["color"], b["r0"], b["r0"] + 5, b["c0"], b["c0"] + 5))
        reason = ("No mixed region with a same-color neighbour exists, so fall back to a uniform block: "
                  "observed transitions show a click inside a 6x6 region repaints the whole region to a "
                  "single color, so a uniform region simply changes its state.")
    return {"status": "ready", "goal": goal,
            "actions": [{"action": "MOUSE", "row": r, "col": c}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs"],
            "reason": reason}


def predict(frame, action):
    grid = _grid(frame)
    nr = len(grid)
    nc = len(grid[0]) if nr else 0
    try:
        r = int(action.get("row"))
        c = int(action.get("col"))
    except Exception:
        return {"mode": "unknown", "reason": "action lacks integer row/col for MOUSE"}
    if not (0 <= r < nr and 0 <= c < nc):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click outside the %dx%d board addresses no task object" % (nr, nc),
                "scope": "no task object affected"}
    r0 = (r // 6) * 6
    c0 = (c // 6) * 6
    cells = []
    obj = []
    for rr in range(r0, min(r0 + 6, nr)):
        for cc in range(c0, min(c0 + 6, nc)):
            cells.append(grid[rr][cc])
            obj.append([rr, cc, grid[rr][cc]])
    col = _majority(cells)
    n = sum(1 for x in cells if x == col)
    tgt = [[rr, cc, grid[rr][cc]] for rr in range(r0, min(r0 + 6, nr))
           for cc in range(c0, min(c0 + 6, nc))]
    if col == "c" and n >= 30:
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": [[r, c, "c"]], "expected_pixels": obj,
                "precondition": "region at rows %d-%d cols %d-%d is already background 'c' "
                                "(%d/36), so there is no task object to change"
                                % (r0, r0 + 5, c0, c0 + 5, n),
                "scope": "background region offers no observable task consequence"}
    exp = [[rr, cc, col] for rr in range(r0, min(r0 + 6, nr))
           for cc in range(c0, min(c0 + 6, nc))]
    if n == 36:
        pre = ("click inside the uniform %s 6x6 region at rows %d-%d cols %d-%d keeps that "
               "region %s (already single-color)" % (col, r0, r0 + 5, c0, c0 + 5, col))
    else:
        pre = ("click inside the mixed 6x6 region at rows %d-%d cols %d-%d (majority %s, %d/36) "
               "repaints the whole region to its majority color %s, as the two real transitions "
               "showed for the O/R mixed regions at rows 4-9 and 12-17"
               % (r0, r0 + 5, c0, c0 + 5, col, n, col))
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tgt, "expected_pixels": exp, "precondition": pre,
            "scope": "the 6x6 region containing (%d,%d) becomes uniformly %s; observable "
                     "consequence is the region's minority pixels disappearing" % (r, c, col)}
