def _cell_layout(frame):
    w = frame.shape[1]
    edge = 0
    for c in range(w):
        if frame.ascii[0][c] != "c":
            edge = c
            break
    if edge < 8:
        edge = 56
    rows = []
    r = 0
    n = len(frame.ascii)
    while r < n:
        if frame.ascii[r][edge] != "c":
            rows.append((r, r + 5))
            r += 8
        else:
            r += 1
    cols = []
    c = 0
    w = frame.shape[1]
    while c < w:
        if frame.ascii[rows[0][0]][c] != "c":
            cols.append((c, c + 5))
            c += 8
        else:
            c += 1
    return rows, cols


def _uniform(frame, r0, c0):
    ref = frame.ascii[r0][c0]
    for r in range(r0, r0 + 6):
        row = frame.ascii[r]
        for c in range(c0, c0 + 6):
            if row[c] != ref:
                return None
    return ref


def _candidates(frame):
    rows, cols = _cell_layout(frame)
    out = []
    for ri, (r0, _r1) in enumerate(rows):
        for ci, (c0, _c1) in enumerate(cols):
            col = _uniform(frame, r0, c0)
            if col in ("R", "O"):
                out.append((ri, ci, r0, c0, col))
    return out


def _at(frame, r, c):
    rows, cols = _cell_layout(frame)
    for ri, (a, b) in enumerate(rows):
        if a <= r <= b:
            for ci, (x, y) in enumerate(cols):
                if x <= c <= y:
                    return ri, ci
    return None


def plan_program(frame):
    try:
        cands = _candidates(frame)
        rows, cols = _cell_layout(frame)
    except Exception:
        return {"status": "abstain", "goal": "uniform cell blocks",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "cannot recompute the cell grid from this frame"}
    if not cands:
        return {"status": "abstain", "goal": "uniform R/O cell block",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "no uniform R/O cell block found"}
    nR = sum(1 for t in cands if t[4] == "R")
    nO = sum(1 for t in cands if t[4] == "O")
    want = "O" if nR > nO else "R"
    pick = None
    for t in cands:
        if t[4] != want:
            pick = t
            break
    if pick is None:
        return {"status": "completed",
                "goal": "all %d uniform cell blocks show %s" % (len(cands), want),
                "actions": [], "evidence_pixels": [],
                "replaces": ["r1", "d1", "cc", "cur"],
                "reason": "recomputed grid: every uniform cell block already shows the "
                          "minority colour %s, so no further click is indicated" % want}
    ri, ci, r0, c0, cur = pick
    ev = [[r, c, frame.ascii[r][c]] for r in range(r0, r0 + 6)
          for c in range(c0, c0 + 6)]
    goal = ("click the uniform %s cell block at grid (%d,%d) rows %d-%d cols %d-%d; "
            "both recorded clicks each recoloured exactly one whole 6x6 cell block "
            "(block %s->%s at rows 52-57 cols 36-41, block O->R at rows 4-9 cols 20-25) "
            "and moved one row-63 counter pixel; this tests whether a cell click flips "
            "the block between R and O" % (cur, ri, ci, r0, r0 + 5, c0, c0 + 5,
                                           "R", "O"))
    return {"status": "ready", "goal": goal,
            "actions": [{"action": "MOUSE", "row": r0 + 3, "col": c0 + 3}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur"],
            "reason": "recomputed from this frame: %d uniform cell blocks (%d R, %d O); "
                      "the only confirmed per-action effect is a whole-block recolour of "
                      "one cell plus one row-63 counter pixel, so the next action is one "
                      "click on the first block not showing the minority colour"
                      % (len(cands), nR, nO)}


def predict(frame, action):
    try:
        cands = _candidates(frame)
        rows, cols = _cell_layout(frame)
    except Exception:
        return {"mode": "unknown", "reason": "cannot recompute the cell grid"}
    if not cands:
        return {"mode": "unknown", "reason": "no uniform R/O cell block to act on"}
    nR = sum(1 for t in cands if t[4] == "R")
    nO = sum(1 for t in cands if t[4] == "O")
    want = "O" if nR > nO else "R"
    pick = None
    for t in cands:
        if t[4] != want:
            pick = t
            break
    if pick is None:
        return {"mode": "noop", "action": action,
                "object_pixels": [], "target_pixels": [], "expected_pixels": [],
                "precondition": "every uniform cell block already shows the minority "
                                "colour, so no mismatching block remains to recolor",
                "scope": "none"}
    ri, ci, r0, c0, cur = pick
    a = action or {}
    ar = a.get("row")
    ac = a.get("col")
    hit = None
    if ar is not None and ac is not None:
        hit = _at(frame, ar, ac)
    if hit != (ri, ci):
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, frame.ascii[r][c]]
                                  for r in range(r0, r0 + 6) for c in range(c0, c0 + 6)],
                "target_pixels": [], "expected_pixels": [],
                "precondition": "click (%s,%s) is outside the selected block rows %d-%d "
                                "cols %d-%d, so the predicted recolour does not apply"
                                % (ar, ac, r0, r0 + 5, c0, c0 + 5),
                "scope": "cell block grid (%d,%d) stays unchanged" % (ri, ci)}
    obj = [[r, c, frame.ascii[r][c]] for r in range(r0, r0 + 6)
           for c in range(c0, c0 + 6)]
    exp = [[r, c, want] for r in range(r0, r0 + 6) for c in range(c0, c0 + 6)]
    y = frame.ascii[63]
    tgt = []
    exp.append([63, 63, y[63]])
    prev = None
    for c in range(63, -1, -1):
        if y[c] != "Y":
            prev = y[c]
            break
    for c in range(63, -1, -1):
        if y[c] != "Y":
            tgt.append([63, c, y[c]])
            break
    if prev is not None and tgt:
        exp.append([63, tgt[0][1], prev])
    return {"mode": "change", "action": action,
            "object_pixels": obj, "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "the click lies inside the uniform %s cell block at rows "
                            "%d-%d cols %d-%d; recorded clicks recoloured one whole 6x6 "
                            "block and shifted one row-63 counter pixel, so this click "
                            "requires the same footprint" % (cur, r0, r0 + 5, c0, c0 + 5),
            "scope": "cell block grid (%d,%d) flips %s->%s and the row-63 counter loses "
                     "one non-Y pixel at its right end: checks the whole-block click "
                     "recolour rule and the counter consequence" % (ri, ci, cur, want)}
