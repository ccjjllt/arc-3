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
    for (r, c) in px:
        if (r, c) not in seen:
            seen.add((r, c))
            out.append((r, c))
    return out


def _center(px):
    rs = [p[0] for p in px]
    cs = [p[1] for p in px]
    return ((min(rs) + max(rs)) / 2.0, (min(cs) + max(cs)) / 2.0)


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


def _single_px_comps(frame, color):
    res = []
    for v, px in _comps(frame, (color,)):
        if len(px) == 1:
            res.append(px[0])
    return res


def _ball(frame):
    hits = [p for p in _single_px_comps(frame, 'S') if p[0] >= 10]
    if not hits:
        return None
    hits.sort(key=lambda p: (-p[0], p[1]))
    return hits[0]


def _mover(frame):
    pcs = _comps(frame, ('p', 'Y'))
    play = [(v, px) for v, px in pcs if min(r for (r, c) in px) >= 10]
    play.sort(key=lambda t: (-len(t[1]), t[1][0]))
    if play:
        return play[0]
    return None


def plan_program(frame):
    try:
        bal = _ball(frame)
        mv = _mover(frame)
        if bal is None or mv is None:
            return {"status": "abstain",
                    "goal": "deliver the pink/purple piece onto the isolated S ball below row 10",
                    "actions": [], "evidence_pixels": [], "replaces": [],
                    "reason": "could not recover both a play-area mover piece and an isolated S ball from this frame"}
        v, px = mv
        a, b = _center(px)
        nxt = _toward((a, b), bal, 7.0)
        pts = _footprint(px) + [bal]
        ev = [[r, c, _rows(frame)[r][c]] for (r, c) in pts]
        return {"status": "ready",
                "goal": "step the merged %s piece at (%d,%d) one <=7 move toward ball %s" % (
                    v, int(round(a)), int(round(b)), bal),
                "actions": [{"action": "MOUSE", "row": nxt[0], "col": nxt[1]}],
                "evidence_pixels": ev,
                "replaces": ["route", "click", "state", "invaders"],
                "reason": "merged piece exists in the play area; command it toward the ball and re-plan from the real new frame"}
    except Exception:
        return {"status": "abstain",
                "goal": "deliver a pink/purple piece onto the isolated S ball below row 10",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "could not recompute the mover piece and ball from this frame"}


def predict(frame, action):
    try:
        ad = action.get('action_data') or {}
        r0 = ad.get('row', action.get('row'))
        c0 = ad.get('col', action.get('col'))
        if r0 is None or c0 is None:
            return {"mode": "unknown", "reason": "action has no row/col"}
        rows = _rows(frame)
        bal = _ball(frame)
        mv = _mover(frame)
        if bal is None or mv is None:
            return {"mode": "unknown", "reason": "no ball or no play-area mover piece to relate the click to"}
        v, px = mv
        a, b = _center(px)
        pts = _footprint(px)
        obj = [[r, c, rows[r][c]] for (r, c) in pts]
        tgt = [[bal[0], bal[1], rows[bal[0]][bal[1]]]]
        inrange = any(abs(r - r0) <= 8 and abs(c - c0) <= 8 for (r, c) in px)
        if not inrange:
            exp = obj + tgt
            return {"mode": "noop", "action": action,
                    "object_pixels": obj,
                    "target_pixels": tgt,
                    "expected_pixels": exp,
                    "precondition": "the click lies more than 8 cells from every cell of the mover piece, so no piece can be commanded there and nothing on the piece or the ball should change",
                    "scope": "mover piece %s and the S ball: verifies only in-range clicks command the piece" % v}
        nxt = _toward((a, b), bal, 7.0)
        dr = nxt[0] - int(round(a))
        dc = nxt[1] - int(round(b))
        exp = []
        for (r, c) in pts:
            rr2 = r + dr
            cc2 = c + dc
            if 0 <= rr2 < len(rows) and 0 <= cc2 < len(rows[rr2]):
                exp.append([rr2, cc2, v])
            else:
                exp.append([r, c, v])
        exp.append([bal[0], bal[1], rows[bal[0]][bal[1]]])
        return {"mode": "change", "action": action,
                "object_pixels": obj,
                "target_pixels": tgt,
                "expected_pixels": exp,
                "precondition": "the click lies within 8 cells of the mover piece, so it should translate toward the ball by up to 7 cells; the ball stays until the piece lands on it",
                "scope": "the mover piece footprint after the step plus the S ball pixel, checking the piece approaches the ball"}
    except Exception:
        return {"mode": "unknown", "reason": "could not relate this click to a current piece"}
