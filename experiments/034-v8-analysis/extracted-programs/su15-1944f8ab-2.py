def _grid(frame):
    a = getattr(frame, "ascii", None)
    if a is None:
        try:
            a = frame["ascii"]
        except Exception:
            return []
    if not isinstance(a, str):
        try:
            a = "\n".join("".join(r) for r in a)
        except Exception:
            return []
    return [list(r) for r in a.split("\n")]


def _pt(g, r, c):
    if 0 <= r < len(g):
        row = g[r]
        if 0 <= c < len(row):
            return row[c]
    return None


def _pockets(g):
    out = []
    for r in range(10, len(g) - 1):
        row = g[r]
        c = 0
        n = len(row)
        while c < n:
            if row[c] == "B":
                c0 = c
                while c < n and row[c] == "B":
                    c += 1
                if c - c0 >= 7:
                    out.append((r, (c0 + c - 1) // 2))
            else:
                c += 1
    return out


def _target(g):
    pk = _pockets(g)
    if not pk:
        return None, []
    rows = [r for r, c in pk]
    band = [p for p in pk if abs(p[0] - max(rows)) <= 6]
    if not band:
        band = [(max(rows), pk[-1][1])]
    return max(band), band


def _knight(a, b):
    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    if dr == 1 and dc == 2:
        return True
    if dr == 2 and dc == 1:
        return True
    return False


def _pieces(g, r0=10, r1=62):
    seen = [[False] * 64 for _ in range(len(g))]
    out = []
    for r in range(r0, min(r1, len(g) - 1) + 1):
        for c in range(len(g[r])):
            ch = g[r][c]
            if ch == "B" or ch is None or seen[r][c]:
                continue
            stack = [(r, c)]
            comp = []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if r0 <= ny <= r1 and 0 <= nx < len(g[ny]):
                        if not seen[ny][nx] and g[ny][nx] == ch:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            out.append((ch, comp))
    return out


def _anchor(comp):
    if len(comp) == 1:
        return comp[0]
    best = None
    for (r, c) in comp:
        s = (r * 2 + c, r, c)
        if best is None or s < best:
            best = s
    return (best[1], best[2])


def _knight_reachable(comps, start):
    cells = [a for a in comps if a != start]
    frontier = [start]
    seen = {start}
    while frontier:
        cur = frontier.pop()
        for nxt in cells:
            if nxt in seen:
                continue
            if _knight(cur, nxt):
                seen.add(nxt)
                frontier.append(nxt)
    return seen


def _candidates(g):
    goal, band = _target(g)
    if goal is None:
        return None, [], []
    comps = []
    for ch, comp in _pieces(g):
        comps.append(_anchor(comp))
    uniq = []
    for a in comps:
        if a not in uniq:
            uniq.append(a)
    reach = _knight_reachable(uniq, goal)
    cands = [a for a in uniq if a in reach and a != goal]
    cands.sort(key=lambda p: (abs(p[0] - goal[0]) + abs(p[1] - goal[1]), p))
    return goal, band, cands


def _pocket_footprint(band):
    pts = []
    if not band:
        return pts
    rows = [r for r, c in band]
    cols = [c for r, c in band]
    r0, r1 = min(rows), max(rows)
    c0, c1 = min(cols) - 3, min(cols) + 3
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            pts.append((r, c))
    return pts


def plan_program(frame):
    g = _grid(frame)
    goal, band, cands = _candidates(g)
    if goal is None:
        return {"status": "abstain", "goal": "no blue pocket target found",
                "actions": [], "evidence_pixels": [], "replaces": ["route"],
                "reason": "cannot locate a pocket-shaped target in the solid field"}
    gr, gc = goal
    pick = None
    for a in cands:
        if a[0] > 8:
            pick = a
            break
    if pick is None:
        return {"status": "abstain",
                "goal": "pocket target at row %d col %d exists but no reachable "
                        "piece component was found" % (gr, gc),
                "actions": [], "evidence_pixels": [],
                "replaces": ["route"],
                "reason": "no knight-reachable component to move; guessing a "
                          "screen coordinate has no rule support"}
    pr, pc = pick
    ch = _pt(g, pr, pc)
    act = {"action": "MOUSE", "row": pr, "col": pc}
    fp = _pocket_footprint(band)
    ev = [[r, c, _pt(g, r, c)] for (r, c) in fp]
    ev += [[pr, pc, ch]]
    return {"status": "ready",
            "goal": "level-5 pocket target at row %d col %d (blue pocket rows "
                    "%d-%d); nearest knight-reachable %s piece at (%d,%d) is "
                    "the mover candidate" % (gr, gc, min(r for r, _ in band),
                                             max(r for r, _ in band), ch, pr, pc),
            "actions": [act],
            "evidence_pixels": ev,
            "replaces": ["route", "click", "invaders", "state", "alive",
                         "noop", "safe", "safe2", "safe3", "dots", "pcs"],
            "reason": "The paused route used level-4 coordinates and a Y piece "
                      "that no longer exists, so it is stale. In this frame the "
                      "only pocket-shaped region in the solid field is rows "
                      "11-19 around col 32, matching the spot whose click "
                      "completed level 4. Selecting the nearest component that "
                      "is knight-connected to that pocket tests the "
                      "piece-movement rule directly: a click on a piece should "
                      "move it toward the pocket, while a click on empty blue "
                      "field was already shown to do nothing."}


def predict(frame, action):
    g = _grid(frame)
    ad = {}
    try:
        ad = dict(action.get("action_data") or {})
    except Exception:
        ad = {}
    r = ad.get("row", action.get("row"))
    c = ad.get("col", action.get("col"))
    goal, band, cands = _candidates(g)
    if goal is None or r is None or c is None:
        return {"mode": "unknown",
                "reason": "missing click coordinate or pocket target"}
    ch = _pt(g, r, c)
    fp = _pocket_footprint(band)
    if ch == "B" or (r, c) not in cands:
        obj = [[r, c, _pt(g, r, c)]]
        tar = [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in fp]
        exp = [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in fp] + obj
        return {"mode": "noop", "action": action,
                "object_pixels": obj, "target_pixels": tar,
                "expected_pixels": exp,
                "precondition": "the clicked cell is solid blue field or a "
                                "component not knight-connected to the pocket, "
                                "so no mover is engaged",
                "scope": "level target pocket; expects no board or level change"}
    obj = [[r, c, ch]]
    tar = [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in fp]
    exp = [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in fp] + obj
    return {"mode": "change", "action": action,
            "object_pixels": obj, "target_pixels": tar,
            "expected_pixels": exp,
            "precondition": "the clicked cell belongs to a piece component that "
                            "is knight-connected to the pocket target, so the "
                            "mover rule should relocate it one knight step "
                            "toward the pocket",
            "scope": "active piece object and the pocket target: expect the "
                     "piece pixels to change colour at (%d,%d) and reappear at "
                     "a knight-step cell nearer row %d col %d; if the frame is "
                     "byte-identical the piece-movement rule is contradicted"
                     % (r, c, goal[0], goal[1])}
