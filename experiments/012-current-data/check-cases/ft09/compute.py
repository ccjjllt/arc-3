def compute_measurement(frame):
    # Select a lattice from the most common solid-square component size.
    # This is a diagnostic extractor for the saved frame, not a general solver.
    squares = []
    sizes = {}
    for node in frame.segmentation["nodes"]:
        boundary = node.get("boundary", [])
        if not boundary:
            continue
        top = min(point[0] for point in boundary)
        bottom = max(point[0] for point in boundary)
        left = min(point[1] for point in boundary)
        right = max(point[1] for point in boundary)
        height, width = bottom - top + 1, right - left + 1
        if height == width and height >= 3 and node["pixels"] == height * width:
            squares.append([top, left, height])
            sizes[height] = sizes.get(height, 0) + 1
    if not sizes:
        return {"status": "no_lattice", "step": frame.step, "level": frame.level}
    size = max(sizes, key=sizes.get)
    anchors = [item for item in squares if item[2] == size]
    row_starts = sorted(set(item[0] for item in anchors))
    col_starts = sorted(set(item[1] for item in anchors))
    rows = frame.ascii.splitlines()
    frequency = {}
    for row in rows:
        for symbol in row:
            frequency[symbol] = frequency.get(symbol, 0) + 1
    background = max(frequency, key=frequency.get)
    mixed = []
    for top in row_starts:
        for left in col_starts:
            symbols = set("".join(rows[r][left:left + size]
                                  for r in range(top, top + size)))
            if len(symbols) > 1 and background not in symbols:
                mixed.append({
                    "pixel_top_left": [top, left],
                    "logical_row_col": [row_starts.index(top), col_starts.index(left)],
                })
    if not mixed:
        return {"status": "no_mixed_tile", "step": frame.step, "level": frame.level}
    selected = min(mixed, key=lambda item: item["pixel_top_left"])
    return {
        "status": "measured",
        "step": frame.step,
        "level": frame.level,
        "square_size": size,
        "row_starts": row_starts,
        "col_starts": col_starts,
        "selection": "topmost mixed tile in the inferred lattice",
        "selected": selected,
    }


measurement = compute_measurement(current_frame)
