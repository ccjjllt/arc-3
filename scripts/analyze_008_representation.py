#!/usr/bin/env python3
"""Manual CPU reconstruction of 008 saved-frame cases; no games or model calls.

The coordinates below are labelled historical observations, not solver rules.
Only our own extraction code and the baseline's generic segmentation execute.
Model transcripts are read as text and are never evaluated.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research.observation_representation import ARC_SYMBOLS, RegionReader


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/008-representation")
    args = parser.parse_args()
    sources = {}
    saved_frames = {}
    segmentation_path = ROOT / "research/runtime-bundle/src/ARC3-Inference/inference/utils/segmentation.py"
    spec = importlib.util.spec_from_file_location("arc3_saved_segmentation", segmentation_path)
    segmentation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(segmentation)

    def source(path):
        path = ROOT / path if not isinstance(path, Path) else path
        key = str(path.relative_to(ROOT))
        sources.setdefault(key, {"path": key, "sha256": digest(path)})
        return path

    def event_frame(relative, line):
        path = source(relative)
        with path.open() as handle:
            for number, text in enumerate(handle, 1):
                if number == line:
                    event = json.loads(text)
                    break
            else:
                raise ValueError(f"Missing {path}:{line}")
        ascii_rows = event["board_ascii"].splitlines()
        numeric_rows = ["".join(ARC_SYMBOLS[v] for v in row) for row in event["board"]]
        if ascii_rows != numeric_rows:
            raise ValueError("Saved board/ascii disagree")
        frame = SimpleNamespace(
            ascii="\n".join(ascii_rows), step=event["action_num"], level=event["level"],
            shape=(len(ascii_rows), len(ascii_rows[0])),
            segmentation=segmentation.segment_layer(event["board"], ARC_SYMBOLS),
        )
        evidence = {"path": relative, "line": line, "event_type": event["type"],
                    "event_action_num": event["action_num"], "analysis_step": event["analysis_step"],
                    "frame": RegionReader(lambda: frame).reference()}
        saved_frames[(relative, line)] = frame
        return frame, evidence

    source(segmentation_path)
    for path in ("src/arc3_research/observation_representation.py",
                 "scripts/analyze_008_representation.py",
                 "research/runtime-bundle/src/ARC3-Inference/inference/agent/python_tool_sandbox.py",
                 "research/runtime-bundle/src/ARC3-Inference/inference/utils/grid_utils.py",
                 "research/007-next-direction.md"):
        source(path)

    bpath = "runs/007-program-state/program_state/artifacts/tr87-cd924810_p0_events.jsonl"
    apath = "runs/007-program-state/baseline/artifacts/tr87-cd924810_p0_events.jsonl"
    initial, initial_source = event_frame(bpath, 34)
    baseline, baseline_source = event_frame(apath, 71)
    current = initial
    reader = RegionReader(lambda: current)
    reference = reader.reference()
    regions = []

    def record(label, bounds, *, frame_reader=reader, evidence=initial_source, fg="B", transforms=True):
        result = frame_reader.read(bounds, foreground=fg, include_transforms=transforms)
        if result["status"] == "observed":
            # Re-slice the saved source, then count characters without module helpers.
            saved = saved_frames[(evidence["path"], evidence["line"])].ascii.splitlines()
            t, l, b, r = bounds
            saved_crop = [saved[y][l:r+1] for y in range(t, b+1)]
            raw = result["raw_rows"]
            if raw != saved_crop or result["bbox"] != list(bounds):
                raise ValueError(f"Saved-frame coordinate mismatch: {label}")
            expected = [[int(char in fg) for char in row] for row in raw]
            if expected != [[int(char) for char in row] for row in result["mask_rows"]]:
                raise ValueError(f"Mask mismatch: {label}")
            if sum(sum(row) for row in expected) != result["foreground_pixels"]:
                raise ValueError(f"Pixel count mismatch: {label}")
        item = {"label": label, "source": evidence, "representation": result,
                "json_chars": len(json.dumps(result, ensure_ascii=False, separators=(",", ":")))}
        regions.append(item)
        return result

    # Explicit sample annotations from 007 B events L36; only the row offset changes.
    pink_starts = [(5, 6), (5, 29), (14, 6), (14, 36), (23, 6), (23, 43)]
    yellow_starts = [(5, 16), (5, 39), (5, 46), (5, 53), (14, 16), (14, 23),
                     (14, 46), (14, 53), (23, 16), (23, 23), (23, 30), (23, 53)]
    yellow_names = ["A0", "B0", "B1", "B2", "C0", "C1", "D0", "D1", "E0", "E1", "E2", "F0"]
    bottom_starts = [(41, c) for c in (19, 26, 33, 40)]
    groups = {}
    for variant in ("wrong_row", "interior_row"):
        pink, yellow = {}, {}
        for kind, starts, names, destination in (
            ("pink", pink_starts, list("ABCDEF"), pink),
            ("yellow", yellow_starts, yellow_names, yellow),
        ):
            for (row, col), name in zip(starts, names):
                if variant == "wrong_row" and row in (14, 23):
                    row -= 1
                destination[name] = record(f"007_{variant}_{kind}_{name}", (row, col, row+4, col+4))
        bottoms = [record(f"007_{variant}_bottom_{i}", (r, c, r+4, c+4))
                   for i, (r, c) in enumerate(bottom_starts)]
        # This explicitly requested D4 comparison reproduces the earlier analysis;
        # it is not an assertion that every game permits mirror equivalence.
        def d4(item): return item["transform_keys"]["dihedral_canonical"]
        classes = defaultdict(list)
        for name, item in yellow.items(): classes[d4(item)].append(name)
        groups[variant] = {
            "bottom_pink_matches_under_explicit_d4": [[name for name, item in pink.items()
                                                      if d4(item) == d4(bottom)] for bottom in bottoms],
            "yellow_d4_classes": list(classes.values()),
            "yellow_class_count": len(classes),
            "yellow_pixels": {name: item["foreground_pixels"] for name, item in yellow.items()},
            "cross_boundary_regions": [name for name, item in {**pink, **yellow}.items()
                                       if item["edge_observations"]["foreground_crossing_counts"]],
            "multiple_component_yellow_regions": {name: len(item["components_4_connected"])
                                                  for name, item in yellow.items()
                                                  if len(item["components_4_connected"]) > 1},
        }

    # Node-derived rectangles avoid retyping boundary coordinates. Insets remain explicit.
    node_cases = []
    for node in initial.segmentation["nodes"]:
        if node["color"] != "P":
            continue
        pts = node["boundary"]
        bbox = [min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts)]
        if bbox[2] >= 30:  # Historical annotation selects the visible legend area.
            continue
        t, l, b, r = bbox
        if b-t < 2 or r-l < 2:
            continue
        rows = initial.ascii.splitlines()
        perimeter = rows[t][l:r+1] + rows[b][l:r+1]
        perimeter += "".join(rows[y][l] + rows[y][r] for y in range(t+1, b))
        if set(perimeter) != {"P"}:
            continue
        result = reader.from_node(node["id"], foreground="B", expect_frame=reference,
                                  inset=1, include_transforms=True)
        node_cases.append(result)
    if len(node_cases) != 6:
        raise ValueError("Historical six-panel observation changed")

    # Real action changes the bottom row; the getter must resolve the new frame.
    newer, newer_source = event_frame(bpath, 39)
    old_observation = reader.read((52, 8, 56, 12), foreground="B")
    current = newer
    new_observation = reader.read((52, 8, 56, 12), foreground="B")
    rejected_old_reference = reader.read((52, 8, 56, 12), foreground="B", expect_frame=reference)
    rejected_old_node = reader.from_node(node_cases[0]["selection"]["node_id"], foreground="B",
                                         expect_frame=reference, inset=1)
    current = initial

    # An actual chiral crop supplies pose examples; transformed frames are labelled derived.
    chiral = next(item for item in regions
                  if item["label"].startswith("007_interior_row_yellow")
                  and item["representation"]["transform_keys"]["rotation_canonical"] !=
                  item["representation"]["transform_keys"]["mirrored_rotation_canonical"])
    crop = chiral["representation"]["raw_rows"]
    rotated = ["".join(crop[len(crop)-1-r][c] for r in range(len(crop)))
               for c in range(len(crop[0]))]
    mirrored = [row[::-1] for row in crop]
    poses = {}
    for name, rows in (("source", crop), ("rotated_clockwise_90", rotated), ("mirrored_left_right", mirrored)):
        derived = SimpleNamespace(ascii="\n".join(rows), shape=(len(rows), len(rows[0])),
                                  step=initial.step, level=initial.level)
        poses[name] = RegionReader(lambda f=derived: f).read(
            (0, 0, len(rows)-1, len(rows[0])-1), foreground="B", include_transforms=True)

    # 005 tr87: restored helper returned letters; old encoder expected the literal '1'.
    old_trpath = "runs/005-full-baseline/baseline/artifacts/tr87-cd924810_p0_events.jsonl"
    old_trframe, old_trsource = event_frame(old_trpath, 331)
    old_reader = RegionReader(lambda: old_trframe)
    encoding_regions = []
    for r in (6, 18, 30):
        for c in (10, 20, 27, 40, 49):
            encoding_regions.append(record(f"005_tr87_r{r}_c{c}", (r, c, r+4, c+4),
                                            frame_reader=old_reader, evidence=old_trsource))
    for r, columns in ((45, (22, 29, 36)), (54, (12, 19, 26, 33, 40, 47))):
        for c in columns:
            encoding_regions.append(record(f"005_tr87_r{r}_c{c}", (r, c, r+4, c+4),
                                            frame_reader=old_reader, evidence=old_trsource))
    invalid_foreground = old_reader.read((6, 10, 10, 14), foreground="1")

    # 005 re86: bbox center was incorrectly used as the actual vertical rod column.
    re_path = "runs/005-full-baseline/baseline/artifacts/re86-8af5384d_p0_events.jsonl"
    re_frame, re_source = event_frame(re_path, 707)
    re_reader = RegionReader(lambda: re_frame)
    re_region = record("005_re86_sky_shape", (30, 18, 48, 36), frame_reader=re_reader,
                       evidence=re_source, fg="S", transforms=False)
    row_occupancy = {str(30+i): [18+j for j, char in enumerate(row) if char == "1"]
                     for i, row in enumerate(re_region["mask_rows"])}

    # Small explicit probes of API boundaries, not a reusable test suite.
    empty = reader.read((0, 0, 2, 2), foreground="B")
    invalid_bbox = reader.read((-1, 0, 3, 3), foreground="B")
    reversed_bbox = reader.read((5, 6, 4, 10), foreground="B")
    oversized = reader.read((0, 0, 63, 63), foreground="B")
    malformed = SimpleNamespace(ascii="BY\n?Y", shape=(2, 2), step=0, level=1)
    unknown_observed = RegionReader(lambda: malformed).read((0, 0, 1, 1), foreground="B")
    source_keys = poses["source"]["transform_keys"]
    observations = {
        "paired_initial_ascii_equal": initial.ascii == baseline.ascii,
        "saved_board_matches_ascii": True,
        "manual_mask_pixel_crosschecks": len(regions),
        "corrected_pink_matches": groups["interior_row"]["bottom_pink_matches_under_explicit_d4"],
        "yellow_classes_wrong_to_correct": [groups["wrong_row"]["yellow_class_count"],
                                             groups["interior_row"]["yellow_class_count"]],
        "default_omits_transform_keys": "transform_keys" not in new_observation,
        "live_getter_step_changes": [old_observation["frame"]["step"], new_observation["frame"]["step"]],
        "live_getter_mask_changed": old_observation["mask_rows"] != new_observation["mask_rows"],
        "old_frame_reference_rejected": rejected_old_reference["status"] == "unavailable",
        "old_node_reference_rejected": rejected_old_node["status"] == "unavailable",
        "rotation_changes_exact": poses["source"]["exact_key"] != poses["rotated_clockwise_90"]["exact_key"],
        "rotation_preserves_rotation_key": source_keys["rotation_canonical"] == poses["rotated_clockwise_90"]["transform_keys"]["rotation_canonical"],
        "reflection_keeps_distinct_rotation_key": source_keys["rotation_canonical"] != poses["mirrored_left_right"]["transform_keys"]["rotation_canonical"],
        "explicit_dihedral_merges_reflection": source_keys["dihedral_canonical"] == poses["mirrored_left_right"]["transform_keys"]["dihedral_canonical"],
        "empty_has_no_identity_key": empty["exact_key"] is None,
        "005_encoding_region_count": len(encoding_regions),
        "005_encoding_nonempty_count": sum(r["foreground_pixels"] > 0 for r in encoding_regions),
        "005_encoding_exact_class_count": len({r["exact_key"] for r in encoding_regions}),
        "005_re86_stem_columns_rows30_to47": sorted(set(c for row, cols in row_occupancy.items()
                                                       if int(row) < 48 for c in cols)),
        "005_re86_bbox_center_column": (18+36)/2,
        "note": "These are deterministic saved-frame/API observations, not model adoption or score gains.",
    }
    result = {
        "schema_version": 1, "study": "008-cpu-region-representation", "python": platform.python_version(),
        "observations": observations, "initial_sources": [initial_source, baseline_source],
        "groups": groups, "regions": regions, "node_selected_pink_interiors": node_cases,
        "fresh_frame_case": {"old_source": initial_source, "new_source": newer_source,
                             "old": old_observation, "new": new_observation,
                             "old_reference_attempt": rejected_old_reference,
                             "old_node_attempt": rejected_old_node},
        "pose_case": {"source_region_label": chiral["label"], "kind": "derived pixel transforms, not new environment observations",
                      "poses": poses},
        "005_encoding_case": {"source": old_trsource, "wrong_foreground_attempt": invalid_foreground,
                              "historical_code_source": "runs/005-full-baseline/baseline/tr87-cd924810_p0_requests.jsonl:135",
                              "boundary": "No historical sig/g5c or action code was executed."},
        "005_re86_case": {"source": re_source, "row_occupancy": row_occupancy},
        "boundary_cases": {"empty": empty, "out_of_bounds": invalid_bbox, "reversed": reversed_bbox,
                           "oversized": oversized, "unknown_observed": unknown_observed},
        "output_chars": {"min": min(r["json_chars"] for r in regions),
                         "max": max(r["json_chars"] for r in regions),
                         "total_individual_region_json": sum(r["json_chars"] for r in regions)},
        "boundaries": ["No GPU, model, SDK action, engine source, or transcript code execution.",
                       "Historical region coordinates only appear in this analysis, never in the reusable module.",
                       "No node, component, bbox or key establishes semantic glyph identity or a victory rule.",
                       "No detected boundary crossing does not prove a semantic region is complete.",
                       "Current frame contract depends on a getter that resolves the live runtime global.",
                       "Prototype is not attached to run_arm or the Python-tool bootstrap."],
    }
    # Include the evidence text source used to annotate the 005 encoder case.
    source("runs/005-full-baseline/baseline/tr87-cd924810_p0_requests.jsonl")
    result["sources"] = list(sources.values())
    result["source_hashes_unchanged"] = all(digest(ROOT / item["path"]) == item["sha256"]
                                            for item in sources.values())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(observations, ensure_ascii=False, indent=2))
    print(f"Saved {args.output_dir / 'analysis.json'}")


if __name__ == "__main__":
    main()
