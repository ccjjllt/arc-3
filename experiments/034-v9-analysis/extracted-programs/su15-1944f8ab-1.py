import collections


def _rows(frame):
    return frame.ascii.splitlines()


def _grid(frame):
    r = _rows(frame)
    return [[r[i][j] for j in range(len(r[i]))] for i in range(len(r))]


def _comps(frame, colors):
    g = _grid(frame)
    n = len(g)
    m = len(g[0]) if n else 0
    seen = [[False] * m for _ in range(n)]
    out = []
    for i in range(n):
        for j in range(m):
            v = g[i][j]
            if v in colors and not seen[i][j]:
                q = collections.deque([(i, j)])
                seen[i][j] = True
                px = []
                while q:
                    r, c = q.popleft()
                    px.append((r, c))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr2, cc2 = r + dr, c + dc
                        if 0 <= rr2 < n and 0 <= cc2 < m and not seen[rr2][cc2] and g[rr2][cc2] == v:
                            seen[rr2][cc2] = True
                            q.append((rr2, cc2))
                out.append((v, px))
    return out


def _footprint(px):
    seen = set()
    out = []
    for r, c in px:
        for dr in (0, 1):
            for dc in (0, 1):
                p = (r + dr, c + dc)
                if p not in seen:
                    seen.add(p)
                    out.append(p)
    return out


def _single_px_comps(frame, color):
    res = []
    for v, px in _comps(frame, (color,)):
        if len(px) == 1:
            res.append(px[0])
    return res


def _ball(frame):
    hits = _single_px_comps(frame, 'S')
    hits = [p for p in hits if p[0] >= 10]
    if not hits:
        return None
    hits.sort(key=lambda p: (-p[0], p[1]))
    return hits[0]


def _toward(a, b, reach=7.0):
    dr = b[0] - a[0]
    dc = b[1] - a[1]
    d = (dr * dr + dc * dc) ** 0.5
    if d <= 0.001:
        return a
    if d <= reach:
        return b
    t = reach / d
    return (int(round(a[0] + dr * t)), int(round(a[1] + dc * t)))


def _center(px):
    rs = [p[0] for p in px]
    cs = [p[1] for p in px]
    return ((min(rs) + max(rs)) / 2.0, (min(cs) + max(cs)) / 2.0)


def plan_program(frame):
    try:
        pcs = _comps(frame, ('p', 'Y'))
        pieces = [(v, px) for v, px in pcs if len(px) <= 4]
        big = [(v, px) for v, px in pcs if len(px) > 4]
        bal = _ball(frame)
        if bal is None:
            return {"status": "abstain",
                    "goal": "deliver the pink/purple piece onto the isolated S ball below row 10",
                    "actions": [], "evidence_pixels": [], "replaces": [],
                    "reason": "no isolated S ball found in the play area"}
        if big:
            v, px = big[0]
            a, b = _center(px)
            nxt = _toward((a, b), bal, 7.0)
            ev = [[r, c, _rows(frame)[r][c]] for (r, c) in _footprint(px)]
            ev.append([bal[0], bal[1], 'S'])
            return {"status": "ready",
                    "goal": "move the merged piece (component %s at %s) one <=8 step toward ball %s" % (v, (int(a), int(b)), bal),
                    "actions": [{"action": "MOUSE", "row": nxt[0], "col": nxt[1]}],
                    "evidence_pixels": ev,
                    "replaces": ["route", "click", "state", "invaders"],
                    "reason": "merged piece exists; step it toward the ball and re-plan from the real frame"}
        if len(pieces) >= 2:
            best = None
            for i in range(len(pieces)):
                for j in range(i + 1, len(pieces)):
                    ca = _center(pieces[i][1])
                    cb = _center(pieces[j][1])
                    mid = ((ca[0] + cb[0]) / 2.0, (ca[1] + cb[1]) / 2.0)
                    r0 = int(round(mid[0]))
                    c0 = int(round(mid[1]))
                    da = ((r0 - ca[0]) ** 2 + (c0 - ca[1]) ** 2) ** 0.5
                    db = ((r0 - cb[0]) ** 2 + (c0 - cb[1]) ** 2) ** 0.5
                    if da <= 8.0 and db <= 8.0:
                        score = max(da, db)
                        if best is None or score < best[0]:
                            best = (score, r0, c0, pieces[i][1], pieces[j][1])
            if best is not None:
                _, r0, c0, pa, pb = best
                ev = [[r, c, _rows(frame)[r][c]] for (r, c) in _footprint(pa + pb)]
                ev.append([bal[0], bal[1], 'S'])
                return {"status": "ready",
                        "goal": "merge the two single-cell pink pieces into one 4-cell piece by clicking %s (within 8 of both centers)" % ((r0, c0),),
                        "actions": [{"action": "MOUSE", "row": r0, "col": c0}],
                        "evidence_pixels": ev,
                        "replaces": ["route", "click", "state", "invaders"],
                        "reason": "two 1-cell pink pieces are in range of one click; merging makes the piece large enough to walk to the ball"}
        if pieces:
            v, px = pieces[0]
            a, b = _center(px)
            nxt = _toward((a, b), bal, 7.0)
            ev = [[r, c, _rows(frame)[r][c]] for (r, c) in _footprint(px)]
            ev.append([bal[0], bal[1], 'S'])
            return {"status": "ready",
                    "goal": "walk the lone pink piece at %s toward ball %s" % ((int(a), int(b)), bal),
                    "actions": [{"action": "MOUSE", "row": nxt[0], "col": nxt[1]}],
                    "evidence_pixels": ev,
                    "replaces": ["route", "click", "state", "invaders"],
                    "reason": "single pink piece is the only mover; step toward the ball"}
        return {"status": "abstain",
                "goal": "deliver a pink/purple piece onto the isolated S ball below row 10",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "no pink or yellow piece component found on this frame; role of the mover is uncertain"}
    except Exception:
        return {"status": "abstain",
                "goal": "deliver a pink/purple piece onto the isolated S ball below row 10",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "could not recompute pieces and ball from this frame"}


def predict(frame, action):
    try:
        ad = action.get('action_data') or {}
        r0 = ad.get('row', action.get('row'))
        c0 = ad.get('col', action.get('col'))
        if r0 is None:
            return {"mode": "unknown", "reason": "action has no row/col"}
        pcs = _comps(frame, ('p', 'Y'))
        pieces = [(v, px) for v, px in pcs if len(px) <= 4]
        big = [(v, px) for v, px in pcs if len(px) > 4]
        bal = _ball(frame)
        if bal is None:
            return {"mode": "unknown", "reason": "no ball to relate the click to"}
        near = []
        for v, px in pieces + big:
            for (r, c) in px:
                if abs(r - r0) <= 8 and abs(c - c0) <= 8:
                    near.append((v, px))
                    break
        if not near:
            return {"mode": "noop", "action": action,
                    "object_pixels": [[bal[0], bal[1], 'S']],
                    "target_pixels": [[bal[0], bal[1], 'S']],
                    "expected_pixels": [[bal[0], bal[1], 'S']],
                    "precondition": "click is more than 8 cells from every pink/yellow piece, so no piece can be commanded or merged there",
                    "scope": "checks that only pieces within range of the click respond"}
        v, px = near[0]
        obj = [[r, c, _rows(frame)[r][c]] for (r, c) in _footprint(px)]
        if len(big) == 0 and len(pieces) >= 2 and len(px) == 1:
            other = None
            for v2, px2 in pieces:
                if px2 != px:
                    other = px2
            tp = [[r, c, _rows(frame)[r][c]] for (r, c) in _footprint(other)] if other else []
            exp = []
            for (r, c) in _footprint(px + (other or [])):
                exp.append([r, c, 'Y'])
            return {"mode": "change", "action": action,
                    "object_pixels": obj,
                    "target_pixels": tp,
                    "expected_pixels": exp,
                    "precondition": "the click lies within 8 of two single-cell pink pieces, so they should combine into one 4-cell piece at the click",
                    "scope": "merge of the two pink pieces; the merged footprint should show a single larger pink/yellow piece"}
        a, b = _center(px)
        nxt = _toward((a, b), bal, 7.0)
        exp = []
        for (r, c) in _footprint(px):
            exp.append([r - int(round(a)) + nxt[0], c - int(round(b)) + nxt[1], v])
        return {"mode": "change", "action": action,
                "object_pixels": obj,
                "target_pixels": [[bal[0], bal[1], 'S']],
                "expected_pixels": exp,
                "precondition": "the click is within 8 of this piece so it should move toward the ball by up to 7 cells",
                "scope": "the mover piece and its new footprint; the ball stays until the piece lands on it"}
    except Exception:
        return {"mode": "unknown", "reason": "could not relate this click to a current piece"}
