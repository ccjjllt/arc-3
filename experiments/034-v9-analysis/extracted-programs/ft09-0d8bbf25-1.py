import math


def _rows(frame):
    return frame.ascii.splitlines()


def _cell_top_left(frame, row, col):
    rs = _rows(frame)
    if not rs:
        return None
    if row < 0 or col < 0 or row >= len(rs) or col >= len(rs[0]):
        return None
    if rs[row][col] != 'c':
        return None
    if row + 6 >= len(rs) or col + 6 >= len(rs[0]):
        return None
    for dr in range(6):
        seg = rs[row + dr][col:col + 6]
        if len(seg) != 6 or seg.count(seg[0]) != 6:
            return None
    return (row, col, rs[row][col])


def _grid_cells(frame):
    rs = _rows(frame)
    out = {}
    for r in range(0, len(rs) - 6):
        line = rs[r]
        for c in range(0, len(line) - 6):
            if line[c] != 'c':
                continue
            tl = _cell_top_left(frame, r, c)
            if tl is None:
                continue
            out[((r - 4) // 8, (c - 12) // 8)] = tl
    return out


def _legend(rs, r0, c0):
    m = []
    for br in range(3):
        row = []
        for bc in range(3):
            row.append(rs[r0 + 2 * br][c0 + 2 * bc])
        m.append(row)
    return m


def _patterns(frame):
    rs = _rows(frame)
    sup = []
    for r in range(0, len(rs) - 6):
        for c in range(0, len(rs[0]) - 6):
            ch = rs[r][c]
            if ch not in ('R', 'O'):
                continue
            ok = True
            for dr in range(6):
                seg = rs[r + dr][c:c + 6]
                if len(seg) != 6:
                    ok = False
                    break
                for dc in range(6):
                    if (dr // 2, dc // 2) == (1, 1):
                        continue
                    if seg[dc] != ch:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                sup.append(((r - 4) // 8, (c - 12) // 8, r, c, ch,
                            _legend(rs, r, c)))
    return sup


def _rot(m, k):
    n = [row[:] for row in m]
    for _ in range(k % 4):
        n = [[n[2 - j][i] for j in range(3)] for i in range(3)]
    return n


def _flp(m):
    return [row[::-1] for row in m]


def _dih(m):
    out = []
    base = m
    for k in range(4):
        out.append(_rot(base, k))
    base = _flp(m)
    for k in range(4):
        out.append(_rot(base, k))
    return out


def _plan_cell(flip, sups, cells, grid):
    for (gr, gc, r0, c0, ch, leg) in sups:
        m = _flp(leg) if flip else leg
        for br in range(3):
            for bc in range(3):
                if (br, bc) == (1, 1):
                    continue
                tgt = (gr + br - 1, gc + bc - 1)
                if tgt not in cells:
                    continue
                sym = m[br][bc]
                want = ch if sym == 'W' else ('O' if ch == 'R' else 'R')
                cur = grid.get(tgt)
                if want == 'R' and cur == 'O':
                    return (tgt, (r0, c0, ch, sym, want))
    return None


def _score(flip, sups, cells, grid):
    good = 0
    tot = 0
    for (gr, gc, r0, c0, ch, leg) in sups:
        m = _flp(leg) if flip else leg
        for br in range(3):
            for bc in range(3):
                if (br, bc) == (1, 1):
                    continue
                tgt = (gr + br - 1, gc + bc - 1)
                if tgt not in cells:
                    continue
                sym = m[br][bc]
                want = ch if sym == 'W' else ('O' if ch == 'R' else 'R')
                tot += 1
                if grid.get(tgt) == want:
                    good += 1
    return (good, tot)


def _footprint(cells, key):
    tl = cells.get(key)
    if tl is None:
        return []
    r0, c0 = tl[0], tl[1]
    out = []
    for r in range(r0, r0 + 6):
        for c in range(c0, c0 + 6):
            out.append([r, c])
    return out


def plan_program(frame):
    try:
        cells = _grid_cells(frame)
        sups = _patterns(frame)
    except Exception:
        return {"status": "abstain",
                "goal": "recompute the 6x6 cell grid and pattern legends",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "board geometry unreadable"}
    grid = {}
    for k, tl in cells.items():
        grid[k] = tl[2]
    ev = []
    for (gr, gc, r0, c0, ch, leg) in sups:
        ev.append([r0, c0, ch])
    for k in sorted(cells):
        ev.append([cells[k][0], cells[k][1], cells[k][2]])
    if not sups or not cells:
        return {"status": "abstain", "goal": "locate pattern legends and cells",
                "actions": [], "evidence_pixels": ev, "replaces": [],
                "reason": "no pattern legend or no cell grid found"}
    order = [False, True]
    for flip in order:
        res = _plan_cell(flip, sups, cells, grid)
        if res is not None:
            tgt, info = res
            r0, c0, ch, sym, want = info
            act = {"action": "MOUSE", "row": cells[tgt][0] + 3,
                   "col": cells[tgt][1] + 3}
            g, t = _score(flip, sups, cells, grid)
            goal = ("pattern-supervised grid: %d/%d satisfied under %s legend "
                    "reading; cell %s currently O should be R per legend symbol "
                    "%s of pattern at row %d col %d (colour %s)"
                    % (g, t, "flipped" if flip else "direct", tgt, sym, r0, c0,
                       ch))
            return {"status": "ready", "goal": goal, "actions": [act],
                    "evidence_pixels": ev,
                    "replaces": ["frame_diff", "current_frame.segmentation"],
                    "reason": "clicking an O cell turned it R in the last two "
                              "observed transitions, so paint the next cell "
                              "that a pattern legend demands to be R"}
    return {"status": "completed",
            "goal": "every cell matches the pattern legend that covers it",
            "actions": [], "evidence_pixels": ev,
            "replaces": ["frame_diff", "current_frame.segmentation"],
            "reason": "no cell currently disagrees with the legend reading "
                      "tested; local target satisfied"}


def predict(frame, action):
    try:
        cells = _grid_cells(frame)
        sups = _patterns(frame)
    except Exception:
        return {"mode": "unknown", "reason": "board geometry unreadable"}
    grid = {}
    for k, tl in cells.items():
        grid[k] = tl[2]
    row = action.get("row")
    col = action.get("col")
    key = None
    for k, tl in cells.items():
        if tl[0] <= row <= tl[0] + 5 and tl[1] <= col <= tl[1] + 5:
            key = k
            break
    if key is None:
        return {"mode": "noop", "action": action, "object_pixels": [],
                "target_pixels": [], "expected_pixels": [],
                "precondition": "click lands on background, not a fillable cell",
                "scope": "no task object touched"}
    cur = grid[key]
    if cur != 'O':
        fp = [[r, c, cur] for (r, c) in _footprint(cells, key)]
        return {"mode": "noop", "action": action, "object_pixels": fp,
                "target_pixels": [], "expected_pixels": fp,
                "precondition": "cell already %s; the observed cycle only turns "
                                "O cells into R, so this click is blocked" % cur,
                "scope": "same grid cell, no colour change expected"}
    obj = [[r, c, cur] for (r, c) in _footprint(cells, key)]
    tgt = []
    want = None
    for (gr, gc, r0, c0, ch, leg) in sups:
        br = key[0] - (gr - 1)
        bc = key[1] - (gc - 1)
        if 0 <= br <= 2 and 0 <= bc <= 2 and (br, bc) != (1, 1):
            sym = leg[br][bc]
            w = ch if sym == 'W' else ('O' if ch == 'R' else 'R')
            for rr in range(r0, r0 + 6):
                for cc in range(c0, c0 + 6):
                    tgt.append([rr, cc, frame.ascii.splitlines()[rr][cc]])
            if want is None:
                want = w
    exp = [[r, c, 'R'] for (r, c) in _footprint(cells, key)]
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "the cell is O and a pattern legend covering it "
                            "calls for R; the two recorded MOUSE clicks each "
                            "turned a whole 6x6 O cell red",
            "scope": "one grid cell of the pattern-supervised board plus the "
                     "legend footprint that justifies the paint"}
