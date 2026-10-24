import math

def _grid(frame):
    g = getattr(frame, "ascii", None)
    if g is None:
        g = getattr(frame, "grid", None)
    if isinstance(g, str):
        return [list(r) for r in g.split("\n")]
    if g and isinstance(g[0], str):
        return [list(r) for r in g]
    return [list(r) for r in g]

def _comps(frame):
    comps = getattr(frame, "object_evidence", None)
    if isinstance(comps, dict):
        comps = comps.get("components")
    if comps is None:
        comps = getattr(frame, "components", None)
    out = []
    for c in (comps or []):
        col = c.get("color")
        pts = []
        if c.get("rect"):
            r0, c0, r1, c1 = c["bbox"]
            for r in range(r0, r1 + 1):
                for cc in range(c0, c1 + 1):
                    pts.append((r, cc))
        else:
            for run in c.get("runs", []):
                rr, c0, c1 = run[0], run[1], run[2]
                for cc in range(c0, c1 + 1):
                    pts.append((rr, cc))
        if pts:
            out.append((col, pts))
    return out

def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def _inside(grid, r, c):
    return 0 <= r < len(grid) and 0 <= c < len(grid[0])

def _first(grid, r, c):
    if _inside(grid, r, c):
        return grid[r][c]
    return None

def _find_target(grid, comps):
    rows = len(grid)
    cols = len(grid[0])
    # 1) isolated single 'S' pixels (ball markers)
    singles = [pts[0] for col, pts in comps if col == "S" and len(pts) == 1]
    singles = [p for p in singles if p[0] >= 10]
    if singles:
        singles.sort(key=lambda p: (p[0], p[1]))
        return singles[0], "isolated S ball marker"
    # 2) symmetric light blob in the play field
    best = None
    for col, pts in comps:
        if len(pts) < 20 or col not in ("b", "B", "W", "Y", "S"):
            continue
        r0 = min(p[0] for p in pts)
        r1 = max(p[0] for p in pts)
        c0 = min(p[1] for p in pts)
        c1 = max(p[1] for p in pts)
        if r0 < 10 or r1 > rows - 2:
            continue
        if (r1 - r0) < 4 or abs((r1 - r0) - (c1 - c0)) > 3:
            continue
        h = (r0 + r1) / 2.0
        w = (c0 + c1) / 2.0
        score = len(pts) / float((r1 - r0 + 1) * (c1 - c0 + 1))
        if best is None or score > best[0]:
            best = (score, (int(round(h)), int(round(w))))
    if best:
        return best[1], "symmetric blob centroid"
    # 3) white boundary strip
    for r in range(rows - 1, -1, -1):
        if all(grid[r][c] == "W" for c in range(cols)):
            return (r, cols // 2), "white boundary strip"
    return None, "none"

def _find_piece(comps):
    cands = [pts for col, pts in comps if col in ("Y", "p", "P") and len(pts) >= 1]
    cands = [pts for pts in cands if min(p[0] for p in pts) >= 8]
    if not cands:
        return None, None
    big = max(len(pts) for pts in cands)
    pts = [p for pt in cands if len(pt) == big for p in pt]
    col = "Y" if big > 4 else "P"
    return _centroid(pts), col

def _nearest_S(grid, comps, r, c):
    best = None
    for col, pts in comps:
        if col != "S":
            continue
        for (rr, cc) in pts:
            if rr < 10:
                continue
            d = math.hypot(rr - r, cc - c)
            if best is None or d < best[0]:
                best = (d, (rr, cc))
    return best

def plan_program(frame):
    grid = _grid(frame)
    comps = _comps(frame)
    tgt, why = _find_target(grid, comps)
    pc, pcol = _find_piece(comps)
    if tgt is None or pc is None:
        return {"status": "abstain", "goal": "locate active piece and ball target",
                "actions": [], "evidence_pixels": [],
                "replaces": ["route", "safe", "safe2", "safe3", "invaders", "state", "click"],
                "reason": "cannot recover piece or ball target from this frame"}
    tr, tc = tgt
    pr, pc_ = pc
    ev = [[tr, tc, _first(grid, tr, tc)],
          [int(round(pr)), int(round(pc_)), _first(grid, int(round(pr)), int(round(pc_)))]]
    if math.hypot(tr - pr, tc - pc_) <= 1.2:
        return {"status": "completed", "goal": "active piece resting on ball target (%d,%d)" % (tr, tc),
                "actions": [], "evidence_pixels": ev,
                "replaces": ["route", "safe", "safe2", "safe3", "invaders", "state", "click"],
                "reason": "piece centroid coincides with the located ball target"}
    # gather merge candidates: small same-colour pieces of the piece colour family
    fam = ("Y", "p", "P")
    small = []
    for col, pts in comps:
        if col in fam and max(p[0] for p in pts) >= 8 and len(pts) <= 12:
            small.append((col, pts))
    merged = [c for c in small if c[0] == "Y"]
    others = [c for c in small if c[0] != "Y"]
    if others and not merged:
        cents = [_centroid(p) for _, p in others]
        best = None
        for i in range(len(cents)):
            for j in range(i + 1, len(cents)):
                mr = (cents[i][0] + cents[j][0]) / 2.0
                mc = (cents[i][1] + cents[j][1]) / 2.0
                d1 = math.hypot(mr - cents[i][0], mc - cents[i][1])
                d2 = math.hypot(mr - cents[j][0], mc - cents[j][1])
                if d1 <= 8.0 and d2 <= 8.0:
                    dd = max(d1, d2)
                    if best is None or dd < best[0]:
                        best = (dd, (mr, mc))
        if best is not None:
            mr, mc = best[1]
            r = int(round(mr))
            c = int(round(mc))
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
                return {"status": "ready",
                        "goal": "merge split piece at (%d,%d) then deliver to ball (%d,%d)" % (r, c, tr, tc),
                        "actions": [{"action": "MOUSE", "row": r, "col": c}],
                        "evidence_pixels": ev,
                        "replaces": ["route", "safe", "safe2", "safe3", "invaders", "state", "click"],
                        "reason": "piece exists only as split sub-pieces; click within range of both to combine"}
    # single click toward target, clamped to observed max travel of 8
    dr = tr - pr
    dc = tc - pc_
    dist = math.hypot(dr, dc)
    step = min(dist, 7.0)
    nr = pr + dr * step / dist
    nc = pc_ + dc * step / dist
    r = int(round(nr))
    c = int(round(nc))
    r = max(0, min(len(grid) - 1, r))
    c = max(0, min(len(grid)[0] - 1, c))
    ns = _nearest_S(grid, comps, r, c)
    if ns is not None and ns[0] > 12 and math.hypot(tr - pr, tc - pc_) < 12:
        r = int(round(pr))
        c = int(round(pc_))
    return {"status": "ready",
            "goal": "move active piece to ball target (%d,%d) found by %s" % (tr, tc, why),
            "actions": [{"action": "MOUSE", "row": r, "col": c}],
            "evidence_pixels": ev,
            "replaces": ["route", "safe", "safe2", "safe3", "invaders", "state", "click"],
            "reason": "recomputed piece centroid and ball target from this frame; one bounded move toward target"}

def predict(frame, action):
    grid = _grid(frame)
    comps = _comps(frame)
    tgt, why = _find_target(grid, comps)
    pc, pcol = _find_piece(comps)
    r = action.get("row")
    c = action.get("col")
    if r is None or c is None:
        return {"mode": "unknown", "reason": "action has no row/col footprint"}
    cur = _first(grid, r, c)
    if cur is None:
        return {"mode": "unknown", "reason": "click outside board"}
    if pc is None or tgt is None:
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, cur]], "target_pixels": [],
                "expected_pixels": [[r, c, cur]],
                "precondition": "no active piece and no ball target recoverable, so the click cannot move any task object",
                "scope": "would check piece relocation; blocked by missing piece/target"}
    tr, tc = tgt
    pr, pc_ = pc
    dist = math.hypot(tr - pr, tc - pc_)
    fam = [p for col, pts in comps if col in ("Y", "p", "P") and max(q[0] for q in pts) >= 8 for p in pts]
    obj = [[int(round(pr)), int(round(pc_)), _first(grid, int(round(pr)), int(round(pc_)))]]
    for (rr, cc) in fam:
        obj.append([rr, cc, grid[rr][cc]])
    tgt_px = []
    for col, pts in comps:
        if col == "S" and len(pts) == 1 and pts[0][0] >= 10:
            tgt_px.append([pts[0][0], pts[0][1], "S"])
    tgt_px.append([tr, tc, cur if (tr, tc) == (r, c) else _first(grid, tr, tc)])
    if dist <= 1.2:
        return {"mode": "noop", "action": action,
                "object_pixels": obj, "target_pixels": tgt_px,
                "expected_pixels": [[int(round(pr)), int(round(pc_)), _first(grid, int(round(pr)), int(round(pc_)))]],
                "precondition": "piece already coincides with the ball target, so a further click cannot produce task progress",
                "scope": "checks that no spurious move occurs when the delivery goal is met"}
    dr = tr - pr
    dc = tc - pc_
    d = math.hypot(dr, dc)
    step = min(d, 7.0)
    nr = int(round(pr + dr * step / d))
    nc = int(round(pc + dc * step / d))
    nr = max(0, min(len(grid) - 1, nr))
    nc = max(0, min(len(grid)[0] - 1, nc))
    exp = []
    for (rr, cc) in fam:
        exp.append([rr, cc, "B"])
    for k in range(-1, 2):
        for l in range(-1, 2):
            rr, cc = nr + k, nc + l
            if _inside(grid, rr, cc):
                exp.append([rr, cc, _first(grid, rr, cc)])
    exp.append([r, c, cur])
    return {"mode": "change", "action": action,
            "object_pixels": obj, "target_pixels": tgt_px,
            "expected_pixels": exp,
            "precondition": "MOUSE click issues a bounded relocation of the active piece toward the ball target at (%d,%d); it is blocked only if the click is out of range of the piece" % (tr, tc),
            "scope": "checks the active piece footprint vacates its old cells and the commanded click neighbourhood changes colour"}
