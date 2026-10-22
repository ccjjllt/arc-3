import math


def _grid(frame):
    raw = getattr(frame, "ascii", None)
    if raw is None:
        raw = getattr(frame, "ascii_map", None)
    lines = str(raw).splitlines()
    return [list(r) for r in lines]


def _cells(grid):
    if not grid:
        return []
    nr = len(grid)
    nc = len(grid[0])
    used = [[False] * nc for _ in range(nr)]
    out = []
    for r0 in range(0, nr - 5, 6):
        for c0 in range(0, nc - 5, 6):
            if used[r0][c0]:
                continue
            cnt = {}
            for r in range(r0, min(r0 + 6, nr)):
                for c in range(c0, min(c0 + 6, nc)):
                    ch = grid[r][c]
                    cnt[ch] = cnt.get(ch, 0) + 1
            if not cnt:
                continue
            col = max(cnt, key=lambda k: cnt[k])
            if col == "c":
                continue
            out.append({"r0": r0, "c0": c0, "color": col})
    return out


def _distinct(cells):
    return len(set(c["color"] for c in cells))


def _score(frame, grid, r0, c0):
    cells = _cells(grid)
    base = _distinct(cells)
    nr = len(grid)
    nc = len(grid[0])
    after = []
    for c in cells:
        if c["r0"] == r0 and c["c0"] == c0:
            continue
        col = c["color"]
        for r in range(c["r0"], min(c["r0"] + 6, nr)):
            for cc in range(c["c0"], min(c["c0"] + 6, nc)):
                after.append(grid[r][cc])
        for r in range(c["r0"], min(c["r0"] + 6, nr)):
            for cc in range(c["c0"], min(c["c0"] + 6, nc)):
                after.append(c["color"])
    distinct_after = len(set(after)) if after else 0
    near_border = 1 if (r0 <= 0 or c0 <= 0 or r0 + 6 >= nr or c0 + 6 >= nc) else 0
    return (base - distinct_after, near_border, -r0 - c0)


def plan_program(frame):
    grid = _grid(frame)
    nr = len(grid)
    nc = len(grid[0]) if nr else 0
    cells = _cells(grid)
    if not cells:
        return {"status": "abstain", "goal": "no clickable colored cells detected",
                "actions": [], "evidence_pixels": [], "replaces": [],
                "reason": "board has no non-background 6x6 blocks"}
    scored = sorted(cells, key=lambda c: _score(frame, grid, c["r0"], c["c0"]), reverse=True)
    best = scored[0]
    r = min(best["r0"] + 3, nr - 1)
    c = min(best["c0"] + 3, nc - 1)
    ev = []
    for rr in (best["r0"], best["r0"] + 5):
        for cc in (best["c0"], best["c0"] + 5):
            if 0 <= rr < nr and 0 <= cc < nc:
                ev.append([rr, cc, grid[rr][cc]])
    goal = ("remove the 6x6 block at rows %d-%d cols %d-%d currently color %s; "
            "clicking an all-one-color block turns its pixels to background and "
            "lowers the number of distinct colors on the board"
            % (best["r0"], best["r0"] + 5, best["c0"], best["c0"] + 5, best["color"]))
    return {"status": "ready", "goal": goal,
            "actions": [{"action": "MOUSE", "row": r, "col": c}],
            "evidence_pixels": ev,
            "replaces": ["r1", "d1", "cc", "cur", "n", "b", "rs", "cs"],
            "reason": "Recomputed blocks from this frame's ascii. Observed transitions show a click "
                      "inside a uniform 6x6 block repaints that whole block to background 'c' and adds "
                      "one yellow progress pixel on the bottom row, so the local target is a uniform "
                      "block whose removal reduces board color variety (score stayed 2, level not done)."}


def predict(frame, action):
    grid = _grid(frame)
    nr = len(grid)
    nc = len(grid[0]) if nr else 0
    try:
        r = int(action.get("row"))
        c = int(action.get("col"))
    except Exception:
        return {"mode": "unknown", "reason": "action lacks integer row/col for MOUSE"}
    if not (0 <= r < nr and 0 <= c < nc):
        return {"mode": "noop", "action": action, "object_pixels": [], "target_pixels": [],
                "expected_pixels": [],
                "precondition": "click outside the 64x64 board cannot address any task object",
                "scope": "no task object affected"}
    r0 = (r // 6) * 6
    c0 = (c // 6) * 6
    cols = set()
    obj = []
    for rr in range(r0, min(r0 + 6, nr)):
        for cc in range(c0, min(c0 + 6, nc)):
            cols.add(grid[rr][cc])
            obj.append([rr, cc, grid[rr][cc]])
    if len(cols) != 1:
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": [[r, c, grid[r][c]]], "expected_pixels": obj,
                "precondition": "block at rows %d-%d cols %d-%d is mixed (%s), not a removable uniform "
                                "object, so the click is blocked" % (r0, r0 + 5, c0, c0 + 5, sorted(cols)),
                "scope": "matched 6x6 block fails the uniform-color precondition"}
    col = cols.pop()
    if col == "c":
        return {"mode": "noop", "action": action, "object_pixels": obj,
                "target_pixels": [[r, c, "c"]], "expected_pixels": obj,
                "precondition": "block is already background color 'c', nothing to clear",
                "scope": "background block offers no task-object change"}
    exp = [[rr, cc, "c"] for rr in range(r0, min(r0 + 6, nr))
            for cc in range(c0, min(c0 + 6, nc))]
    tgt = [[rr, cc, grid[rr][cc]] for rr in range(r0, min(r0 + 6, nr))
           for cc in range(c0, min(c0 + 6, nc))]
    return {"mode": "change", "action": action, "object_pixels": obj,
            "target_pixels": tgt, "expected_pixels": exp,
            "precondition": "click inside a uniform %s 6x6 block at rows %d-%d cols %d-%d clears it to "
                            "background 'c'" % (col, r0, r0 + 5, c0, c0 + 5),
            "scope": "that 6x6 block disappears and the board's distinct-color count drops"}
