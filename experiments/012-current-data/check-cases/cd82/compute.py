def compute_measurement(frame):
    # Historical diagnostic region/foreground only, not a production game rule.
    rows = frame.ascii.splitlines()
    cells = [(row, col) for row in range(18, 62)
             for col, symbol in enumerate(rows[row]) if symbol == "g"]
    if not cells:
        return {"status": "empty", "step": frame.step, "level": frame.level}
    row_values = [row for row, col in cells]
    col_values = [col for row, col in cells]
    return {
        "status": "measured",
        "step": frame.step,
        "level": frame.level,
        "pixel_count": len(cells),
        "bbox_tlbr_inclusive": [min(row_values), min(col_values),
                                max(row_values), max(col_values)],
    }


measurement = compute_measurement(current_frame)
