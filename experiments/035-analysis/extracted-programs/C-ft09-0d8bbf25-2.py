def plan_program(frame):
    rows = frame.ascii.splitlines()
    # Grid cell positions: row_bands = [4,12,20,28,36,44,52], col_bands = [12,20,28,36,44]
    # Each cell is 6x6 pixels. Patterns at (1,2),(3,1),(3,3),(5,2) in grid coords.
    # Rule A: In each pattern legend, W -> center color, g -> other color (R<->O).
    # Pattern at (1,2) center O: W->O, g->R. Neighbors should be:
    #   (0,1)=O,(0,2)=O,(0,3)=O,(1,1)=O,(1,3)=R,(2,1)=R,(2,2)=O,(2,3)=R
    # Pattern at (3,1) center R: W->R, g->O. All match.
    # Pattern at (3,3) center R: W->R, g->O. All match.
    # Pattern at (5,2) center O: W->O, g->R. Neighbors should be:
    #   (4,1)=R,(4,2)=O,(4,3)=R,(5,1)=O,(5,3)=R,(6,1)=O,(6,2)=O,(6,3)=O
    # Current (0,1) is R but should be O -> click to toggle.
    # Current (5,3) is O but should be R -> click to toggle.
    # Grid (0,1) center: row=6, col=22. Grid (5,3) center: row=46, col=38.
    # Verify current colors:
    c01 = rows[6][22]  # should be R (needs toggle to O)
    c53 = rows[46][38]  # should be O (needs toggle to R)
    if c01 == 'R' and c53 == 'O':
        actions = [
            {"action": "MOUSE", "row": 6, "col": 22},
            {"action": "MOUSE", "row": 46, "col": 38}
        ]
    elif c01 == 'R':
        actions = [{"action": "MOUSE", "row": 6, "col": 22}]
    elif c53 == 'O':
        actions = [{"action": "MOUSE", "row": 46, "col": 38}]
    else:
        return {"status": "completed", "goal": "All cells match pattern legends",
                "actions": [], "evidence_pixels": [[6,22,'O'],[46,38,'R']],
                "replaces": ["r1","d1","cc","cur"], "reason": "All mismatches resolved"}
    ev = []
    for r in range(4,10):
        for c in range(20,26):
            ev.append([r, c, rows[r][c]])
    for r in range(44,50):
        for c in range(36,42):
            ev.append([r, c, rows[r][c]])
    return {"status": "ready",
            "goal": "Toggle (0,1) R->O and (5,3) O->R to satisfy pattern legends",
            "actions": actions,
            "evidence_pixels": ev,
            "replaces": ["r1","d1","cc","cur"],
            "reason": "Pattern at (1,2) center O requires (0,1)=O but it is R; pattern at (5,2) center O requires (5,3)=R but it is O"}


def predict(frame, action):
    rows = frame.ascii.splitlines()
    r_click = action.get("row", 0)
    c_click = action.get("col", 0)
    # Determine which grid cell was clicked
    row_bands = [4, 12, 20, 28, 36, 44, 52]
    col_bands = [12, 20, 28, 36, 44]
    gr = None
    gc = None
    for i, rb in enumerate(row_bands):
        if rb <= r_click <= rb + 5:
            gr = i
            break
    for j, cb in enumerate(col_bands):
        if cb <= c_click <= cb + 5: