import heapq


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
    rows = [r for r, c in _pockets(g)]
    if not rows:
        return None, []
    band = [p for p in _pockets(g) if abs(p[0] - max(rows)) <= 6]
    if not band:
        band = [(max(rows), _pockets(g)[-1][1])]
    return max(band), band


def _knight(a, b):
    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    if dr == 1 and dc == 2:
        return True
    if dr == 2 and dc == 1:
        return True
    return False


def _route(start, goal, cells, limit=60000):
    if start is None or goal is None:
        return []
    if start == goal:
        return []
    openq = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0, start)]
    best = {start: 0}
    prev = {}
    seen = 0
    while openq and seen < limit:
        seen += 1
        _, g0, cur = heapq.heappop(openq)
        if g0 > best.get(cur, 99):
            continue
        if cur == goal:
            path = [cur]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            return path[1:]
        for nxt in cells:
            if not _knight(cur, nxt):
                continue
            ng = g0 + 1
            if ng < best.get(nxt, 99) and ng < 12:
                best[nxt] = ng
                prev[nxt] = cur
                heapq.heappush(openq, (ng + abs(nxt[0] - goal[0]) + abs(nxt[1] - goal[1]), ng, nxt))
    return None


def plan_program(frame):
    g = _grid(frame)
    goal, band = _target(g)
    if goal is None:
        return {"status": "abstain", "goal": "no blue pocket column found",
                "actions": [], "evidence_pixels": [], "replaces": ["route"],
                "reason": "cannot locate level target without pocket geometry"}
    gr, gc = goal
    pts = []
    for rr in (gr - 1, gr, gr + 1):
        for cc in (gc - 1, gc, gc + 1):
            if _pt(g, rr, cc) == "B":
                pts.append((rr, cc))
    if not pts:
        pts = [goal]
    act = {"action": "MOUSE", "row": pts[0][0], "col": pts[0][1]}
    ev = [[r, c, _pt(g, r, c)] for (r, c) in band]
    ev += [[r, c, "S"] for (r, c) in pts]
    return {"status": "ready",
            "goal": "deepest blue pocket (col %d, rows %d-%d) is the level-5 "
                    "target; single MOUSE there tests whether the next frame is "
                    "a fresh level (target consumed) or an invalid-spot no-op" %
                    (gc, min(r for r, _ in band), max(r for r, _ in band)),
            "actions": [act],
            "evidence_pixels": ev,
            "replaces": ["route", "click", "invaders", "state", "alive", "noop", "safe", "safe2", "safe3", "dots", "pcs"],
            "reason": "Level 5 just began after the previous pocket click completed level 4, so the "
                      "paused Y-runner route and its level-4 coordinates are stale. Current frame has "
                      "no Y piece; the only blue pocket column inside the solid field is the widest "
                      "one (rows 11-19, cols 28-36). One click at its centre distinguishes "
                      "target-consumption from a no-op without assuming the merge/chase rules."}


def predict(frame, action):
    g = _grid(frame)
    ad = {}
    try:
        ad = dict(action.get("action_data") or {})
    except Exception:
        ad = {}
    r = ad.get("row", action.get("row"))
    c = ad.get("col", action.get("col"))
    goal, band = _target(g)
    if goal is None or r is None or c is None:
        return {"mode": "unknown", "reason": "missing click coordinate or target pocket"}
    gr, gc = goal
    if abs(r - gr) > 1 or abs(c - gc) > 1:
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, _pt(g, r, c)]],
                "target_pixels": [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in band],
                "expected_pixels": [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in band] + [[r, c, _pt(g, r, c)]],
                "precondition": "click is outside the deepest pocket footprint, so no target is contacted",
                "scope": "level target object; expects no board or level change"}
    obj = [[rr, cc, _pt(g, rr, cc)] for (rr, cc) in band]
    tar = [[rr, cc, _pt(g, rr, cc)] for rr in range(gr - 1, gr + 2) for cc in range(gc - 1, gc + 2)]
    exp = [[rr, cc, "S"] for rr in range(gr - 1, gr + 2) for cc in range(gc - 1, gc + 2)]
    return {"mode": "change", "action": action,
            "object_pixels": obj,
            "target_pixels": tar,
            "expected_pixels": exp,
            "precondition": "the pocket interior is solid blue field with a single "
                            "reachable cell; clicking it registers the target hit that "
                            "completed the previous level",
            "scope": "level target object: expect level_completed/score change and a "
                     "new board layout; if the frame is byte-identical the pocket is "
                     "not the actionable target and the rule is contradicted"}
