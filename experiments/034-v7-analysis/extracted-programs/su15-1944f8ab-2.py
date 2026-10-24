import math

def _grid(frame):
    a = frame.ascii
    if isinstance(a, str):
        return [list(r) for r in a.split("\n") if r]
    return [list(r) for r in a]


def _walk(g, r, c, color):
    seen = set()
    stack = [(r, c)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < len(g) and 0 <= x < len(g[0]):
            if g[y][x] == color and (y, x) not in seen:
                seen.add((y, x))
                stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return seen


def _invaders(g):
    out = []
    for r in range(len(g)):
        for c in range(len(g[0])):
            if g[r][c] == "P" and (r, c) not in out:
                out.extend(_walk(g, r, c, "P"))
    return set(out)


def _blob(g, color, r0, r1):
    best = None
    for r in range(max(0, r0), min(len(g), r1)):
        for c in range(len(g[0])):
            if g[r][c] == color:
                comp = _walk(g, r, c, color)
                if best is None or len(comp) > len(best):
                    best = comp
    return best or set()


def _center(comp):
    rs = [p[0] for p in comp]
    cs = [p[1] for p in comp]
    return (sum(rs) / len(rs), sum(cs) / len(cs))


def _pawns(g):
    out = []
    for r in range(10, len(g)):
        for c in range(len(g[0])):
            if g[r][c] in ("Y", "p"):
                comp = _walk(g, r, c, g[r][c])
                if comp and all(p[0] >= 10 for p in comp):
                    out.append((g[r][c], comp))
    return out


def _targets(g):
    out = []
    for r in range(10, len(g)):
        for c in range(len(g[0])):
            if g[r][c] in ("S", "b"):
                comp = _walk(g, r, c, g[r][c])
                if comp:
                    out.append((g[r][c], comp))
    return out


def _pick(pieces):
    tgt = [t for t in _targets(_GRID) if t[0] == "S"] or _targets(_GRID)
    if not tgt or not pieces:
        return None
    tc = _center(max(tgt, key=lambda t: len(t[1]))[1])
    def far(p):
        pc = _center(p[1])
        d = math.hypot(pc[0] - tc[0], pc[1] - tc[1])
        return (d, -len(p[1]))
    return max(pieces, key=far)


_GRID = None


def plan_program(frame):
    global _GRID
    g = _grid(frame)
    _GRID = g
    pcs = _pawns(g)
    if not pcs:
        return {"status": "abstain", "goal": "no movable pawn below row 10",
                "actions": [], "evidence_pixels": [], "replaces": ["route"],
                "reason": "no Y/p component below the legend band to move"}
    inv = _invaders(g)
    tgt = [t for t in _targets(g) if t[0] == "S"] or _targets(g)
    if not tgt:
        return {"status": "abstain", "goal": "no S/b target below row 10",
                "actions": [], "evidence_pixels": [], "replaces": ["route"],
                "reason": "no target blob found"}
    tc = _center(max(tgt, key=lambda t: len(t[1]))[1])
    piece = max(pcs, key=lambda p: (math.hypot(*[x - y for x, y in
                              zip(_center(p[1]), tc)]), -len(p[1])))
    pc = _center(piece[1])
    if piece[0] == "p" and len([p for p in pcs if p[0] == "p"]) > 1:
        other = max([p for p in pcs if p[0] == "p" and p is not piece],
                    key=lambda p: len(p[1]))
        oc = _center(other[1])
        mid = ((pc[0] + oc[0]) / 2.0, (pc[1] + oc[1]) / 2.0)
        goal = "merge the two p components toward the S target"
        best = (mid[0], mid[1], 0.0)
        for rr in range(10, len(g) - 1):
            for cc in range(len(g[0]) - 1):
                d1 = math.hypot(rr - pc[0], cc - pc[1])
                d2 = math.hypot(rr - oc[0], cc - oc[1])
                if d1 <= 8.0 and d2 <= 8.0:
                    s = -max(d1, d2) - 0.3 * math.hypot(rr - tc[0], cc - tc[1])
                    if s > best[2]:
                        best = (rr, cc, s)
        act = [{"action": "MOUSE", "row": int(best[0]), "col": int(best[1])}]
        why = "two pawns of color p remain; merge click within 8 of both"
    else:
        goal = "walk the %s pawn onto the S target at %.1f,%.1f" % (
            piece[0], tc[0], tc[1])
        step = (pc[0] + 7.0 * (tc[0] - pc[0]) / max(1e-9, math.hypot(
            tc[0] - pc[0], tc[1] - pc[1])),
            pc[1] + 7.0 * (tc[1] - pc[1]) / max(1e-9, math.hypot(
            tc[0] - pc[0], tc[1] - pc[1])))
        best = (step[0], step[1], -1e9)
        for rr in range(10, len(g) - 1):
            for cc in range(len(g[0]) - 1):
                if g[rr][cc] not in ("B", "b"):
                    continue
                d = math.hypot(rr - pc[0], cc - pc[1])
                if d < 5.0 or d > 7.6:
                    continue
                s = -math.hypot(rr - tc[0], cc - tc[1]) - 0.6 * min(
                    [math.hypot(rr - ir, cc - ic) for ir, ic in inv] or [99])
                if s > best[2]:
                    best = (rr, cc, s)
        act = [{"action": "MOUSE", "row": int(best[0]), "col": int(best[1])}]
        why = "single pawn: step toward S while avoiding P cells"
    ev = [[r, c, g[r][c]] for r, c in sorted(piece[1])][:12]
    ev += [[r, c, g[r][c]] for r, c in sorted(max(tgt, key=lambda t: len(t[1]))[1])][:12]
    return {"status": "ready", "goal": goal, "actions": act,
            "evidence_pixels": ev,
            "replaces": ["route", "safe", "safe2", "safe3", "invaders", "state"],
            "reason": why}


def predict(frame, action):
    g = _grid(frame)
    pcs = _pawns(g)
    if not pcs or action.get("action") != "MOUSE":
        return {"mode": "unknown", "reason": "no pawn or non-MOUSE action"}
    inv = _invaders(g)
    tgt = [t for t in _targets(g) if t[0] == "S"] or _targets(g)
    tc = _center(max(tgt, key=lambda t: len(t[1]))[1]) if tgt else (32.0, 32.0)
    piece = max(pcs, key=lambda p: (math.hypot(*[x - y for x, y in
                              zip(_center(p[1]), tc)]), -len(p[1])))
    pc = _center(piece[1])
    rr, cc = action.get("row", 0), action.get("col", 0)
    d = math.hypot(rr - pc[0], cc - pc[1])
    if d > 8.5:
        return {"mode": "noop", "action": action,
                "object_pixels": [[r, c, g[r][c]] for r, c in sorted(piece[1])],
                "target_pixels": [], "expected_pixels": [],
                "precondition": "click is %.1f from the pawn, beyond the 8-cell reach" % d,
                "scope": "pawn " + piece[0] + " should not move"}
    if piece[0] == "p" and len([p for p in pcs if p[0] == "p"]) > 1:
        other = max([p for p in pcs if p[0] == "p" and p is not piece],
                    key=lambda p: len(p[1]))
        oc = _center(other[1])
        if math.hypot(rr - oc[0], cc - oc[1]) > 8.5:
            return {"mode": "noop", "action": action,
                    "object_pixels": [[r, c, g[r][c]] for r, c in sorted(piece[1])],
                    "target_pixels": [[r, c, g[r][c]] for r, c in sorted(other[1])],
                    "expected_pixels": [],
                    "precondition": "merge needs one click within 8 of both p pawns",
                    "scope": "p-pair merge"}
        rows = range(max(0, rr - 2), min(63, rr + 3))
        cols = range(max(0, cc - 2), min(63, cc + 3))
        exp = [[r, c, "Y"] for r in rows for c in cols]
        src = [[r, c, g[r][c]] for r, c in sorted(piece[1] | other[1])]
        return {"mode": "change", "action": action,
                "object_pixels": src, "target_pixels": [],
                "expected_pixels": exp,
                "precondition": "one click within 8 of both p pawns fuses them",
                "scope": "p-pair merge into a single Y pawn"}
    tset = max(tgt, key=lambda t: len(t[1]))[1] if tgt else set()
    tpix = [[r, c, g[r][c]] for r, c in sorted(tset)]
    exp = [[r, c, "Y"] for r, c in sorted(tset)]
    near = any(math.hypot(rr - r, cc - c) <= 2.0 for r, c in tset)
    if near:
        return {"mode": "change", "action": action,
                "object_pixels": [[r, c, g[r][c]] for r, c in sorted(piece[1])],
                "target_pixels": tpix, "expected_pixels": exp,
                "precondition": "pawn reaches the S target cell, completing the level",
                "scope": "pawn " + piece[0] + " delivered onto S target"}
    return {"mode": "change", "action": action,
            "object_pixels": [[r, c, g[r][c]] for r, c in sorted(piece[1])],
            "target_pixels": tpix,
            "expected_pixels": [[r, c, g[r][c]] for r, c in sorted(tset)],
            "precondition": "click within 8 relocates the pawn; P cells untouched",
            "scope": "pawn " + piece[0] + " relocation toward S target"}