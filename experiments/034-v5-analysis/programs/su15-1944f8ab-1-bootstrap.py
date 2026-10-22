import math


def _grid(frame):
    a = getattr(frame, "ascii", None)
    if a is None:
        a = frame["ascii"]
    return [list(r) for r in a.split("\n")]


def _shape(frame):
    s = getattr(frame, "shape", None)
    if s is None:
        s = (len(_grid(frame)), 0)
    return int(s[0]), int(s[1])


def _bbox(cells):
    rs = [r for r, c in cells]
    cs = [c for r, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def _find(grid, ch):
    cells = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v == ch]
    if not cells:
        return None, []
    return _bbox(cells), cells


def _find_lower(grid, ch, min_row):
    cells = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row)
             if v == ch and r >= min_row]
    if not cells:
        return None, []
    return _bbox(cells), cells


def _center(bb):
    return ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _analyze(frame):
    grid = _grid(frame)
    rows, cols = _shape(frame)
    walls = set()
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v == "B":
                walls.add((r, c))
    blobs = {}
    for ch in ("Y", "S", "M", "p", "P", "b"):
        bb, cells = _find(grid, ch)
        if cells:
            blobs[ch] = (bb, cells)
    pcs = []
    bb, cells = _find(grid, "P")
    if cells:
        seen = set(cells)
        for cell in cells:
            if cell not in seen:
                continue
            stack = [cell]
            comp = []
            seen.discard(cell)
            while stack:
                r, c = stack.pop()
                comp.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (r + dr, c + dc)
                    if n in seen:
                        seen.discard(n)
                        stack.append(n)
            pcs.append(comp)
    balls = []
    for ch in ("S",):
        bb, cells = _find_lower(grid, ch, 10)
        for cell in cells:
            balls.append(cell)
    y = blobs.get("Y")
    if y:
        target = ("deliver Y (4x4 block, top-left %s) onto a silver ball cell" % (y[0],),
                  y[1], balls)
    else:
        ps = [c for c in blobs.get("p", ([], []))[1]]
        target = ("merge pink p pieces into a Y, then deliver to a ball", ps, balls)
    return grid, rows, cols, walls, blobs, pcs, balls, target


def plan_program(frame):
    grid, rows, cols, walls, blobs, pcs, balls, (goal, objs, targets) = _analyze(frame)
    if not targets:
        return {"status": "abstain", "goal": goal, "actions": [],
                "evidence_pixels": [[r, c, grid[r][c]] for r, c in objs[:6]],
                "replaces": ["route", "click", "invaders", "state"],
                "reason": "no silver ball target visible in current frame"}
    if "Y" in blobs:
        ybb, ycells = blobs["Y"]
        yc = _center(ybb)
        ball = min(targets, key=lambda b: _dist(yc, b))
        br, bc = ball
        # invader threat: nearest P pixel to the Y block
        threat = None
        if pcs:
            allp = [c for comp in pcs for c in comp]
            threat = min((_dist(_center(_bbox(comp)), yc), comp) for comp in pcs)[1]
        # greedy step toward the ball, avoiding walls, max step ~7
        best = None
        for dr in range(-8, 9):
            for dc in range(-8, 9):
                nr, nc = int(round(yc[0] + dr)), int(round(yc[1] + dc))
                if not (0 <= nr < rows - 1 and 0 <= nc < cols):
                    continue
                d = _dist(yc, (nr, nc))
                if d < 2.0 or d > 7.6:
                    continue
                blk = [(nr + i, nc + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]
                if any(b in walls for b in blk):
                    continue
                gain = _dist(yc, ball) - _dist((nr, nc), ball)
                if gain <= 0:
                    continue
                score = gain - 0.25 * d
                if threat:
                    tc = _center(_bbox(threat))
                    after = min(_dist((nr + i, nc + j), tc) for i in (-1, 0, 1) for j in (-1, 0, 1))
                    if after < 3.0:
                        score -= 5.0
                if best is None or score > best[0]:
                    best = (score, nr, nc)
        if best is None:
            return {"status": "abstain", "goal": goal, "actions": [],
                    "evidence_pixels": [[r, c, grid[r][c]] for r, c in (ycells[:4] + targets[:2])],
                    "replaces": ["route", "click", "invaders", "state"],
                    "reason": "Y exists but no wall-free improving step found"}
        _, nr, nc = best
        act = {"action": "MOUSE", "row": nr, "col": nc}
        return {"status": "ready", "goal": goal + " (ball at %d,%d)" % (br, bc),
                "actions": [act],
                "evidence_pixels": ([[r, c, "Y"] for r, c in ycells[:4]] +
                                    [[br, bc, grid[br][bc]]] +
                                    ([[threat[0][0], threat[1][0], "P"]] if threat else [])),
                "replaces": ["route", "click", "invaders", "state"],
                "reason": "step Y block toward nearest ball center (%d,%d), max ~7 cell hop, "
                          "avoiding blue walls and the pink invader" % (br, bc)}
    # no Y yet: try to merge p pieces (click within 8 of two of them)
    pc = blobs.get("p")
    if pc:
        pcells = pc[1]
        comps = []
        seen = set(pcells)
        for cell in pcells:
            if cell not in seen:
                continue
            stack = [cell]
            comp = []
            seen.discard(cell)
            while stack:
                r, c = stack.pop()
                comp.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (r + dr, c + dc)
                    if n in seen:
                        seen.discard(n)
                        stack.append(n)
            comps.append(_center(_bbox(comp)))
        if len(comps) >= 2:
            best = None
            for r in range(10, rows - 1):
                for c in range(cols):
                    if (r, c) in walls:
                        continue
                    ds = sorted(_dist((r, c), p) for p in comps)
                    if ds[1] > 8.0:
                        continue
                    ball = min(targets, key=lambda b: _dist((r, c), b))
                    score = -ds[1] - 0.4 * _dist((r, c), ball)
                    if best is None or score > best[0]:
                        best = (score, r, c)
            if best:
                _, r, c = best
                return {"status": "ready",
                        "goal": "merge two pink p clusters into a Y (click within 8 of both)",
                        "actions": [{"action": "MOUSE", "row": r, "col": c}],
                        "evidence_pixels": [[r, c, grid[r][c]]] +
                                           [[pcells[0][0], pcells[0][1], "p"]],
                        "replaces": ["route", "click", "invaders", "state"],
                        "reason": "no Y on board; click equidistant point to fuse p clusters"}
    return {"status": "abstain", "goal": goal, "actions": [],
            "evidence_pixels": [[r, c, grid[r][c]] for r, c in targets[:3]],
            "replaces": ["route", "click", "invaders", "state"],
            "reason": "no movable Y or mergeable p pieces recovered from this frame"}


def predict(frame, action):
    grid, rows, cols, walls, blobs, pcs, balls, (goal, objs, targets) = _analyze(frame)
    if not isinstance(action, dict) or action.get("action") != "MOUSE":
        return {"mode": "unknown", "reason": "only MOUSE moves are modeled"}
    r = action.get("row")
    c = action.get("col")
    if r is None or c is not None and (not (0 <= int(r) < rows and 0 <= int(c) < cols)):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click outside the playable grid is ignored",
                "scope": "none"}
    r, c = int(r), int(c)
    if "Y" in blobs:
        ybb, ycells = blobs["Y"]
        yc = _center(ybb)
        if _dist(yc, (r, c)) > 8.5:
            return {"mode": "noop", "action": action,
                    "object_pixels": [[x, y, "Y"] for x, y in ycells[:4]],
                    "target_pixels": [[b[0], b[1], grid[b[0]][b[1]]] for b in targets[:2]],
                    "expected_pixels": [[x, y, "Y"] for x, y in ycells[:4]],
                    "precondition": "click is beyond the ~8-cell reach of the Y block, so it cannot move",
                    "scope": "Y delivery: no relocation, ball untouched"}
        ball = min(targets, key=lambda b: _dist((r, c), b)) if targets else None
        if ball and _dist((r, c), ball) <= 1.5:
            return {"mode": "change", "action": action,
                    "object_pixels": [[x, y, "Y"] for x, y in ycells[:4]],
                    "target_pixels": [[ball[0], ball[1], grid[ball[0]][ball[1]]]],
                    "expected_pixels": [[ball[0] + i, ball[1] + j, "Y"]
                                        for i in (-1, 0, 1) for j in (-1, 0, 1)
                                        if 0 <= ball[0] + i < rows and 0 <= ball[1] + j < cols],
                    "precondition": "Y lands on the ball cell, which completes the level",
                    "scope": "Y block: delivery to ball, expect level completion"}
        nr, nc = r, c
        exp = [[nr + i, nc + j, "Y"] for i in (-1, 0, 1) for j in (-1, 0, 1)
               if 0 <= nr + i < rows and 0 <= nc + j < cols]
        obj = [[x, y, "Y"] for x, y in ycells[:4]]
        tgt = [[b[0], b[1], grid[b[0]][b[1]]] for b in targets[:2]]
        return {"mode": "change", "action": action,
                "object_pixels": obj,
                "target_pixels": tgt,
                "expected_pixels": exp + [[x, y, "B"] for x, y in ycells[:4]],
                "precondition": "click within reach and off a wall relocates the 4x4 Y block to the clicked center",
                "scope": "Y block: relocation toward the ball, old cells revert to background"}
    if blobs.get("p"):
        pcells = blobs["p"][1]
        return {"mode": "change", "action": action,
                "object_pixels": [[x, y, "p"] for x, y in pcells[:4]],
                "target_pixels": [[b[0], b[1], grid[b[0]][b[1]]] for b in targets[:2]],
                "expected_pixels": [[r + i, c + j, "Y"] for i in (-1, 0, 1) for j in (-1, 0, 1)
                                    if 0 <= r + i < rows and 0 <= c + j < cols],
                "precondition": "click within 8 of two p clusters fuses them into one Y block",
                "scope": "p clusters: merge into a Y piece"}
    return {"mode": "unknown", "reason": "no task object found to predict"}
