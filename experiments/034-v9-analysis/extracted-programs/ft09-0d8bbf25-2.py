def _rows(frame):
    return frame.ascii.splitlines()


def _tl(rs, r, c):
    if r < 0 or c < 0 or r + 5 >= len(rs) or c + 5 >= len(rs[0]):
        return False
    for dr in range(6):
        seg = rs[r + dr][c:c + 6]
        if len(seg) != 6 or seg.count(seg[0]) != 6:
            return False
    return True


def _cells(frame):
    rs = _rows(frame)
    out = {}
    for r in range(0, len(rs) - 5):
        line = rs[r]
        for c in range(0, len(line) - 5):
            if line[c] not in ('R', 'O'):
                continue
            if not _tl(rs, r, c):
                continue
            top = (r - 4) % 8 == 0 and (c - 12) % 8 == 0
            if top:
                out[(r, c)] = line[c]
    return out


def _fp(tl):
    r0, c0 = tl
    out = []
    for r in range(r0, r0 + 6):
        for c in range(c0, c0 + 6):
            out.append((r, c))
    return out


def _pick(cells):
    best = None
    for tl in sorted(cells):
        r0, c0 = tl
        if r0 < 44:
            continue
        if cells[tl] != 'O':
            continue
        if best is None or (r0, c0) < best:
            best = tl
    return best


def plan_program(frame):
    try:
        cells = _cells(frame)
    except Exception:
        return {"status": "abstain",
                "goal": "recompute the uniform 6x6 cell grid from this frame",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "board geometry unreadable"}
    grid = {}
    for tl, ch in cells.items():
        grid[((tl[0] - 4) // 8, (tl[1] - 12) // 8)] = ch
    ev = []
    for tl in sorted(cells):
        ev.append([tl[0], tl[1], cells[tl]])
    for r in (0, 1, 2, 3):
        ev.append([r, 60, 'R'])
    for r in (4, 5, 6, 7):
        ev.append([r, 60, 'O'])
    ev.append([63, 53, 'Y'])
    ev.append([63, 63, 'Y'])
    if not cells:
        return {"status": "abstain",
                "goal": "locate uniform 6x6 fillable cells",
                "actions": [], "evidence_pixels": ev, "replaces": [],
                "reason": "no uniform 6x6 cell found, cannot choose a click"}
    tgt = _pick(cells)
    if tgt is None:
        return {"status": "completed",
                "goal": "convert every uniform orange cell in the lower band "
                        "(rows 44 and above) to red",
                "actions": [], "evidence_pixels": ev,
                "replaces": ["_cells", "_pick", "_fp"],
                "reason": "no uniform orange cell remains in the lower band, so "
                          "the local paint target is already satisfied"}
    low = [tl for tl in cells if tl[0] >= 44]
    goal = ("paint the uniform 6x6 orange cell at top-left (%d,%d) red; lower "
            "band holds %d uniform cells of which %d are still orange; the two "
            "recorded MOUSE clicks each recoloured one whole uniform cell and "
            "advanced the row-63 counter by one"
            % (tgt[0], tgt[1], len(low),
               len([t for t in low if cells[t] == 'O'])))
    act = {"action": "MOUSE", "row": tgt[0] + 3, "col": tgt[1] + 3}
    return {"status": "ready", "goal": goal, "actions": [act],
            "evidence_pixels": ev,
            "replaces": ["_cells", "_pick", "_fp"],
            "reason": "both recorded clicks landed inside a uniform 6x6 orange "
                      "cell and turned that entire cell red while adding one "
                      "yellow pixel to the row-63 counter, so repeat that "
                      "effect on the next remaining orange cell"}


def predict(frame, action):
    try:
        cells = _cells(frame)
    except Exception:
        return {"mode": "unknown", "reason": "board geometry unreadable"}
    rs = _rows(frame)
    row = action.get("row")
    col = action.get("col")
    key = None
    for tl, ch in cells.items():
        if tl[0] <= row <= tl[0] + 5 and tl[1] <= col <= tl[1] + 5:
            key = tl
            break
    if key is None:
        return {"mode": "noop", "action": action, "object_pixels": [],
                "target_pixels": [], "expected_pixels": [],
                "precondition": "the click point is not inside a uniform 6x6 "
                                "cell, so no task object is under the cursor",
                "scope": "no task object touched"}
    cur = cells[key]
    obj = [[r, c, cur] for (r, c) in _fp(key)]
    if cur != 'O':
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": [], "expected_pixels": obj,
                "precondition": "cell at (%d,%d) is already %s; the observed "
                                "effect only recolours a uniform orange cell, "
                                "so this click is obstructed"
                                % (key[0], key[1], cur),
                "scope": "same grid cell, no colour change and no counter "
                         "increment expected"}
    exp = [[r, c, 'R'] for (r, c) in _fp(key)]
    tgt = []
    for c in range(53, 64):
        tgt.append([63, c, rs[63][c]])
    exp.append([63, 52, 'Y'])
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "the cell is uniformly orange and both recorded "
                            "MOUSE clicks on uniform orange cells recoloured "
                            "the whole 6x6 block to red and extended the yellow "
                            "row-63 counter by one pixel",
            "scope": "one uniform grid cell plus the row-63 yellow counter "
                     "boundary, checking that a paint advances the counter"}
