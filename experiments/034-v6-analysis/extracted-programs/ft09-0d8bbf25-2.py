import heapq

CELL_H = 8
CELL_W = 8
MIN_CELL = 24


def _grid(frame):
    ascii_text = getattr(frame, "ascii", None)
    if ascii_text:
        return [list(row) for row in ascii_text.split("\n")]
    raw = getattr(frame, "grid", None)
    if raw:
        return [list(row) for row in raw]
    return [list(row) for row in list(frame)]


def _within(grid, row, col):
    return 0 <= row < len(grid) and 0 <= col < len(grid[0])


def _cells(grid):
    rows = len(grid)
    cols = len(grid[0])
    seen = [[False] * cols for _ in range(rows)]
    found = []
    for r0 in range(0, rows - CELL_H + 1, CELL_H):
        for c0 in range(0, cols - CELL_W + 1, CELL_W):
            if seen[r0][c0]:
                continue
            color = grid[r0][c0]
            if color in ("c", " ", "."):
                continue
            stack = [(r0, c0)]
            seen[r0][c0] = True
            blob = []
            while stack:
                r, c = stack.pop()
                blob.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if not _within(grid, nr, nc) or seen[nr][nc]:
                        continue
                    if grid[nr][nc] != color:
                        continue
                    if nr < r0 or nc < c0:
                        continue
                    if nr > r0 + 3 * CELL_H or nc > c0 + 3 * CELL_W:
                        continue
                    seen[nr][nc] = True
                    stack.append((nr, nc))
            if len(blob) < MIN_CELL:
                continue
            rs = [p[0] for p in blob]
            cs = [p[1] for p in blob]
            rmin, rmax = min(rs), max(rs)
            cmin, cmax = min(cs), max(cs)
            if rmax - rmin < 4 or cmax - cmin < 4:
                continue
            area = (rmax - rmin + 1) * (cmax - cmin + 1)
            if area == 0 or len(blob) / float(area) < 0.85:
                continue
            found.append({"color": color, "r0": rmin, "r1": rmax,
                          "c0": cmin, "c1": cmax, "pixels": len(blob)})
    return found


def _cell_map(cells):
    mapping = {}
    for cell in cells:
        mapping[((cell["r0"] + cell["r1"]) // 2,
                 (cell["c0"] + cell["c1"]) // 2)] = cell
    return mapping


def _legend(grid):
    rows = len(grid)
    cols = len(grid[0])
    for c in range(cols - 1, -1, -1):
        for r in range(rows):
            if grid[r][c] == "Y":
                return grid[r][c - 1] if c > 0 else None
    return None


def _patterns(grid, cell_map):
    rows = len(grid)
    cols = len(grid[0])
    out = []
    for r in range(rows):
        for c in range(cols):
            ch = grid[r][c]
            if ch not in ("W", "g"):
                continue
            if (r, c) in cell_map:
                continue
            if _within(grid, r - 1, c) and grid[r - 1][c] in ("W", "g"):
                continue
            if _within(grid, r, c - 1) and grid[r][c - 1] in ("W", "g"):
                continue
            rr = r
            while rr + 1 < rows and grid[rr + 1][c] in ("W", "g"):
                rr += 1
            cc = c
            while cc + 1 < cols and grid[r][cc + 1] in ("W", "g"):
                cc += 1
            if (rr - r + 1) * (cc - c + 1) < 9:
                continue
            center = grid[(r + rr) // 2][(c + cc) // 2]
            if center not in ("R", "O"):
                continue
            out.append({"r0": r, "c0": c, "r1": rr, "c1": cc, "center": center})
    return out


def _subsymbol(grid, pat, sr, sc):
    rows = pat["r1"] - pat["r0"] + 1
    cols = pat["c1"] - pat["c0"] + 1
    r = pat["r0"] + (2 * sr + 1) * rows // 6
    c = pat["c0"] + (2 * sc + 1) * cols // 6
    return grid[r][c]


def _targets(grid, cell_map, pats, key):
    want = {}
    for pat in pats:
        rows = pat["r1"] - pat["r0"] + 1
        cols = pat["c1"] - pat["c0"] + 1
        cr = pat["r0"] + rows // 2
        cc = pat["c0"] + cols // 2
        center = grid[cr][cc]
        other = "O" if center == "R" else "R"
        for sr in range(3):
            for sc in range(3):
                if sr == 1 and sc == 1:
                    continue
                rr = pat["r0"] + (2 * sr + 1) * rows // 6
                cc2 = pat["c0"] + (2 * sc + 1) * cols // 6
                near = None
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        hit = cell_map.get((rr + dr, cc2 + dc))
                        if hit is not None:
                            near = hit
                            break
                    if near is not None:
                        break
                if near is None:
                    continue
                sym = _subsymbol(grid, pat, sr, sc)
                if sym == "W":
                    col = center
                elif sym == "g":
                    col = other
                else:
                    continue
                keyc = ((near["r0"] + near["r1"]) // 2,
                        (near["c0"] + near["c1"]) // 2)
                prev = want.get(keyc)
                if prev is None:
                    want[keyc] = col
                elif prev[1] != col:
                    want[keyc] = (prev[1], col)
    return want


def _analyze(frame):
    grid = _grid(frame)
    cells = _cells(grid)
    cell_map = _cell_map(cells)
    pats = _patterns(grid, cell_map)
    key = _legend(grid)
    want = _targets(grid, cell_map, pats, key)
    conflicts = [k for k, v in want.items() if isinstance(v, tuple)]
    mism = [k for k, v in want.items()
            if not isinstance(v, tuple) and cell_map[k]["color"] != v]
    return {"grid": grid, "cells": cells, "cell_map": cell_map,
            "pats": pats, "key": key, "want": want,
            "conflicts": conflicts, "mism": mism}


def plan_program(frame):
    try:
        info = _analyze(frame)
    except Exception as exc:
        return {"status": "abstain", "goal": "recompute board cells and legends",
                "actions": [], "evidence_pixels": [],
                "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs", "b"],
                "reason": "analysis failed: %s" % (exc,)}
    grid = info["grid"]
    cell_map = info["cell_map"]
    want = info["want"]
    mism = info["mism"]
    conflicts = info["conflicts"]
    ev = []
    for pat in info["pats"]:
        ev.append([pat["r0"] + (pat["r1"] - pat["r0"]) // 2,
                   pat["c0"] + (pat["c1"] - pat["c0"]) // 2, pat["center"]])
    for keyc in mism[:6]:
        ev.append([keyc[0], keyc[1], cell_map[keyc]["color"]])
    goal = ("legend-consistent board: %d cells, %d legend blocks, %d cells "
            "disagreeing with their legend symbols, %d conflicting cells"
            % (len(cell_map), len(info["pats"]), len(mism), len(conflicts)))
    if not info["pats"]:
        return {"status": "abstain", "goal": goal, "actions": [],
                "evidence_pixels": ev,
                "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs", "b"],
                "reason": "no legend blocks found on this frame"}
    if not mism:
        return {"status": "completed", "goal": goal, "actions": [],
                "evidence_pixels": ev,
                "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs", "b"],
                "reason": "every legend-covered cell already matches the "
                          "legend-derived color; local target reached"}
    # rank mismatches: prefer cells asserted by a single legend block
    def score(keyc):
        votes = 0
        for pat in info["pats"]:
            rows = pat["r1"] - pat["r0"] + 1
            cols = pat["c1"] - pat["c0"] + 1
            for sr in range(3):
                for sc in range(3):
                    if sr == 1 and sc == 1:
                        continue
                    rr = pat["r0"] + (2 * sr + 1) * rows // 6
                    cc2 = pat["c0"] + (2 * sc + 1) * cols // 6
                    if abs(rr - keyc[0]) <= 1 and abs(cc2 - keyc[1]) <= 1:
                        votes += 1
        return (votes, keyc)

    ordered = sorted(mism, key=score)
    actions = []
    for keyc in ordered[:2]:
        actions.append({"action": "MOUSE", "row": keyc[0], "col": keyc[1]})
    return {"status": "ready", "goal": goal, "actions": actions,
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "rs", "cs", "b"],
            "reason": "click cells whose current colour contradicts the "
                      "W/g legend symbol (W->block centre colour, g->other "
                      "colour); two observed clicks each recoloured exactly "
                      "one 6x6 cell block and advanced the yellow bar"}


def predict(frame, action):
    try:
        info = _analyze(frame)
    except Exception as exc:
        return {"mode": "unknown", "reason": "analysis failed: %s" % (exc,)}
    grid = info["grid"]
    cell_map = info["cell_map"]
    want = info["want"]
    if not action or action.get("action") != "MOUSE":
        return {"mode": "unknown",
                "reason": "only MOUSE cell clicks have a supported effect"}
    row = action.get("row")
    col = action.get("col")
    hit = None
    for keyc, cell in cell_map.items():
        if cell["r0"] <= row <= cell["r1"] and cell["c0"] <= col <= cell["c1"]:
            hit = (keyc, cell)
            break
    if hit is None:
        return {"mode": "noop", "action": action, "object_pixels": [],
                "target_pixels": [], "expected_pixels": [],
                "precondition": "click lands on background/legend bar, not on "
                                "a 6x6 cell block, so no cell can change",
                "scope": "confirms cell blocks are the only clickable objects"}
    keyc, cell = hit
    obj = []
    for r in range(cell["r0"], cell["r1"] + 1):
        for c in range(cell["c0"], cell["c1"] + 1):
            obj.append([r, c, grid[r][c]])
    tgt = []
    exp = []
    for pat in info["pats"]:
        for r in range(pat["r0"], pat["r1"] + 1):
            for c in range(pat["c0"], pat["c1"] + 1):
                tgt.append([r, c, grid[r][c]])
    cur = cell["color"]
    other = "O" if cur == "R" else "R"
    if keyc in want and not isinstance(want[keyc], tuple):
        exp_color = want[keyc]
        why = ("legend symbol at this cell demands %s; click recolours the "
               "cell block, and one yellow bar pixel advances" % exp_color)
    else:
        exp_color = other
        why = ("cell is legend-free or legend-conflicted; the observed "
               "effect of a cell click is a two-tone swap")
    for r, c, _ in obj:
        exp.append([r, c, exp_color])
    if not exp:
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": tgt, "expected_pixels": [],
                "precondition": "cell block has no pixels to recolour",
                "scope": "cell block footprint"}
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tgt, "expected_pixels": exp,
            "precondition": why,
            "scope": "the clicked cell block changes colour; legend blocks "
                     "and other cells must stay unchanged"}
