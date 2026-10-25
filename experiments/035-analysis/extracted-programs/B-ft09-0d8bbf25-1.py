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
        leg[(pr, gc2)] = m if False else None
        leg.pop((pr, gc2), None)
        leg[(pr, pc)] = m
    return leg

def _mapping(leg, pr, pc, center):
    votes = collections.Counter()
    cells = None
    for sr in range(3):
        for sc in range(3):
            if sr == 1 and sc == 1:
                continue
            gr = 2 * pr + sr - 2
            gc = 2 * pc + sc - 2
            if gr < 0 or gr > 6 or gc < 0 or gc > 4:
                continue
            s = leg[(pr, pc)][sr][sc]
            if s in ('W', 'g'):
                votes[(s, cells)] = votes.get((s, cells), 0)
    return votes

def _score(rows, cellmap, leg, center_of):
    good = 0
    tot = 0
    for key in leg:
        pr, pc = key
        cen = center_of[key]
        for sr in range(3):
            for sc in range(3):
                if sr == 1 and sc == 1:
                    continue
                gr = 2 * pr + sr - 2
                gc = 2 * pc + sc - 2
                if gr < 0 or gr > 6 or gc < 0 or gc > 4:
                    continue
                s = leg[key][sr][sc]
                if s not in ('W', 'g'):
                    continue
                tot += 1
                want = cen if s == 'W' else ('O' if cen == 'R' else 'R')
                if cellmap[(gr, gc)][2] == want:
                    good += 1
    return good, tot

def plan_program(frame):
    rows = _rows(frame)
    cellmap = _cells(rows)
    leg = _legends(rows)
    center_of = {}
    for (pr, pc) in leg:
        center_of[(pr, pc)] = rows[pr * 6 + 7][pc * 6 + 7]
    bad = []
    for key in leg:
        cen = center_of[key]
        pr, pc = key
        for sr in range(3):
            for sc in range(3):
                if sr == 1 and sc == 1:
                    continue
                gr = 2 * pr + sr - 2
                gc = 2 * pc + sc - 2
                if gr < 0 or gr > 6 or gc < 0 or gc > 4:
                    continue
                s = leg[key][sr][sc]
                if s not in ('W', 'g'):
                    continue
                want = cen if s == 'W' else ('O' if cen == 'R' else 'R')
                if cellmap[(gr, gc)][2] != want:
                    bad.append((gr, gc, want))
    if not bad:
        gr, gc = (2, 1)
        cr, cc, cur = cellmap[(gr, gc)]
        acts = []
        ev = [[cr + 1, cc + 1, cur]]
        return {"status": "ready",
                "goal": "All 3x3 legends satisfied (W=center color, g=other color); probe one legend cell",
                "actions": [{"action": "MOUSE", "row": cr + 1, "col": cc + 1}],
                "evidence_pixels": ev,
                "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs"],
                "reason": "Board already matches the hypothesized legend mapping; single probe click on a legend-linked cell to test the toggle effect."}
    bad.sort()
    gr, gc, want = bad[0]
    cr, cc, cur = cellmap[(gr, gc)]
    ev = []
    for key in leg:
        pr, pc = key
        rr, ccx, _ = cellmap[(2 * pr - 2 + 1, 2 * pc - 2 + 1)] if (2 * pr - 1) <= 6 else (0, 0, 'c')
    ev.append([cr + 1, cc + 1, cur])
    for key in leg:
        pr, pc = key
        rr = pr * 6 + 7
        ccx = pc * 6 + 7
        ev.append([rr, ccx, rows[rr][ccx]])
    return {"status": "ready",
            "goal": "Satisfy every pattern legend: a 'W' legend mark requires its overlapping cell to equal that pattern's center color, a 'g' mark requires the other color. Next unsatisfied cell is grid (%d,%d) wanting %s." % (gr, gc, want),
            "actions": [{"action": "MOUSE", "row": cr + 1, "col": cc + 1}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs"],
            "reason": "Recomputed the 7x5 cell grid and the four 3x3 legends from this frame; the click toggles the cell between R and O (observed twice) so painting the first unsatisfied overlap cell moves toward legend consistency."}

def predict(frame, action):
    rows = _rows(frame)
    cellmap = _cells(rows)
    r = action.get("row")
    c = action.get("col")
    if r is None or c is None:
        return {"mode": "unknown", "reason": "action has no row/col"}
    hit = None
    for (gr, gc), (cr, cc, maj) in cellmap.items():
        if cr <= r <= cr + 5 and cc <= c <= cc + 5:
            hit = (gr, gc, cr, cc, maj)
            break
    if hit is None:
        return {"mode": "noop",
                "action": action,
                "object_pixels": [[r, c, rows[r][c]]],
                "target_pixels": [],
                "expected_pixels": [[r, c, rows[r][c]]],
                "precondition": "Click lands on background/legend art, not on a 6x6 playable cell, so no cell color changes.",
                "scope": "Checks that only 6x6 cell blocks respond to MOUSE."}
    gr, gc, cr, cc, maj = hit
    other = 'O' if maj == 'R' else 'R'
    obj = [[rr, ccx, rows[rr][ccx]] for rr in range(cr, cr + 6) for ccx in range(cc, cc + 6)]
    exp = [[rr, ccx, other] for rr in range(cr, cr + 6) for ccx in range(cc, cc + 6)]
    return {"mode": "change",
            "action": action,
            "object_pixels": obj,
            "target_pixels": obj,
            "expected_pixels": exp,
            "precondition": "The clicked point lies inside 6x6 cell grid(%d,%d) whose dominant color is %s; recorded clicks on such cells recolored the whole 36-pixel block to the other color." % (gr, gc, maj),
            "scope": "Cell grid(%d,%d) flips %s->%s and only that block changes, which tests whether legend consistency is driven by cell toggles." % (gr, gc, maj, other)}
