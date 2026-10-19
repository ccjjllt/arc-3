def occupied_blocks(cells, origin, block_size, minimum_pixels, color):
    # Generic projection into an explicitly chosen block lattice, not a game solver.
    counts = {}
    for row, values in enumerate(cells):
        for col, value in enumerate(values):
            if value == color:
                block = ((origin[0] + row) // block_size, (origin[1] + col) // block_size)
                counts[block] = counts.get(block, 0) + 1
    return sorted(block for block, count in counts.items() if count >= minimum_pixels)

region = current_frame.region((9, 42, 29, 62), foreground="B")
observed_blocks = occupied_blocks(region.cells, region.origin, 3, 7, "B")
probe = current_frame.region((24, 51, 26, 56), foreground="B")
result = {"observed_blocks": observed_blocks, "source": region.source,
          "probe_source": probe.source, "probe_rows": probe.raw_rows,
          "probe_mask": probe.mask, "probe_positions": probe.positions(),
          "consumer_input": "region.cells and region.origin passed directly; no copied block table"}
