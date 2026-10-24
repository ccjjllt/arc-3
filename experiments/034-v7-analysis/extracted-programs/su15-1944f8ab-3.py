import math

def _grid(frame):
    a = frame.ascii
    if isinstance(a, str):
        return [list(r) for r in a.split("\n") if r]
    return [list(r) for r in a]

def _walk(g, r, c, col):
    seen = set()
    st = [(r, c)]
    H = len(g)
    W = len(g[0])
    while st:
        y, x = st.pop()
        if 0 <= y < H and 0 <= x < W and g[y][x] == col and (y, x) not in seen:
            seen.add((y, x))
            st += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return seen

def _comps(g, cols, r0=10):
    out = []
    seen = set()
    for r in range(r0, len(g)):
        for c in range(len(g[0])):
            if g[r][c] in cols and (r, c) not in seen:
                comp = _walk(g, r, c, g[r][c])
                seen |= comp
                if comp:
                    out.append((g[r][c], comp))
    return out

def _ctr(comp):
    rs = [p[0] for p in comp]
    cs = [p[1] for p in comp]
    return (sum(rs) / len(rs), sum(cs) / len(cs))

def _pick(g):
    pcs = _comps(g, ("Y", "p", "M", "S"))
    pcs = [p for p in pcs if len(p[1]) >= 4]
    tg = [t for t in _comps(g, ("S", "b")) if len(t[1]) >= 4]
    if not pcs or not tg:
        return None
    tgt = max(tg, key=lambda t: len(t[1]))
    tc = _ctr(tgt[1])
    pc = max(pcs, key=lambda p: (math.hypot(*[x - y for x, y in
            zip(_ctr(p[1]), tc)]), -len(p[1])))
    return (pc, tgt, tc)

def _pix(comp):
    return [[r, c, None] for r, c in sorted(comp)]

def plan_program(frame):
    g = _grid(frame)
    sel = _pick(g)
    if sel is None:
        return {"status": "abstain", "goal": "no pawn/target pair below row 10",
                "actions": [], "evidence_pixels": [],
                "replaces": ["route", "click", "invaders", "state"],
                "reason": "no >=4px pawn and >=4px target below the legend band"}
    piece, tgt, tc = sel
    pc = _ctr(piece[1])
    best = (pc[0], pc[1], -1e9)
    for rr in range(10, len(g) - 1):
        for cc in range(len(g[0]) - 1):
            if g[rr][cc] not in ("B", "b", "c"):
                continue
            d = math.hypot(rr - pc[0], cc - pc[1])
            if d < 4.0 or d > 7.6:
                continue
            s = -math.hypot(rr - tc[0], cc - tc[1])
            if s > best[2]:
                best = (rr, cc, s)
    act = [{"action": "MOUSE", "row": int(best[0]), "col": int(best[1])}]
    ev = [[r, c, g[r][c]] for r, c in sorted(piece[1])][:14]
    ev += [[r, c, g[r][c]] for r, c in sorted(tgt[1])][:14]
    return {"status": "ready",
            "goal": "move the %s pawn (center %.1f,%.1f) toward the %s target at %.1f,%.1f"
                    % (piece[0], pc[0], pc[1], tgt[0], tc[0], tc[1]),
            "actions": act, "evidence_pixels": ev,
            "replaces": ["route", "click", "invaders", "state"],
            "reason": "last click within reach relocated the pawn and scored; "
                      "one click toward the largest S/b target"}

def predict(frame, action):
    g = _grid(frame)
    if action.get("action") != "MOUSE":
        return {"mode": "unknown", "reason": "non-MOUSE action"}
    sel = _pick(g)
    if sel is None:
        return {"mode": "unknown", "reason": "no pawn/target pair to model"}
    piece, tgt, tc = sel
    pc = _ctr(piece[1])
    rr = action.get("row", 0)
    cc = action.get("col", 0)
    d = math.hypot(rr - pc[0], cc - pc[1])
    obj = [[r, c, g[r][c]] for r, c in sorted(piece[1])]
    tar = [[r, c, g[r][c]] for r, c in sorted(tgt[1])]
    if d > 8.5:
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": tar, "expected_pixels": [],
                "precondition": "click is %.1f cells from the pawn, past the "
                                "~8-cell relocation reach" % d,
                "scope": "pawn " + piece[0] + " must stay put when out of reach"}
    rows = range(max(0, rr - 3), min(len(g), rr + 4))
    cols = range(max(0, cc - 3), min(len(g[0]), cc + 4))
    exp = [[r, c, piece[0]] for r in rows for c in cols]
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tar, "expected_pixels": exp,
            "precondition": "a MOUSE click within ~8 cells relocates the "
                            "selected pawn to the clicked neighbourhood",
            "scope": "pawn " + piece[0] + " relocation one step toward the "
                     "S/b target region"}
