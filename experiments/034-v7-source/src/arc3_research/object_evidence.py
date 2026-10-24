"""Exact component geometry and bounded public transition observations.

The callable is deliberately self-contained: the native child sandbox embeds
its source, while host context construction invokes the same implementation.
It names no game, role, interactive region, color meaning or grid pitch.
"""


def object_evidence(ascii, transition_records):
    """Return current same-color four-connected components, never role labels.

    ``transition_records`` contains at most two oldest-to-newest dictionaries
    with action, before_ascii, after_ascii, before_level and after_level.
    Component ids are assigned again on each call in row-major discovery order;
    they are not identities across frames. All coordinates are zero-based and
    bbox/run endpoints are inclusive. A filled rectangle uses bbox alone;
    otherwise complete horizontal runs specify its exact footprint.

    Per-transition counts project those *current* footprints onto the recorded
    screen coordinates. They do not establish object identity, motion, causal
    effect or interactivity. A zero count never implies a UI role. Boundaries
    supply no effects. No component/run is silently dropped to fit a bound.
    """
    import json
    import re

    max_pixels = 4096
    max_total_pixels = 20480  # current plus two pairs of 64x64 public frames
    max_json_characters = 24000

    def unavailable(reason):
        return {"status": "unavailable", "reason": reason}

    def rows_of(text):
        if not isinstance(text, str) or not text or len(text) > 8192:
            return None
        rows = text.splitlines()
        if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
            return None
        if len(rows) * len(rows[0]) > max_pixels:
            return None
        return rows

    rows = rows_of(ascii)
    if rows is None:
        return unavailable("current frame is not a nonempty rectangle of at most 4096 pixels")
    if not isinstance(transition_records, (list, tuple)) or len(transition_records) > 2:
        return unavailable("at most two oldest-to-newest transition records are required")
    records = []
    total_pixels = len(rows) * len(rows[0])
    for record in transition_records:
        if not isinstance(record, dict):
            return unavailable("transition record is not a dictionary")
        action = record.get("action")
        if not isinstance(action, str) or len(action) > 256:
            return unavailable("transition action must be a string of at most 256 characters")
        before, after = rows_of(record.get("before_ascii")), rows_of(record.get("after_ascii"))
        if before is None or after is None:
            return unavailable("transition frame missing, malformed or over 4096 pixels")
        levels = (record.get("before_level"), record.get("after_level"))
        if any(value is not None and type(value) is not int for value in levels):
            return unavailable("transition levels must be integers or unknown")
        total_pixels += len(before) * len(before[0]) + len(after) * len(after[0])
        if total_pixels > max_total_pixels:
            return unavailable("total public-frame pixels exceed 20480")
        records.append((record, before, after))

    height, width = len(rows), len(rows[0])
    labels = [[-1] * width for _ in rows]
    components = []
    for row in range(height):
        for col in range(width):
            if labels[row][col] != -1:
                continue
            component_id = len(components)
            color = rows[row][col]
            pending, cells = [(row, col)], []
            labels[row][col] = component_id
            while pending:
                r, c = pending.pop()
                cells.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if (0 <= nr < height and 0 <= nc < width and
                            labels[nr][nc] == -1 and rows[nr][nc] == color):
                        labels[nr][nc] = component_id
                        pending.append((nr, nc))
            cells.sort()
            r0, r1 = cells[0][0], cells[-1][0]
            c0, c1 = min(c for r, c in cells), max(c for r, c in cells)
            rectangle = len(cells) == (r1 - r0 + 1) * (c1 - c0 + 1)
            component = {"id": component_id, "color": color,
                         "pixel_count": len(cells), "bbox": [r0, c0, r1, c1],
                         "rect": rectangle}
            if not rectangle:
                runs = []
                for r, c in cells:
                    if runs and runs[-1][0] == r and runs[-1][2] == c - 1:
                        runs[-1][2] = c
                    else:
                        runs.append([r, c, c])
                component["runs"] = runs
            components.append(component)

    # Infer the current level only when the most recent recorded after-frame
    # exactly equals the supplied current frame. Otherwise it is unknown.
    current_level = None
    if records and records[-1][2] == rows:
        current_level = records[-1][0].get("after_level")
    recent = []
    for record, before, after in records:
        entry = {"action": record["action"],
                 "before_level": record.get("before_level"),
                 "after_level": record.get("after_level"),
                 "after_is_current": after == rows}
        before_level, after_level = entry["before_level"], entry["after_level"]
        same_shape = (len(before) == height == len(after) and
                      len(before[0]) == width == len(after[0]))
        if (not same_shape or (before_level is not None and after_level is not None and
                               before_level != after_level) or
                (current_level is not None and after_level is not None and
                 current_level != after_level)):
            entry.update({"status": "boundary", "effects": "unknown"})
            recent.append(entry)
            continue
        if before_level is None or after_level is None:
            entry.update({"status": "unknown_level", "effects": "unknown"})
            recent.append(entry)
            continue
        counts = [0] * len(components)
        for r in range(height):
            for c in range(width):
                if before[r][c] != after[r][c]:
                    counts[labels[r][c]] += 1
        entry.update({"status": "observed_screen_overlap",
                      "changed_pixels": sum(counts),
                      "changed_by_component": [[i, count] for i, count in enumerate(counts) if count]})
        click = re.fullmatch(r"MOUSE\(row=(-?\d+),\s*col=(-?\d+)\)", record["action"])
        entry["click"] = "unavailable_or_non_mouse"
        if click:
            r, c = int(click.group(1)), int(click.group(2))
            if 0 <= r < height and 0 <= c < width:
                entry["click"] = {"row": r, "col": c,
                                  "current_component_at_coordinate": labels[r][c],
                                  "before_color": before[r][c], "after_color": after[r][c]}
            else:
                entry["click"] = "out_of_frame"
        recent.append(entry)

    result = {
        "status": "available", "shape": [height, width],
        "coordinates": "zero-based row,col; bbox=[r0,c0,r1,c1], endpoints inclusive",
        "geometry": "rect=true: every pixel in bbox; rect=false: complete runs=[row,c0,c1], inclusive",
        "id_scope": "current frame only; row-major same-color 4-connectivity; recompute on every frame",
        "support_scope": "current footprints projected onto recorded screen coordinates; no tracked identity, motion, causality, role or interactivity; missing changed_by_component id means zero; unchanged does not imply UI",
        "components": components, "recent": recent,
    }
    if len(json.dumps(result, ensure_ascii=True, separators=(",", ":"))) > max_json_characters:
        return unavailable("complete component evidence exceeds 24000 JSON characters; none truncated")
    return result
