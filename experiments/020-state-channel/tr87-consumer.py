def equal_color_masks(left, right):
    # Exact comparison. Rotation, reflection and semantic identity are not assumed.
    return left == right

region = current_frame.region((23, 6, 27, 10), foreground="B")
other = current_frame.region((41, 26, 45, 30), foreground="B")
same = equal_color_masks(region.mask, other.mask)
# Select a node derived from current segmentation without transcribing its rectangle.
node = next(node for node in current_frame.segmentation["nodes"]
               if node["color"] == "B" and node["boundary"]
               and max(p[0] for p in node["boundary"]) - min(p[0] for p in node["boundary"]) < 10
               and max(p[1] for p in node["boundary"]) - min(p[1] for p in node["boundary"]) < 10)
node_region = current_frame.region_from_node(node, foreground="B")
result = {"equal": same, "rows": region.raw_rows, "mask": region.mask,
          "sources": [region.source, other.source], "node_source": node_region.source,
          "node_observed_pixel_count": len(node_region.positions()),
          "consumer_input": "two current_frame mask tuples passed directly to comparison"}
