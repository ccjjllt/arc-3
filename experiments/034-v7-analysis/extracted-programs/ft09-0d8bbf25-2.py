import math
def cells(frame):
    grid = [list(r) for r in frame.ascii.strip().splitlines()]
    n = len(grid)
    m = len(grid[0]) if grid else 0
    out = []
    for i in range(1, n - 1):
        for j in range(1, m - 1):
            if grid[i][j] in ("R", "O"):
                out.append((i, j, grid[i][j]))
    return out, grid, n, m
def blocks(frame):
    cl, g, n, m = cells(frame)
    seen = set((r, c) for r, c, _ in cl)
    res = []
    for r, c, col in cl:
        if (r, c) not in seen:
            continue
        st = [(r, c)]
        seen.discard((r, c))
        comp = []
        while st:
            a, b = st.pop()
            comp.append((a, b))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                na, nb = a + da, b + db
                if (na, nb) in seen:
                    seen.discard((na, nb))
                    st.append((na, nb))
        res.append((min(a for a, _ in comp), min(b for _, b in comp),
                    max(a for a, _ in comp), max(b for _, b in comp), col, len(comp)))
    return res, g, n, m
def cell_at(g, n, m, r, c):
    if n < 3 or m < 3:
        return None
    if r < 1 or r > n - 2 or c < 1 or c > m - 2:
        return None
    if g[r][c] in ("R", "O"):
        return (r, c)
    return None
def legend(g, r0, c0):
    out = []
    for dr in (0, 1, 2):
        for dc in (0, 1, 2):
            if dr == 1 and dc == 1:
                continue
            out.append(g[r0 + 2 * dr][c0 + 2 * dc])
    return out
def pats(frame):
    cl, g, n, m = cells(frame)
    res = []
    for r, c, col in cl:
        if r + 4 >= n or c + 4 >= m:
            continue
        if g[r + 1][c] != g[r + 1][c + 4]:
            continue
        if g[r][c + 1] != g[r + 4][c + 1]:
            continue
        if g[r + 2][c] != g[r + 2][c + 4]:
            continue
        if g[r][c + 2] != g[r + 4][c + 2]:
            continue
        ring = [g[r + 1][c], g[r][c + 1], g[r][c + 2], g[r + 1][c + 4],
                g[r + 4][c + 2], g[r + 4][c + 1], g[r + 2][c], g[r + 4][c]]
        if any(x not in ("W", "g") for x in ring):
            continue
        res.append((r, c, col, ring))
    return res, g, n, m
def rot90(ring):
    idx = (6, 0, 7, 1, 8, 2, 9, 3, 4)
    return [ring[i - 1] for i in idx]
def rots(ring):
    cur = list(ring)
    res = []
    for _ in range(4):
        res.append(list(cur))
        cur = rot90(cur)
    return res
def conflicts(p, rot, want):
    return sum(1 for s, t in zip(rot, want) if s != t)
def bestrot(p, want):
    return min(((conflicts(p, r, want), i) for i, r in enumerate(rots(p[3]))))[1]
def targets(p, rot):
    return [(p[0] + 2 * d, p[1] + 2 * e)
            for d in (0, 1, 2) for e in (0, 1, 2) if not (d == 1 and e == 1)]
def expand(g, n, m, r0, c0):
    pts = []
    for rr in range(r0, r0 + 6):
        for cc in range(c0, c0 + 6):
            if 0 <= rr < n and 0 <= cc < m:
                pts.append([rr, cc, g[rr][cc]])
    return pts
def plan_program(frame):
    ps, g, n, m = pats(frame)
    ev = [[r, c, ch] for r, c, ch in cells(frame)]
    names = ["r1", "d1", "cc", "cur", "n"]
    if len(ps) < 2:
        return {"status": "abstain", "goal": "no rotatable legend patterns located",
                "actions": [], "evidence_pixels": ev, "replaces": names,
                "reason": "cannot recover pattern layout from this frame"}
    for p in ps:
        want = []
        for d in (0, 1, 2):
            for e in (0, 1, 2):
                if d == 1 and e == 1:
                    continue
                rr, cc = p[0] + 2 * d, p[1] + 2 * e
                want.append(g[rr][cc] if 0 <= rr < n and 0 <= cc < m else "c")
        if min(conflicts(p, r, want) for r in rots(p[3])) > 0:
            ri = bestrot(p, want)
            rot = rots(p[3])[ri]
            tp = []
            for k, sym in enumerate(rot):
                rr, cc = targets(p, rot)[k]
                tp.append([rr, cc, g[rr][cc]])
            goal = ("rotate pattern at rows%d-cols%d center %s by %d steps so its "
                    "W/g legend matches the R/O colours of its 8 neighbour cells"
                    % (p[0], p[1], p[2], ri))
            return {"status": "ready", "goal": goal,
                    "actions": [{"action": "MOUSE", "row": p[0] + 3, "col": p[1] + 3}],
                    "evidence_pixels": ev, "replaces": names,
                    "reason": "clicking the 6x6 legend block cycles its orientation; "
                              "no current orientation explains the surrounding cells, "
                              "so an unsatisfied legend is the outstanding local goal"}
    return {"status": "completed",
            "goal": "every legend block already consistent with its neighbour cells",
            "actions": [], "evidence_pixels": ev, "replaces": names,
            "reason": "all patterns have a zero-conflict orientation; nothing left "
                      "to change locally"}
def predict(frame, action):
    ps, g, n, m = pats(frame)
    ev = cells(frame)
    if action.get("action") != "MOUSE" or n < 3:
        return {"mode": "unknown", "reason": "not a MOUSE action or no grid"}
    r = action.get("row")
    c = action.get("col")
    hit = None
    for p in ps:
        if p[0] <= r <= p[0] + 5 and p[1] <= c <= p[1] + 5:
            hit = p
    if hit is None:
        cell = cell_at(g, n, m, r, c)
        if cell is None:
            return {"mode": "unknown",
                    "reason": "click lands on background, legend or control"}
        rr, cc = cell
        obj = expand(g, n, m, rr - 2, cc - 2)
        cur = g[rr][cc]
        nxt = "O" if cur == "R" else "R"
        return {"mode": "change", "action": action,
                "object_pixels": obj, "target_pixels": obj,
                "expected_pixels": [[rr, cc, nxt]],
                "precondition": "cell %d,%d is %s and toggles to %s on a click" % (rr, cc, cur, nxt),
                "scope": "single R/O cell at %d,%d changes colour, legend blocks untouched" % (rr, cc)}
    tp = expand(g, n, m, hit[0], hit[1])
    exp = [[rr, cc, g[rr][cc]] for rr, cc, _ in tp]
    return {"mode": "noop", "action": action,
            "object_pixels": tp,
            "target_pixels": [[hit[0] + 3, hit[1] + 3, hit[2]]],
            "expected_pixels": exp,
            "precondition": "legend block at rows%d-cols%d is internally consistent "
                            "with its neighbour cells, so clicking its centre is a no-op"
                            % (hit[0], hit[1]),
            "scope": "legend block %d,%d orientation and the R/O cell grid are unchanged"
                     % (hit[0], hit[1])