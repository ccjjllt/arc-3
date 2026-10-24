import collections
def grid_of(frame):
    return [list(r) for r in frame.ascii.splitlines()]
def blocks(g):
    seen = set()
    out = []
    for r, row in enumerate(g):
        for c, ch in enumerate(row):
            if ch in "RWg" and (r, c) not in seen:
                q = collections.deque([(r, c)])
                seen.add((r, c))
                comp = []
                while q:
                    a, b = q.popleft()
                    comp.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if 0 <= na < len(g) and 0 <= nb < len(g[na]):
                            if g[na][nb] in "RWg" and (na, nb) not in seen:
                                seen.add((na, nb))
                                q.append((na, nb))
                out.append((min(a for a, _ in comp), min(b for _, b in comp),
                            max(a for a, _ in comp), max(b for _, b in comp),
                            sorted(comp)))
    return out
def cell6(g, r0, c0):
    pts = []
    for rr in range(r0, r0 + 6):
        for cc in range(c0, c0 + 6):
            if 0 <= rr < len(g) and 0 <= cc < len(g[rr]):
                pts.append((rr, cc))
    return pts
def cell_colors(g, r0, c0):
    cols = set()
    for rr, cc in cell6(g, r0, c0):
        cols.add(g[rr][cc])
    return cols
def pick(g):
    cands = []
    for r0, c0, r1, c1, pts in blocks(g):
        if (r1 - r0 + 1) * (c1 - c0 + 1) > 36:
            continue
        if len(pts) > 36:
            continue
        nr, nc = r0 - 6, c0
        sr, sc = r0 + 6, c0
        w, e = c0 - 6, c0 + 6
        nb = []
        for br, bc in ((nr, nc), (sr, sc), (r0, w), (r0, e)):
            if 0 <= br < len(g) and 0 <= bc < len(g[br]):
                ch = g[br][bc]
                if ch in "RO" and cell_colors(g, br - 2, bc - 2) == {ch}:
                    nb.append((br, bc, ch))
        if len(nb) >= 1:
            cands.append((len(nb), r0, c0, pts, nb))
    if not cands:
        return None
    cands.sort(key=lambda t: (-t[0], t[1], t[2]))
    return cands[0]
def plan_program(frame):
    g = grid_of(frame)
    ev = []
    for r, row in enumerate(g):
        for c, ch in enumerate(row):
            if ch in "RWg":
                ev.append([r, c, ch])
    names = ["r1", "d1", "cc", "cur", "n"]
    p = pick(g)
    if p is None:
        return {"status": "abstain",
                "goal": "no mixed W/g/R pattern cell adjacent to a uniform R/O cell",
                "actions": [], "evidence_pixels": ev, "replaces": names,
                "reason": "cannot recover a pattern cell with a uniform neighbour "
                          "from this frame"}
    n, r0, c0, pts, nb = p
    goal = ("click the 6x6 pattern cell at rows %d-%d cols %d-%d whose interior "
            "mixes W/g/R (centre %d,%d=%s); its uniform neighbour(s) %s are the "
            "colours a cell toggle propagates into"
            % (r0, r0 + 5, c0, c0 + 5, r0 + 3, c0 + 3, g[r0 + 3][c0 + 3],
               [(a, b, ch) for a, b, ch in nb]))
    return {"status": "ready",
            "goal": goal,
            "actions": [{"action": "MOUSE", "row": r0 + 3, "col": c0 + 3}],
            "evidence_pixels": ev, "replaces": names,
            "reason": "observed clicks changed exactly the 36 pixels of one 6x6 "
                      "cell to the clicked cell's base colour plus one bottom-row "
                      "counter pixel; the mixed cell is the only unexplored role "
                      "(pattern rotation vs cell toggle) and one click settles it"}
def predict(frame, action):
    g = grid_of(frame)
    if action.get("action") != "MOUSE" or len(g) < 3:
        return {"mode": "unknown", "reason": "not a MOUSE action or no grid"}
    r = action.get("row")
    c = action.get("col")
    if r is None or c is None:
        return {"mode": "unknown", "reason": "action lacks row/col"}
    if not (0 <= r < len(g) and 0 <= c < len(g[r])):
        return {"mode": "unknown", "reason": "click outside grid"}
    ch = g[r][c]
    if ch == "c":
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, ch]], "target_pixels": [[r, c, ch]],
                "expected_pixels": [[r, c, ch]],
                "precondition": "click on background gap, no task cell there",
                "scope": "no cell or counter pixel should change"}
    r0 = r - 2
    c0 = c - 2
    pts = cell6(g, r0, c0)
    obj = [[a, b, g[a][b]] for a, b in pts]
    if ch in "RO":
        nxt = "O" if ch == "R" else "R"
        exp = [[a, b, nxt] for a, b in pts]
        return {"mode": "change", "action": action,
                "object_pixels": obj, "target_pixels": obj,
                "expected_pixels": exp,
                "precondition": "cell containing %d,%d is uniform %s and a click "
                                "repaints all 36 of its pixels to %s"
                                % (r, c, ch, nxt),
                "scope": "the whole clicked 6x6 cell flips base colour; other "
                         "cells and legend cells keep their pixels"}
    exp = [[a, b, g[a][b]] for a, b in pts]
    return {"mode": "noop", "action": action,
            "object_pixels": obj, "target_pixels": [[r, c, ch]],
            "expected_pixels": exp,
            "precondition": "cell containing %d,%d is a W/g/R pattern, not a "
                            "toggleable R/O cell, so its 36 pixels stay as-is"
                            % (r, c),
            "scope": "pattern cell rows %d-%d cols %d-%d unchanged; distinguishes "
                     "legend-role from cell-role" % (r0, r0 + 5, c0, c0 + 5)}
