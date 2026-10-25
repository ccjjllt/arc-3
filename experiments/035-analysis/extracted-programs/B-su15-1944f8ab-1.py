import math

def _rows(frame):
    return frame.ascii.splitlines()

def _runs(rows, r0, c0, r1, c1, ch):
    out = []
    for r in range(r0, r1 + 1):
        if r < 0 or r >= len(rows):
            continue
        row = rows[r]
        c = c0
        while c <= c1 and c < len(row):
            if row[c] == ch:
                e = c
                while e + 1 <= c1 and e + 1 < len(row) and row[e + 1] == ch:
                    e += 1
                out.append((r, c, e))
                c = e + 1
            else:
                c += 1
    return out

def _nearest_run(runs, r, c):
    best = None
    bd = 1e9
    for (rr, c0, c1) in runs:
        cc = min(max(c, c0), c1)
        d = math.hypot(rr - r, cc - c)
        if d < bd:
            bd = d
            best = (rr, cc)
    return best, bd

def _find_all(rows, ch):
    res = []
    seen = set()
    for r, row in enumerate(rows):
        for c, x in enumerate(row):
            if x == ch and (r, c) not in seen:
                st = [(r, c)]
                seen.add((r, c))
                comp = []
                while st:
                    y, x = st.pop()
                    comp.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]):
                            if (ny, nx) not in seen and rows[ny][nx] == ch:
                                seen.add((ny, nx))
                                st.append((ny, nx))
                res.append(comp)
    return res

def _target_ball(rows):
    cands = []
    for comp in _find_all(rows, 'S'):
        r0 = min(p[0] for p in comp)
        r1 = max(p[0] for p in comp)
        if r0 >= 10:
            c0 = min(p[1] for p in comp)
            c1 = max(p[1] for p in comp)
            cands.append(((r0 + r1) / 2.0, (c0 + c1) / 2.0, len(comp)))
    if not cands:
        return None
    cands.sort(key=lambda t: -t[2])
    return cands[0]

def plan_program(frame):
    rows = _rows(frame)
    ball = _target_ball(rows)
    if ball is None:
        return {"status": "abstain", "goal": "local target: deliver a Y/p mass onto the S ball below the level divider",
                "evidence_pixels": [], "replaces": [],
                "reason": "no S pixel below row 10 in this frame, so the ball target cannot be located"}
    pcs = []
    for ch in ('Y', 'p'):
        for comp in _find_all(rows, ch):
            r0 = min(p[0] for p in comp)
            r1 = max(p[0] for p in comp)
            if r0 >= 10:
                pcs.append((ch, comp))
    if not pcs:
        return {"status": "abstain", "goal": "local target: deliver a Y/p mass onto the S ball below the level divider",
                "evidence_pixels": [], "replaces": [],
                "reason": "no Y or p mass below the divider in this frame; nothing to move toward the ball"}
    # prefer a Y mass; otherwise the largest p mass
    ys = [t for t in pcs if t[0] == 'Y']
    pool = ys if ys else pcs
    ch, comp = max(pool, key=lambda t: len(t[1]))
    r0 = min(p[0] for p in comp)
    r1 = max(p[0] for p in comp)
    c0 = min(p[1] for p in comp)
    c1 = max(p[1] for p in comp)
    cr, cc = (r0 + r1) / 2.0, (c0 + c1) / 2.0
    br, bc = ball[0], ball[1]
    d = math.hypot(br - cr, bc - cc)
    ev = [[r, c, rows[r][c]] for (r, c) in sorted(comp)[:24]]
    ev += [[int(ball[0]), int(ball[1]), 'S']]
    if d <= 1.2:
        return {"status": "completed",
                "goal": "mass of color %s bbox[%d,%d,%d,%d] sits on S ball at (%.1f,%.1f)" % (ch, r0, c0, r1, c1, br, bc),
                "evidence_pixels": ev,
                "replaces": ["click", "invaders", "state", "route"],
                "reason": "the carried mass already occupies the ball cell, so the local delivery target is met"}
    step = min(7.0, d)
    tr = cr + (br - cr) * step / d
    tc = cc + (bc - cc) * step / d
    tr = max(11.0, min(62.0, tr))
    tc = max(0.0, min(63.0, tc))
    act = {"action": "MOUSE", "row": int(round(tr)), "col": int(round(tc))}
    return {"status": "ready",
            "goal": "move mass %s bbox[%d,%d,%d,%d] one <=7-step toward S ball at (%.1f,%.1f)" % (ch, r0, c0, r1, c1, br, bc),
            "actions": [act],
            "evidence_pixels": ev,
            "replaces": ["click", "invaders", "state", "route"],
            "reason": "paused route coordinates came from an older level; recompute the step from this frame's own mass centroid and S ball position"}

def predict(frame, action):
    rows = _rows(frame)
    ball = _target_ball(rows)
    pcs = []
    for ch in ('Y', 'p'):
        for comp in _find_all(rows, ch):
            if min(p[0] for p in comp) >= 10:
                pcs.append((ch, comp))
    if not pcs or ball is None:
        return {"mode": "unknown", "reason": "no carried mass or no S ball below the divider in this frame"}
    ys = [t for t in pcs if t[0] == 'Y']
    pool = ys if ys else pcs
    ch, comp = max(pool, key=lambda t: len(t[1]))
    r0 = min(p[0] for p in comp)
    r1 = max(p[0] for p in comp)
    c0 = min(p[1] for p in comp)
    c1 = max(p[1] for p in comp)
    cr, cc = (r0 + r1) / 2.0, (c0 + c1) / 2.0
    br, bc = ball[0], ball[1]
    d = math.hypot(br - cr, bc - cc)
    if d <= 1.2:
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, rows[r][c]] for (r, c) in sorted(comp)[:24]],
                "target_pixels": [[int(br), int(bc), 'S']],
                "expected_pixels": [],
                "precondition": "mass already on the ball; a further click cannot advance the local target",
                "scope": "carried mass and S ball contact state"}
    step = min(7.0, d)
    tr = cr + (br - cr) * step / d
    tc = cc + (bc - cc) * step / d
    tr = max(11.0, min(62.0, tr))
    tc = max(0.0, min(63.0, tc))
    ar, ac = tr, tc
    h = max(r1 - r0, c1 - c0)
    nr0 = int(round(ar - h / 2.0))
    nc0 = int(round(ac - h / 2.0))
    nr1 = nr0 + (r1 - r0)
    nc1 = nc0 + (c1 - c0)
    obj = [[r, c, rows[r][c]] for (r, c) in sorted(comp)[:24]]
    tgt = [[int(br), int(bc), 'S']]
    exp = []
    for rr in range(max(0, r0), min(len(rows) - 1, r1) + 1):
        for ccx in range(max(0, c0), min(len(rows[rr]) - 1, c1) + 1):
            if (rr, ccx) in comp:
                exp.append([rr, ccx, 'B'])
    for rr in range(max(0, nr0), min(len(rows) - 1, nr1) + 1):
        for ccx in range(max(0, nc0), min(len(rows[rr]) - 1, nc1) + 1):
            exp.append([rr, ccx, ch])
    near, nd = _nearest_run(_runs(rows, 10, 0, 62, 63, ch), ar, ac)
    if near is not None and nd <= 1.6:
        mode = "change"
        pre = "click within range of the %s mass: it relayouts toward the click point (nearest %s run at %s)" % (ch, ch, str(near))
    else:
        mode = "noop"
        pre = "click point (%d,%d) is %.1f away from the nearest %s pixel, out of the ~8 command radius, so it should be refused" % (int(ar), int(ac), nd, ch)
    return {"mode": mode, "action": action,
            "object_pixels": obj,
            "target_pixels": tgt,
            "expected_pixels": exp,
            "precondition": pre,
            "scope": "carried %s mass footprint plus S ball cell: mass shifts toward the ball, ball pixel stays S" % ch}