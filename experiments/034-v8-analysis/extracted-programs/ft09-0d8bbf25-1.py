import math

def _cell_map(frame):
    grid = frame.ascii
    cells = {}
    for gr in range(7):
        for gc in range(5):
            r0 = 4 + 8 * gr
            c0 = 12 + 8 * gc
            cells[(gr, gc)] = (r0 + 3, c0 + 3)
    return cells

def _legend(frame):
    grid = frame.ascii
    pats = [((12, 28), "O"), ((28, 20), "R"), ((28, 36), "R"), ((44, 28), "O")]
    out = []
    for (pr, pc), cen in pats:
        sub = []
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1:
                    continue
                r = pr + 2 * i
                c = pc + 2 * j
                sub.append(((i, j), grid[r][c]))
        out.append(((pr, pc), cen, tuple(sub)))
    return out

def _conflicts(frame):
    cells = _cell_map(frame)
    grid = frame.ascii
    pats = _legend(frame)
    rec = {}
    for (pr, pc), cen, sub in pats:
        gr0 = (pr - 4) // 8
        gc0 = (pc - 12) // 8
        for (i, j), sym in sub:
            key = (gr0 + i - 1, gc0 + j - 1)
            if key in cells:
                want = cen if sym == "W" else ("O" if cen == "R" else "R")
                rec.setdefault(key, []).append(want)
    bad = []
    for key, wants in sorted(rec.items()):
        r, c = cells[key]
        cur = frame.ascii[r][c]
        if any(w != cur for w in wants):
            bad.append((key, cur, tuple(sorted(set(wants)))))
    return bad

def plan_program(frame):
    try:
        bad = _conflicts(frame)
    except Exception:
        return {"status": "abstain", "goal": "legend-consistent cell grid",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "cannot recompute board layout"}
    if not bad:
        return {"status": "completed", "goal": "every cell matches every legend that covers it",
                "actions": [], "evidence_pixels": [], "replaces": ["r1", "d1", "cc", "cur"],
                "reason": "no legend mismatch remains on the recomputed grid"}
    key, cur, wants = bad[0]
    gr, gc = key
    r0 = 4 + 8 * gr
    c0 = 12 + 8 * gc
    target = None
    for w in wants:
        if w != cur:
            target = w
            break
    if target is None:
        return {"status": "abstain", "goal": "legend-consistent cell grid",
                "actions": [], "evidence_pixels": [], "replaces": ["r1", "d1", "cc", "cur"],
                "reason": "mismatch not resolvable by colour change"}
    run = 4 + 8 * gc
    rows = range(r0, r0 + 6)
    cols = range(run, run + 6)
    ev = [[r, c, frame.ascii[r][c]] for r in rows for c in cols]
    goal = ("cell grid row %d col %d shows %s but legends covering it require %s; "
            "click its 6x6 footprint at rows %d-%d cols %d-%d to test the "
            "click-cycles-cell-colour rule" % (gr, gc, cur, target, r0, r0 + 5, run, run + 5))
    return {"status": "ready", "goal": goal,
            "actions": [{"action": "MOUSE", "row": r0 + 3, "col": run + 3}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur"],
            "reason": "recomputed legends give a unique desired colour for this cell; "
                      "the last two MOUSE clicks each recoloured exactly one 6x6 cell "
                      "component plus the row-63 counter, supporting a cell-click rule"}

def predict(frame, action):
    try:
        bad = _conflicts(frame)
    except Exception:
        return {"mode": "unknown", "reason": "cannot recompute board layout"}
    if not bad:
        return {"mode": "noop",
                "reason": "no legend mismatch remains, so a cell click has no task effect",
                "object_pixels": [], "target_pixels": [], "expected_pixels": [],
                "action": action, "scope": "none"}
    key, cur, wants = bad[0]
    gr, gc = key
    r0 = 4 + 8 * gr
    run = 4 + 8 * gc
    target = None
    for w in wants:
        if w != cur:
            target = w
            break
    if target is None:
        return {"mode": "noop",
                "reason": "cell already matches its legends; click would be cosmetic",
                "object_pixels": [], "target_pixels": [], "expected_pixels": [],
                "action": action, "scope": "none"}
    rows = range(r0, r0 + 6)
    cols = range(run, run + 6)
    obj = [[r, c, frame.ascii[r][c]] for r in rows for c in cols]
    exp = [[r, c, target] for r in rows for c in cols]
    y = frame.ascii[63]
    prev = None
    for c in range(63, -1, -1):
        if y[c] != "Y":
            prev = y[c]
            break
    tgt = [[63, c, frame.ascii[63][c]] for c in range(64)
            if frame.ascii[63][c] != "Y"]
    if prev is not None:
        exp = exp + [[63, tgt[0][1], prev]]
    return {"mode": "change", "action": action,
            "object_pixels": obj, "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "the clicked point lies inside the 6x6 cell block at rows "
                            "%d-%d cols %d-%d whose colour disagrees with the legends "
                            "covering grid row %d col %d; a click on a cell block "
                            "recolours the whole block" % (r0, r0 + 5, run, run + 5, gr, gc),
            "scope": "one cell block of the 7x5 grid plus the row-63 progress counter: "
                     "checks that clicking a mismatching cell sets it to the colour the "
                     "legends demand and advances the counter"}
