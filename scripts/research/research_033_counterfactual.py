#!/usr/bin/env python3
"""CPU mechanism intervention: fixed 031 target_for, bbox versus visible pixels.

This is researcher-directed offline replay, not a model evaluation or submission.
Each input/mode combination starts from an independent 028 ft09 checkpoint.
The old inspection snippet is executed verbatim; only its pieces dictionary is
replaced in the exact-pixel condition. No game implementation or hidden answer is
read. Plans use the unchanged target_for result and the observed cell grid.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "research/runtime-bundle/src/ARC3-Inference"
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/arc3-033-cpu-matplotlib")
sys.path[:0] = ["/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps", str(RUNTIME)]

from arcengine import GameAction
from arc_agi import Arcade, OperationMode
from inference.utils.grid_utils import ARC_COLOR_CHARS, format_grid_ascii
from inference.utils.segmentation import segment_layer


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def grid_of(response):
    if response is None or not response.frame:
        raise RuntimeError("Offline environment returned no visible frame")
    return [[int(v) for v in row] for row in response.frame[-1]]


def state_of(response):
    return {"levels_completed": int(response.levels_completed),
            "state": getattr(response.state, "name", str(response.state)),
            "grid_sha256": digest(grid_of(response))}


def restore(fork, rec_dir):
    arcade = Arcade(environments_dir=str(ROOT / "research/data/extracted/environment_files"),
                    operation_mode=OperationMode.OFFLINE, recordings_dir=rec_dir)
    env = arcade.make("ft09-0d8bbf25", seed=int(fork["seed"]),
                      render_mode=None, save_recording=False)
    response = env.reset()
    for raw in fork["actions"]:
        raw = raw.get("action", raw)
        response = env.step(GameAction.from_name(raw["id"]), data=raw.get("data") or None)
        grid_of(response)
    if grid_of(response) != fork["current_frame"]["grid"]:
        raise RuntimeError("Restored public observation differs from the frozen 028 checkpoint")
    return env, response


def target_records(target):
    return [{"tile": list(k), "want": v} for k, v in sorted(target.items())]


def run_condition(fork, code, source_stdout, input_kind, mode, rec_dir):
    env, response = restore(fork, rec_dir)
    initial = state_of(response)
    grid = grid_of(response)
    ascii_rows = format_grid_ascii(grid).splitlines()
    frame = SimpleNamespace(ascii="\n".join(ascii_rows),
                            segmentation=segment_layer(grid, ARC_COLOR_CHARS))
    namespace = {"current_frame": frame}
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exec(compile(code, "<original-031-B-inspection>", "exec"), namespace)
    bbox_pieces = dict(namespace["pieces"])
    bbox_target = namespace["target_for"](mode)
    if input_kind == "visible_pixels":
        namespace["pieces"] = {(r, c): color for r, line in enumerate(ascii_rows)
                               for c, color in enumerate(line)}
    target = namespace["target_for"](mode)
    cur = namespace["cur"]
    mismatches = [{"tile": list(k), "current": cur.get(k), "want": target[k]}
                  for k in sorted(target) if cur.get(k) != target[k]]
    if any(tuple(m["tile"]) not in cur for m in mismatches):
        raise RuntimeError("Original target includes a non-cell; no rule repair is permitted")
    rows, cols = namespace["grid_rows"], namespace["grid_cols"]
    # The previously observed cells are uniform 6x6 tiles. Use the same +2
    # interior click convention as existing model code, with no handpicked tile.
    plan = [{"id": "ACTION6", "data": {"x": cols[m["tile"][1]] + 2,
                                         "y": rows[m["tile"][0]] + 2}}
            for m in mismatches]
    sampled_differences = []
    patterns = []
    for pr, pc in namespace["pats"]:
        old, actual = [], []
        for i in range(3):
            old.append("".join(bbox_pieces[(pr + 2*i, pc + 2*j)] for j in range(3)))
            actual.append("".join(ascii_rows[pr + 2*i][pc + 2*j] for j in range(3)))
            for j in range(3):
                pos = (pr + 2*i, pc + 2*j)
                if bbox_pieces[pos] != ascii_rows[pos[0]][pos[1]]:
                    sampled_differences.append({"pixel": list(pos), "bbox": bbox_pieces[pos],
                                                "visible": ascii_rows[pos[0]][pos[1]]})
        patterns.append({"origin": [pr, pc], "bbox": old, "visible": actual})
    actions = []
    stop_reason = "all_derived_mismatches_executed"
    for item in plan:
        before = grid_of(response)
        before_state = state_of(response)
        response = env.step(GameAction.from_name(item["id"]), data=item["data"])
        after = grid_of(response)
        after_state = state_of(response)
        r, c = item["data"]["y"], item["data"]["x"]
        actions.append({"action": item, "before": before_state, "after": after_state,
                        "clicked_pixel_before": ARC_COLOR_CHARS[before[r][c]],
                        "clicked_pixel_after": ARC_COLOR_CHARS[after[r][c]],
                        "changed_pixels": sum(a != b for ar, br in zip(before, after)
                                              for a, b in zip(ar, br)),
                        "level_completed": after_state["levels_completed"] > before_state["levels_completed"]})
        if after_state["levels_completed"] > initial["levels_completed"]:
            stop_reason = "level_advanced_stop_before_applying_old_plan_to_new_level"
            break
        if after_state["state"] in ("GAME_OVER", "WIN"):
            stop_reason = after_state["state"]
            break
    final = state_of(response)
    return {
        "input_kind": input_kind, "rule_mode": mode,
        "initial": initial, "restored_grid_matches_frozen_package": True,
        "original_bbox_stdout_matches_recorded_031_tool": stdout.getvalue() == source_stdout,
        "original_bbox_stdout": stdout.getvalue(),
        "patterns": patterns, "sampled_pixel_differences": sampled_differences,
        "target": target_records(target),
        "target_changes_from_bbox": [{"tile": list(k), "bbox": bbox_target[k], "visible": target[k]}
                                     for k in sorted(target) if bbox_target[k] != target[k]],
        "mismatches": mismatches, "derived_plan": plan, "executed_actions": actions,
        "executed_action_count": len(actions), "stop_reason": stop_reason,
        "final": final, "added_levels": final["levels_completed"] - initial["levels_completed"],
    }


def main():
    started = time.monotonic()
    package_path = ROOT / "experiments/028-fork-package.json"
    audit_path = ROOT / "experiments/031-forks-analysis/adoption-review.json"
    fork = json.loads(package_path.read_text())["forks"]["ft09-0d8bbf25"]
    source = json.loads(audit_path.read_text())["confirmed_pixel_failure"]
    code = source["candidate_code"]
    report = {
        "kind": "researcher_cpu_counterfactual_not_model_benefit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "game_id": "ft09-0d8bbf25", "checkpoint_cut": fork["cut"], "seed": fork["seed"],
        "source_package": str(package_path.relative_to(ROOT)),
        "source_package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
        "algorithm_source": str(audit_path.relative_to(ROOT)),
        "algorithm_source_call_id": source["candidate_code_call_id"],
        "algorithm_source_request_line_1based": source["candidate_first_snapshot_line"],
        "algorithm_code_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "original_algorithm_code": code,
        "unchanged_algorithm": "The complete observed 031 B inspection snippet executes verbatim. target_for, color mapping, hardcoded observed layout, iteration order, and target overwrite behavior are unchanged. Only pieces is replaced by same-frame visible pixels in the intervention.",
        "execution_bridge": "Sort target mismatch tiles as in the original snippet; click each observed 6x6 tile once at its existing grid origin +2,+2. Stop immediately on level advance or terminal state. No handpicked action or game-internal answer is used.",
        "original_algorithm_ambiguity": "No implementation ambiguity. A and B are alternative existing rule hypotheses, each independently replayed; neither is selected in advance as correct.",
        "provenance_limit": "Offline researcher intervention; no model calls, no GPU, no online prompt injection, no formal submission or score estimate. The frozen layout-specific code is not a general controller.",
        "environment_access": "Only public env.reset/step response frames, levels_completed and state; no private game fields or game source inspected.",
        "conditions": [],
    }
    with tempfile.TemporaryDirectory(prefix="arc3-033-counterfactual-") as rec_root:
        for input_kind in ("bbox_fill", "visible_pixels"):
            for mode in ("A", "B"):
                condition = run_condition(fork, code, source["candidate_actual_tool_stdout"],
                                          input_kind, mode, str(Path(rec_root) / f"{input_kind}-{mode}"))
                report["conditions"].append(condition)
                print(input_kind, mode, "actions", condition["executed_action_count"],
                      "added_levels", condition["added_levels"], flush=True)
    report["elapsed_seconds"] = time.monotonic() - started
    report["model_calls"] = 0
    report["gpu_seconds"] = 0
    out = ROOT / "experiments/033-controller-analysis/counterfactual-ft09.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
