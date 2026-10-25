#!/usr/bin/env python3
"""Replay two archived pure generated helpers; no model or game calls.

Only norm/rotCW/canon definitions are executed with a small builtin allowlist.
Inputs are the actual shape and comparison line from the saved 036 probe.
"""
from pathlib import Path
import ast
import hashlib
import json


HERE = Path(__file__).resolve().parent
fixture = json.loads((HERE / "normalization-source.json").read_text())
shape = tuple(fixture["shape_from_actual_generated_probe"])
line = tuple(fixture["comparison_line_shape"])
px = lambda value: sum(row.count("#") for row in value)
report = {
    "status": "checking", "scope": "offline pure-function counterexample replay",
    "real_model_calls": 0, "gpu_calls": 0, "network_calls": 0,
    "game_actions": 0, "solver_modified": False,
    "shape": shape, "shape_pixels": px(shape), "versions": {},
    "limits": fixture["limits"],
}
for label in ("bad", "fixed"):
    path = HERE / f"tr87-medium-normalization-{label}.py"
    source = path.read_text()
    tree = ast.parse(source)
    assert len(tree.body) == 3
    assert all(isinstance(node, ast.FunctionDef) for node in tree.body)
    assert {node.name for node in tree.body} == {"norm", "rotCW", "canon"}
    namespace = {"__builtins__": {
        "min": min, "max": max, "len": len, "range": range,
        "tuple": tuple,
    }}
    exec(compile(tree, str(path), "exec"), namespace)
    current = shape
    pixels, rotations = [], []
    for _ in range(4):
        rotations.append(current)
        pixels.append(px(current))
        current = namespace["rotCW"](current)
    result = {
        "source_path": path.name,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "pixels_before_each_rotation": pixels,
        "rotations": rotations,
        "pixels_after_four_rotations": px(current),
        "four_rotations_return_original": current == shape,
        "canonical_conflates_shape_with_five_pixel_line":
            namespace["canon"](shape) == namespace["canon"](line),
    }
    report["versions"][label] = result
assert report["versions"]["bad"]["pixels_before_each_rotation"] == [14, 14, 5, 5]
assert not report["versions"]["bad"]["four_rotations_return_original"]
assert report["versions"]["bad"]["canonical_conflates_shape_with_five_pixel_line"]
assert report["versions"]["fixed"]["pixels_before_each_rotation"] == [14, 14, 14, 14]
assert report["versions"]["fixed"]["four_rotations_return_original"]
assert not report["versions"]["fixed"]["canonical_conflates_shape_with_five_pixel_line"]
report["status"] = "passed_counterexample_reproduced"
(HERE / "normalization-counterexample.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": report["status"], "versions": {
    label: {key: value for key, value in result.items() if key != "rotations"}
    for label, result in report["versions"].items()}}))
