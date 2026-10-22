import math

def _grid(frame):
    a = getattr(frame, "ascii", None)
    if a is None:
        a = getattr(frame, "ascii_map", "")
    rows = [list(r) for r in a.split("\n")]
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def _shape(frame):
    sh = getattr(frame, "shape", None)
    if sh:
        return int(sh[0]), int(sh[1])
    g = _grid(frame)
    return len(g), (len(g[0]) if g else 0)


def _morph(g, r0, r1, c0, c1):
    if not g:
        return False
    R, C = len(g), len(g[0])
    r0 = max(0, r0)
    c0 = max(0, c0)
    r1 = min(R - 1, r1)
    c1 = min(C - 1, c1)
    vals = set()
    for r in range(r0, r1 + 1):
        row = g[r]
        for c in range(c0, c1 + 1):
            vals.add(row[c])
    return len(vals) == 1


def _target_pair(g):
    pair = []
    for r in range(len(g)):
        for c in range(len(g[r])):
            if g[r][c] == "p":
                pair.append((r, c))
    return pair


def _solid_rect(g, ch, r0, r1, c0, c1):
    if not g:
        return False
    R, C = len(g), len(g[0])
    if r0 < 0 or c0 < 0 or r1 >= R or c1 >= C:
        return False
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if g[r][c] != ch:
                return False
    return True


def _candidates(frame):
    g = _grid(frame)
    out = []
    pair = _target_pair(g)
    if len(pair) >= 2:
        pr = pair[0][0]
        pc = min(c for (r, c) in pair)
        if _solid_rect(g, "p", pr, pr + 1, pc, pc + 1):
            for dr in (-9, -8, -7, 7, 8, 9):
                rr = pr + dr
                if 0 <= rr < len(g):
                    if _morph(g, rr, rr + 1, pc, pc + 1):
                        out.append((rr, pc, "uniform-2x2-block"))
        if _solid_rect(g, "p", pr, pr + 1, pc, pc + 1):
            for dr in (-8, 8):
                rr = pr + dr
                if 0 <= rr < len(g) and _solid_rect(g, "Y", rr, rr + 1, pc, pc + 1):
                    out.insert(0, (rr, pc, "yellow-2x2-pad"))
    blob = [(r, c) for r in range(len(g)) for c in range(len(g[r])) if g[r][c] == "b"]
    if blob:
        br = min(r for (r, c) in blob)
        bc = min(c for (r, c) in blob)
        for dc in (-16, 0, 16):
            cc = bc + dc
            if 0 <= cc < len(g[0]) and _morph(g, br, br + 1, cc, cc + 1):
                out.append((br, cc, "uniform-2x2-under-blob"))
    seen = set()
    res = []
    for it in out:
        if it[:2] not in seen:
            seen.add(it[:2])
            res.append(it)
    return res


def _valid(frame):
    va = getattr(frame, "valid_actions", []) or []
    names = []
    for v in va:
        if isinstance(v, dict):
            names.append(str(v.get("action_name") or v.get("name") or v.get("action") or ""))
        else:
            names.append(str(v))
    return names


def plan_program(frame):
    g = _grid(frame)
    R, C = _shape(frame)
    cands = _candidates(frame)
    names = _valid(frame)
    pair = _target_pair(g)
    ev = [[r, c, g[r][c]] for (r, c) in pair[:4]]
    for (r, c, how) in cands[:2]:
        ev += [[r, c, g[r][c]], [r + 1, c, g[r + 1][c]]]
    if "MOUSE" not in names:
        return {"status": "abstain",
                "goal": "MOUSE action unavailable this frame",
                "actions": [],
                "evidence_pixels": ev,
                "replaces": ["route", "click", "invaders", "state"],
                "reason": "valid_actions lacks MOUSE; cannot act."}
    if not cands:
        return {"status": "abstain",
                "goal": "no uniform 2x2 landing cell adjacent to the pink pair target",
                "actions": [],
                "evidence_pixels": ev,
                "replaces": ["route", "click", "invaders", "state"],
                "reason": "No candidate 2x2 region matching the pink-pair footprint is currently uniform, so a click there would be a no-op."}
    r, c, how = cands[0]
    act = {"action": "MOUSE", "row": r, "col": c}
    goal = ("drop the pink 2x2 piece from rows %d-%d cols %d-%d onto the "
            "uniform 2x2 region at rows %d-%d cols %d-%d (%s)"
            % (pair[0][0], pair[0][0] + 1, min(x[1] for x in pair),
               max(x[1] for x in pair), r, r + 1, c, how))
    return {"status": "ready",
            "goal": goal,
            "actions": [act],
            "evidence_pixels": ev,
            "replaces": ["route", "click", "invaders", "state"],
            "reason": "Paused planner used fixed route coordinates from an earlier level; recomputed the landing cell from this frame by requiring the target 2x2 region to be a single uniform color (prior fixed-coordinate clicks landed on non-uniform cells and produced no gameplay change)."}


def predict(frame, action):
    g = _grid(frame)
    R, C = _shape(frame)
    if not isinstance(action, dict) or str(action.get("action")) != "MOUSE":
        return {"mode": "unknown", "reason": "only MOUSE clicks are predicted"}
    try:
        r = int(action.get("row"))
        c = int(action.get("col"))
    except Exception:
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [], "precondition": "missing row/col",
                "scope": "none"}
    if r < 0 or c < 0 or r >= R or c >= C:
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [], "precondition": "click outside board",
                "scope": "none"}
    cells = [(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)]
    colors = {}
    obj = []
    for (rr, cc) in cells:
        if rr < R and cc < C:
            colors.setdefault(g[rr][cc], []).append((rr, cc))
            obj.append([rr, cc, g[rr][cc]])
    tgt = [[rr, cc, g[rr][cc]] for (rr, cc) in _target_pair(frame)[:4]]
    if len(colors) == 1 and len(obj) == 4:
        ch = list(colors.keys())[0]
        exp = [[rr, cc, ch] for (rr, cc) in obj]
        return {"mode": "change", "action": action,
                "object_pixels": obj,
                "target_pixels": tgt,
                "expected_pixels": exp,
                "precondition": "the 2x2 region under the click is a single uniform color (%s), so it satisfies the flat-surface precondition for placing the selected 2x2 piece" % ch,
                "scope": "checks whether clicking the uniform 2x2 region transfers the pink 2x2 piece there (piece pixels appear at the target and the piece's old pixels clear)"}
    return {"mode": "noop", "action": action,
            "object_pixels": obj,
            "target_pixels": tgt,
            "expected_pixels": [[rr, cc, g[rr][cc]] for (rr, cc) in obj],
            "precondition": "the 2x2 region under the click is not a single uniform color (mixed %s), so no flat landing surface exists and the click is rejected" % "/".join(sorted(colors.keys())),
            "scope": "checks that a click on a non-uniform region leaves the pink piece and the board unchanged"}
