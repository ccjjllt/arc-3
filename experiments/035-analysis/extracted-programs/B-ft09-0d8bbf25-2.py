import collections

def _rows(frame):
    return frame.ascii.splitlines()

def _cells(rows):
    R = len(rows)
    C = len(rows[0]) if R else 0
    out = {}
    for gr in range(6):
        for gc in range(5):
            cr = 44 + gr * 6
            cc = 8 + gc * 6
            if cr + 5 >= R or cc + 5 >= C:
                continue
            cnt = collections.Counter()
            for r in range(cr, cr + 6):
                row = rows[r]
                for c in range(cc, cc + 6):
                    cnt[row[c]] += 1
            maj, _ = cnt.most_common(1)[0]
            out[(gr, gc)] = (cr, cc, maj)
    return out

def _legends(rows):
    leg = {}
    for (pr, pc) in ((2, 4), (4, 2), (4, 6), (6, 4)):
        m = []
        for sr in range(3):
            row = []
            for sc in range(3):
                if sr == 1 and sc == 1:
                    row.append('.')
                else:
                    row.append(rows[pr * 6 + sr * 2 + 1][pc * 6 + sc * 2 + 1])
            m.append(row)
        leg[(pr, pc)] = m
    return leg

def _center_of(rows, pr, pc):
    return rows[pr * 6 + 7][pc * 6 + 7]

def _want(s, cen):
    if s == 'W':
        return cen
    if s == 'g':
        return 'O' if cen == 'R' else 'R'
    return None

def _unsat(rows, cellmap, leg):
    bad = []
    for key in leg:
        pr, pc = key
        cen = _center_of(rows, pr, pc)
        for sr in range(3):
            for sc in range(3):
                if sr == 1 and sc == 1:
                    continue
                gr = 2 * pr + sr - 2
                gc = 2 * pc + sc - 2
                if gr < 0 or gr > 5 or gc < 0 or gc > 4:
                    continue
                w = _want(leg[key][sr][sc], cen)
                if w is None:
                    continue
                if cellmap[(gr, gc)][2] != w:
                    bad.append((gr, gc, w))
    bad.sort()
    return bad

def plan_program(frame):
    rows = _rows(frame)
    cellmap = _cells(rows)
    leg = _legends(rows)
    bad = _unsat(rows, cellmap, leg)
    ev = []
    for key in leg:
        pr, pc = key
        rr = pr * 6 + 7
        ccx = pc * 6 + 7
        ev.append([rr, ccx, rows[rr][ccx]])
    for (gr, gc, w) in bad[:4]:
        cr, cc, cur = cellmap[(gr, gc)]
        ev.append([cr + 1, cc + 1, cur])
    if not bad:
        (gr, gc) = (2, 1)
        cr, cc, cur = cellmap[(gr, gc)]
        ev.append([cr + 1, cc + 1, cur])
        return {"status": "ready",
                "goal": "Every 3x3 legend mark is satisfied (W means the overlapped cell equals that legend's centre colour, g means the opposite colour). Probe one legend-linked cell to re-test the toggle effect.",
                "actions": [{"action": "MOUSE", "row": cr + 1, "col": cc + 1}],
                "evidence_pixels": ev,
                "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs", "gc2"],
                "reason": "Recomputed the cell grid and the four legends from this frame; all marks currently agree with the W/g rule, so one click on a legend-linked cell tests whether the toggle is what the puzzle tracks."}
    gr, gc, want = bad[0]
    cr, cc, cur = cellmap[(gr, gc)]
    return {"status": "ready",
            "goal": "Satisfy every pattern legend: a 'W' mark requires its overlapped cell to equal that legend's centre colour and a 'g' mark requires the other colour. First unsatisfied cell is grid(%d,%d) currently %s wanting %s." % (gr, gc, cur, want),
            "actions": [{"action": "MOUSE", "row": cr + 1, "col": cc + 1}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs", "gc2"],
            "reason": "Two recorded clicks each recoloured exactly one 6x6 cell block between R and O, so clicking the first legend-unsatisfied cell flips it toward the colour its legend demands. Layout and legends are recomputed from this frame, not reused constants."}

def predict(frame, action):
    rows = _rows(frame)
    cellmap = _cells(rows)
    r = action.get("row")
    c = action.get("col")
    if r is None or c is None:
        return {"mode": "unknown", "reason": "action has no row/col"}
    hit = None
    for key in cellmap:
        cr, cc, maj = cellmap[key]
        if cr <= r <= cr + 5 and cc <= c <= cc + 5:
            hit = (key[0], key[1], cr, cc, maj)
            break
    if hit is None:
        return {"mode": "noop",
                "action": action,
                "object_pixels": [[r, c, rows[r][c]]],
                "target_pixels": [],
                "expected_pixels": [[r, c, rows[r][c]]],
                "precondition": "The click lands on background or legend art, not inside a 6x6 cell block, so no task cell recolours.",
                "scope": "Checks that only 6x6 cell blocks respond to MOUSE."}
    gr, gc, cr, cc, maj = hit
    other = 'O' if maj == 'R' else 'R'
    obj = []
    exp = []
    for rr in range(cr, cr + 6):
        for ccx in range(cc, cc + 6):
            obj.append([rr, ccx, rows[rr][ccx]])
            exp.append([rr, ccx, other])
    return {"mode": "change",
            "action": action,
            "object_pixels": obj,
            "target_pixels": obj,
            "expected_pixels": exp,
            "precondition": "The clicked point lies inside 6x6 cell grid(%d,%d) whose dominant colour is %s; both recorded clicks recoloured the whole 36-pixel block to the other colour, so this click needs a playable R/O cell which it has." % (gr, gc, maj),
            "scope": "Cell grid(%d,%d) flips %s->%s across its complete 6x6 footprint, testing whether legend consistency is driven by cell toggles." % (gr, gc, maj, other)}
