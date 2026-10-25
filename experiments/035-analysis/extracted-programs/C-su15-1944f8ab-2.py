def plan_program(frame):
    rows = frame.ascii.splitlines()
    # Find Y piece (component 6: rows 3-6, cols 30-33)
    # Find ball 'b' (component 8: rows 11-19, cols 28-36)
    # Y center approx (4.5, 31.5), ball center approx (15, 32)
    # Distance ~10.5, max move ~8, so click at (12, 32) to move Y toward ball
    # This tests if Y can cross from 'c' area to 'B' playfield
    
    # Verify Y is still at rows 3-6, cols 30-33
    y_pixels = []
    for r in range(3, 7):
        for c in range(30, 34):
            if rows[r][c] == 'Y':
                y_pixels.append([r, c, 'Y'])
    
    if len(y_pixels) < 16:
        return {"status": "abstain", "goal": "Move Y piece to ball target", "actions": [], "evidence_pixels": y_pixels, "replaces": [], "reason": "Y piece not found at expected location"}
    
    # Verify ball exists
    ball_pixels = []
    for r in range(11, 20):
        for c in range(28, 37):
            if rows[r][c] == 'b':
                ball_pixels.append([r, c, 'b'])
    
    if len(ball_pixels) < 10:
        return {"status": "abstain", "goal": "Move Y piece to ball target", "actions": [], "evidence_pixels": y_pixels, "replaces": [], "reason": "Ball target not found"}
    
    # Click at (12, 32) - distance from Y center (4.5,31.5) is ~7.5, within range 8
    action = {"action": "MOUSE", "row": 12, "col": 32}
    
    return {
        "status": "ready",
        "goal": "Move Y piece from rows 3-6 cols 30-33 toward ball at rows 11-19 cols 28-36 by clicking (12,32)",
        "actions": [action],
        "evidence_pixels": y_pixels + ball_pixels[:5],
        "replaces": ["click", "invaders", "state"],
        "reason": "Y center (4.5,31.5) to ball center (15,32) distance ~10.5 exceeds max move ~8. Click (12,32) at distance ~7.5 to advance Y into playfield overlapping ball."
    }


def predict(frame, action):
    rows = frame.ascii.splitlines()
    
    # Current Y pixels at rows 3-6, cols 30-33
    object_pixels = []
    for r in range(3, 7):
        for c in range(30, 34):
            if rows[r][c] == 'Y':
                object_pixels.append([r, c, 'Y'])
    
    # Target pixels: ball area
    target_pixels = []
    for r in range(11, 20):
        for c in range(28, 37):
            if rows[r][c] == 'b':
                target_pixels.append([r, c, 'b'])
    
    # Expected: Y moves to center (12,32), occupying rows 10-13, cols 30-33
    # Old Y location becomes 'c' (background)
    # New Y location: rows 10-13, cols 30-33 become 'Y'
    expected_pixels = []
    # Old Y pixels should become 'c'
    for r in range(3, 7):
        for c in range(30, 34):
            if rows[r][c] == 'Y':
                expected_pixels.append([r, c, 'c'])
    # New Y pixels should appear
    for r in range(10, 14):
        for c in range(30, 34):
            expected_pixels.append([r, c, 'Y'])
    
    return {
        "mode": "change",
        "action": action,
        "object_pixels": object_pixels,
        "target_pixels": target_pixels,
        "expected_pixels": expected_pixels,
        "precondition": "Y piece at rows 3-6 cols 30-33 can move to clicked point (12,32) which is within max distance ~8 from Y center (4.5,31.5)",
        "scope": "Y active piece moves from c-area into B-playfield, overlapping ball target area at rows 11-13 cols 30-33"
    }
