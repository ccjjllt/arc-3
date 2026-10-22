#!/usr/bin/env python3
"""Freeze the first 032 candidate su15 L5 request, using public replay only.

No model, GPU, network, game-source inspection or post-cut solver answer is used.
Only su15-package.json(.gz.b64) is solver input. The separate baseline L5 audit
is retrospective researcher material and must not be mounted in a solver run.
Run with the project's Python 3.12 runtime and the existing 018 SDK dependencies.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/arc3-034-su15-mpl")
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"),
               str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
               "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]
sys.path.extend(p for p in os.environ.get("ARC3_CPU_DEPENDENCY_PATHS", "").split(os.pathsep) if p)

from arc_agi import Arcade, OperationMode
from arcengine import GameAction
from inference.agent.python_tool_sandbox import run_sandboxed_python
from prepare_028_inputs import STATE_RE, load_checkpoint, original_grid, text_content

GAME_ID = "su15-1944f8ab"
CANDIDATE = ROOT / "runs/032-memory-recovery/solved_level_memory"
BASELINE = ROOT / "runs/032-memory-full/baseline"
ENV_DIR = ROOT / "research/data/extracted/environment_files"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def value_sha(value) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def find_cut(request_path: Path):
    prefix = []
    with request_path.open("rb") as stream:
        for index, line in enumerate(stream):
            prefix.append(line)
            record = json.loads(line)
            if record.get("event") != "request":
                continue
            latest = next(m for m in reversed(record["messages"]) if m["role"] == "user")
            match = STATE_RE.search(text_content(latest.get("content")))
            if match and int(match.group(2)) == 5:
                step = int(match.group(1))
                if int(record["action"]) != step:
                    raise ValueError("Request action counter disagrees with displayed step")
                return index, record, step - 1, sha(b"".join(prefix))
    raise ValueError("No L5 request found")


def replay_public(actions, recording_dir: str):
    arcade = Arcade(environments_dir=str(ENV_DIR), operation_mode=OperationMode.OFFLINE,
                    recordings_dir=recording_dir)
    env = arcade.make(GAME_ID, seed=0, render_mode=None, save_recording=False)
    response = env.reset()
    records = []

    def observe(index, action):
        if response is None or not response.frame:
            raise RuntimeError("Replay returned no public frame")
        grid = [[int(c) for c in row] for row in response.frame[-1]]
        state = getattr(response.state, "name", str(response.state))
        records.append({"action_count": index, "action": action,
                        "levels_completed": int(response.levels_completed),
                        "state": state, "grid_sha256": value_sha(grid)})
        return grid

    grid = observe(0, None)
    for index, action in enumerate(actions, 1):
        response = env.step(GameAction.from_name(action["id"]), data=action["data"] or None)
        grid = observe(index, action)
    return grid, records


def baseline_audit():
    path = BASELINE / "benchmark.json"
    run = next(g for g in json.loads(path.read_text())["game_runs"] if g["game_id"] == GAME_ID)
    start = sum(run["actions_per_level"][:4])
    end = start + run["actions_per_level"][4]
    return {"classification": "researcher_posthoc_only_never_solver_input",
            "source": str(path.relative_to(ROOT)), "source_sha256": sha(path.read_bytes()),
            "game_id": GAME_ID, "level": 5,
            "history_slice_zero_based": [start, end],
            "baseline_total_levels_completed": run["levels_completed"],
            "level_action_count": end - start,
            "actions": [{"history_action_number_1based": i + 1,
                         "action": run["history"][i]["action"]} for i in range(start, end)],
            "warning": "Different baseline trajectory. These actions are not a candidate plan, "
                       "are not passed to either arm, and are not used to choose the prefix cut."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/034-fork-inputs")
    args = parser.parse_args()
    out = args.output.resolve()
    names = ("su15-package.json", "su15-package.json.gz.b64", "su15-package-report.json",
             "baseline-l5-posthoc-audit.json", "input-boundaries.json")
    if any((out / name).exists() for name in names):
        raise FileExistsError("Use a fresh output directory; existing frozen artifacts are not overwritten")
    request_path = CANDIDATE / f"{GAME_ID}_p0_requests.jsonl"
    benchmark_path = CANDIDATE / "benchmark.json"
    cut_record, selected, cut, request_prefix_hash = find_cut(request_path)
    run = next(g for g in json.loads(benchmark_path.read_text())["game_runs"] if g["game_id"] == GAME_ID)
    if cut != sum(run["actions_per_level"][:4]):
        raise ValueError("First L5 request is not immediately after the L4 action boundary")
    actions = [{"id": h["action"]["id"], "data": dict(h["action"].get("data") or {})}
               for h in run["history"][:cut]]
    target, messages, kept, step, level, removed_images = load_checkpoint(request_path, cut_record)
    if target != selected or level != 5 or step != cut + 1:
        raise ValueError("Checkpoint reader disagrees with first L5 request selection")
    with tempfile.TemporaryDirectory(prefix="arc3-034-su15-replay-") as root:
        grid, states = replay_public(actions, str(Path(root) / "a"))
        second_grid, second_states = replay_public(actions, str(Path(root) / "b"))
    image_grid = original_grid(target["messages"], (len(grid), len(grid[0])))
    if grid != image_grid or grid != second_grid or states != second_states:
        raise ValueError("Public replay differs from the original request image or second replay")
    if states[-1]["levels_completed"] != 4 or states[-1]["state"] != "NOT_FINISHED":
        raise ValueError("Replay did not end on the starting L5 board")
    if any(s["levels_completed"] >= 4 for s in states[:-1]):
        raise ValueError("Prefix contains an action after L5 was entered")
    if any(s["state"] == "GAME_OVER" for s in states):
        raise ValueError("Unexpected death/reset requires explicit step-counter alignment")
    # The request renders the next action number; the native Frame.step is the
    # number of already executed actions. Keep those two counters distinct.
    current = {"grid": grid, "step": cut, "level": level}
    blocked = []

    def no_actions(request):
        blocked.append(request)
        raise RuntimeError("Environment actions forbidden during function restoration")

    sandbox = run_sandboxed_python(
        code="print('034 checkpoint retained functions restored')", timeout_seconds=10,
        initial_state={"current_frame": current, "history": []}, action_handler=no_actions,
        kept_functions=list(kept.values()), retain_imports=True)
    restored = {item["name"] for item in sandbox.get("keepable_functions", [])}
    if sandbox.get("error") or restored != set(kept) or blocked:
        raise ValueError(f"Retained function restoration failed: {sandbox.get('error')}; "
                         f"missing={sorted(set(kept) - restored)}; actions={len(blocked)}")
    env_sources = {str(path.relative_to(ROOT)): sha(path.read_bytes())
                   for path in sorted((ENV_DIR / "su15").rglob("*.py"))}
    entry = {"cut": cut, "cut_record": cut_record, "analysis_step": int(target["analysis_step"]),
             "kind": "level_entry_diagnostic", "max_extra_actions": 30,
             "max_extra_seconds": 450, "seed": 0, "actions": actions,
             "messages": messages, "kept_functions": kept, "retain_imports": True,
             "current_frame": current, "environment_sources": env_sources,
             "counter_alignment": {"history_actions": cut, "runtime_frame_step": cut,
                                   "displayed_request_step": step,
                                   "explanation": "The user prompt displays next action number (history count + 1). "
                                                  "current_frame.step stores native runtime action_count, not the displayed next-step value."},
             "source": {"benchmark": str(benchmark_path.relative_to(ROOT)),
                        "benchmark_sha256": sha(benchmark_path.read_bytes()),
                        "request_log": str(request_path.relative_to(ROOT)),
                        "request_sha256": sha(request_path.read_bytes()),
                        "request_prefix_including_cut_sha256": request_prefix_hash}}
    package = {"schema_version": 1, "forks": {GAME_ID: entry}}
    raw = json.dumps(package, ensure_ascii=False, separators=(",", ":")).encode()
    packed = base64.b64encode(gzip.compress(raw, mtime=0)) + b"\n"
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "game_id": GAME_ID, "cut": cut, "cut_record_zero_based": cut_record,
              "cut_request_line_1based": cut_record + 1, "analysis_step": target["analysis_step"],
              "current_level": level, "history_action_count": cut, "runtime_frame_step": cut,
              "displayed_step": step, "python_version": sys.version,
              "source_selection": "First request reporting L5, before any L5 action; selected by level metadata only",
              "future_responses_in_package": 0, "baseline_actions_in_package": 0,
              "messages": len(messages), "removed_images": removed_images,
              "history_image_policy": "All images removed exactly as 028; current frame is frozen separately "
                                      "and the runner regenerates public replay history. Not byte-identical original context.",
              "source_arm": "032 solved_level_memory candidate; preserved prefix may contain prior-level memory text",
              "kept_function_names": sorted(kept), "retained_sandbox_restore_passed": True,
              "retained_sandbox_environment_action_calls": 0,
              "public_replay_twice_identical": True,
              "replay_matches_original_current_request_image": True,
              "grid_sha256": value_sha(grid), "prefix_public_states": states,
              "level_entry_actions": [s["action_count"] for a, s in zip(states, states[1:])
                                      if s["levels_completed"] > a["levels_completed"]],
              "public_observation_only": True, "game_source_access": "SHA256 provenance only; no rule inspection",
              "package": "su15-package.json", "package_sha256": sha(raw + b"\n"),
              "package_bytes": len(raw) + 1, "packed_sha256": sha(packed), "packed_bytes": len(packed),
              "preparer_sha256": sha(Path(__file__).read_bytes()),
              "checkpoint_parser_sha256": sha((ROOT / "scripts/prepare/prepare_028_inputs.py").read_bytes()),
              "model_calls": 0, "gpu_seconds": 0}
    out.mkdir(parents=True, exist_ok=True)
    (out / "su15-package.json").write_bytes(raw + b"\n")
    (out / "su15-package.json.gz.b64").write_bytes(packed)
    write_json(out / "su15-package-report.json", report)
    write_json(out / "baseline-l5-posthoc-audit.json", baseline_audit())
    write_json(out / "input-boundaries.json", {
        "solver_input_allowlist": ["su15-package.json.gz.b64"],
        "equivalent_uncompressed_input": "su15-package.json",
        "researcher_only_do_not_mount": ["su15-package-report.json", "baseline-l5-posthoc-audit.json", "input-boundaries.json"],
        "runner_integration": "Use the schema-1 forks[su15-1944f8ab] entry. Parameterize the 033 runner's GAME_ID and package path; "
                              "do not copy the hard-coded ft09 identifier or researcher audit files. Replay actions with the existing "
                              "session executor, compare current grid/level and prefix count, restore messages/functions, then reset "
                              "continuation timer and action cap. A/B must consume the identical package."})
    print(json.dumps({key: report[key] for key in ("game_id", "cut", "cut_request_line_1based",
          "current_level", "displayed_step", "kept_function_names", "package_sha256", "package_bytes")}, indent=2))


if __name__ == "__main__":
    main()
