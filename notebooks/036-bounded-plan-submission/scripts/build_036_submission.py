"""Build 036 bounded program delivery for GPU save and the live competition gateway.

This is a local builder only. It never uploads, starts a model, or submits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from pprint import pformat
import shutil
import subprocess
import sys
import tempfile

import build_submission as baseline_builder


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ("__init__.py", "program_repair.py", "executable_plan_contract.py",
           "executable_plan.py", "bounded_executable_plan.py")
REMOTE_SRC = "/kaggle/bounded_plan_submission/src"

FORMAL_DEADLINE = '''# 036 explicitly counts cold loading and setup inside the nine-hour notebook cap.
# The common first-cell monotonic clock is independent of the later solver clock.
soft_end = None
if TRUE_SUBMISSION:
    _budget = ARC3_SUBMISSION_CONFIG["formal_runtime_budget"]
    _elapsed = time.monotonic() - ARC3_NOTEBOOK_STARTED_MONOTONIC
    _remaining = (_budget["hard_limit_seconds"] - _elapsed
                  - _budget["cleanup_reserve_seconds"])
    if _remaining <= 0:
        raise RuntimeError("036 total notebook budget exhausted before gameplay")
    bm.solver.max_runtime_s_per_game = min(
        ARC3_SUBMISSION_CONFIG["solver"]["max_runtime_s_per_game"], _remaining)
    bm.solver.cancel_drain_timeout_s = _budget["cancel_drain_timeout_seconds"]
    soft_end = datetime.now() + timedelta(seconds=_remaining)
    ARC3_FORMAL_BUDGET_REPORT = {
        "clock_origin": "first_notebook_cell_monotonic",
        "notebook_started_epoch": ARC3_NOTEBOOK_STARTED_EPOCH,
        "elapsed_before_gameplay_seconds": _elapsed,
        "remaining_gameplay_seconds": _remaining,
        "effective_per_game_limit_seconds": bm.solver.max_runtime_s_per_game,
        "soft_end_local": soft_end.isoformat(),
        "cleanup_reserve_seconds": _budget["cleanup_reserve_seconds"],
        "cancel_drain_timeout_seconds": bm.solver.cancel_drain_timeout_s,
        "hard_limit_seconds": _budget["hard_limit_seconds"],
        "live_gateway_game_count": len(bm.games),
        "runtime_change_from_009": "Explicit total deadline including setup/cold loading; 009 used formal soft_end=None",
    }
    (ARC3_SUBMISSION_WORKING / "formal-runtime-budget.json").write_text(
        json.dumps(ARC3_FORMAL_BUDGET_REPORT, indent=2) + "\\n")
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/036-bounded-plan-submission.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    baseline_path = ROOT / config["baseline_config"]
    baseline_config = json.loads(baseline_path.read_text())
    if baseline_builder.sha256(baseline_path.read_bytes()) != config["baseline_config_sha256"]:
        raise ValueError("The frozen 009 baseline configuration changed")
    for key in ("base_notebook", "base_source_sha256", "hard_limit_seconds", "machine_shape",
                "enable_internet", "input_resolution_timeout_seconds", "formal_mode", "save_mode",
                "save_placeholder_is_scored", "formal_submission_file_owner", "official_save_protocol", "revision"):
        if config[key] != baseline_config[key]:
            raise ValueError(f"036 must retain the reviewed submission protocol: {key}")
    expected_solver = {**baseline_config["solver"], "research_interventions": ["bounded_executable_plan"]}
    if config["solver"] != expected_solver or any(key in config for key in ("games", "game_ids", "arm_order")):
        raise ValueError("036 installs only bounded executable planning and never a fixed formal game pool")
    expected_smoke = {**baseline_config["save_smoke"], "startup_timeout_seconds": 4200,
                      "total_timeout_seconds": 5400}
    if config["save_smoke"] != expected_smoke:
        raise ValueError("036 save retains two real 300s games with explicit 4200s/5400s loading limits")
    budget = config["formal_runtime_budget"]
    if (budget["clock_origin"] != "first_notebook_cell_monotonic"
            or budget["hard_limit_seconds"] != 32400
            or budget["cleanup_reserve_seconds"] != 300
            or budget["cancel_drain_timeout_seconds"] != 120):
        raise ValueError("036 formal cold loading, gameplay and cleanup must share one nine-hour budget")
    provenance = config["kernel_owner_provenance"]
    owner = config["kernel_id"].split("/", 1)[0]
    if owner != provenance["owner"] or provenance["must_verify_authenticated_account_and_team_before_push"] is not True:
        raise ValueError("036 requires explicit owner provenance and live account/team verification before upload")
    helpers = [ROOT / "src/arc3_research" / name for name in HELPERS]
    expected_helpers = config["bounded_executable_plan"]["source_sha256"]
    if set(expected_helpers) != {str(path.relative_to(ROOT)) for path in helpers}:
        raise ValueError("036 helper manifest must cover exactly the shared implementation dependencies")
    for path in helpers:
        if baseline_builder.sha256(path.read_bytes()) != expected_helpers[str(path.relative_to(ROOT))]:
            raise ValueError(f"Pinned 036 implementation changed: {path.name}")
    if config["bounded_executable_plan"]["configuration_source"] != "arc3_research.bounded_executable_plan.DEFAULT_CONFIG":
        raise ValueError("Research, save and formal installs must use the same module defaults")

    # Build historical 009 untouched; all 036 overrides remain in this builder.
    with tempfile.TemporaryDirectory(prefix="arc3-036-base-") as temporary:
        subprocess.run([sys.executable, str(ROOT / "scripts/build_submission.py"),
                        "--config", str(baseline_path), "--output-dir", temporary],
                       check=True, capture_output=True, text=True)
        base_dir = Path(temporary)
        notebook = json.loads((base_dir / "submission.ipynb").read_text())
        metadata = json.loads((base_dir / "kernel-metadata.json").read_text())
        inherited = json.loads((base_dir / "build-manifest.json").read_text())
    native_sources = ["".join(cell["source"]) for cell in notebook["cells"]]
    tracked = [*(ROOT / name for name in inherited["source_hashes"]), Path(__file__), config_path, *helpers]
    hashes = {str(path.relative_to(ROOT)): baseline_builder.sha256(path.read_bytes()) for path in tracked}
    notebook["cells"][0] = baseline_builder.code_cell(
        "# 036 first-cell clock: input resolution and cold loading count toward the total cap.\n"
        "import time\n"
        "ARC3_NOTEBOOK_STARTED_MONOTONIC = time.monotonic()\n"
        "ARC3_NOTEBOOK_STARTED_EPOCH = time.time()\n"
        "ARC3_SUBMISSION_CONFIG = " + pformat(config, width=100, sort_dicts=False) + "\n\n"
        "ARC3_SUBMISSION_SOURCE_HASHES = " + pformat(hashes, width=100, sort_dicts=False) + "\n\n"
        + baseline_builder.BOOTSTRAP.replace("009 v2 save smoke", "036 bounded-plan save smoke")
    )
    original = json.loads((ROOT / config["base_notebook"]).read_text())
    introduction = (
        "# ARC3 036 — bounded executable program delivery\n\n"
        "Prepared locally; no upload, GPU run or formal submission is implied. Research, save and "
        "competition modes install the same bounded-executable-plan module with its DEFAULT_CONFIG. "
        "The ordinary actor and model serving remain the frozen Franzen v3/009 implementation. "
        "No fork histories, public game filter, successful-level memory or persistent Python patch "
        "is included. Save loads the real model, allows 4200 seconds for startup, then plays "
        "sb26/cd82 for 300 seconds before the organizer's unscored placeholder; total save cap is "
        "5400 seconds. Formal reruns enumerate live gateway games and explicitly include cold loading "
        "in the 32400-second total budget, reserving 300 seconds for cleanup. This total-deadline "
        "protection is an intentional runtime change from 009, not an observed score gain.\n\n"
    )
    notebook["cells"][2]["source"] = (introduction + "".join(original["cells"][0]["source"])).splitlines(keepends=True)
    notebook["cells"][21]["source"] = (
        "## Run the live gateway or real GPU save smoke\n\n"
        "The gateway alone writes formal submission scores. Formal gameplay uses the first-cell "
        "total deadline minus a 300-second cleanup reserve. Save uses two public games for 300 "
        "seconds after health 200, with a 5400-second total watchdog and 4200-second startup limit. "
        "A successful save validates execution and is not a hidden leaderboard result.\n"
    ).splitlines(keepends=True)
    runtime = baseline_builder.replace_once(
        native_sources[22],
        "# Formal retains the original deadline behavior; save starts its 300-second window now.\nsoft_end = None\n",
        FORMAL_DEADLINE,
    )
    runtime = baseline_builder.replace_once(
        runtime,
        "if TRUE_SUBMISSION:\n    await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)\n",
        "if TRUE_SUBMISSION:\n"
        "    try:\n"
        "        await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)\n"
        "    finally:\n"
        "        ARC3_FORMAL_BUDGET_REPORT['elapsed_after_gameplay_seconds'] = time.monotonic() - ARC3_NOTEBOOK_STARTED_MONOTONIC\n"
        "        (ARC3_SUBMISSION_WORKING / 'formal-runtime-budget.json').write_text(\n"
        "            json.dumps(ARC3_FORMAL_BUDGET_REPORT, indent=2) + '\\n')\n"
        "        (ARC3_SUBMISSION_WORKING / 'bounded-plan-summary.json').write_text(\n"
        "            json.dumps(ARC3_BOUNDED_PLAN_PATCH.snapshot(), indent=2) + '\\n')\n",
    )
    notebook["cells"][22]["source"] = runtime.splitlines(keepends=True)

    inserts = [baseline_builder.code_cell(
        "# Readable helpers are installed before benchmark construction in both modes.\n"
        f"Path({REMOTE_SRC + '/arc3_research'!r}).mkdir(parents=True, exist_ok=True)\n")]
    for path in helpers:
        source = path.read_text()
        if not source.endswith("\n"):
            raise ValueError(f"Native helper source must end with LF: {path}")
        inserts.append(baseline_builder.code_cell(f"%%writefile {REMOTE_SRC}/arc3_research/{path.name}\n" + source))
    inserts.append(baseline_builder.code_cell(
        "# Exact shared defaults: do not copy a divergent set of formal request parameters.\n"
        f"sys.path.insert(0, {REMOTE_SRC!r})\n"
        "from arc3_research.bounded_executable_plan import DEFAULT_CONFIG, install_bounded_executable_plan\n"
        "ARC3_BOUNDED_PLAN_PATCH = install_bounded_executable_plan()\n"
        "ARC3_BOUNDED_PLAN_INSTALL = ARC3_BOUNDED_PLAN_PATCH.snapshot()\n"
        "(ARC3_SUBMISSION_WORKING / 'bounded-plan-install.json').write_text(\n"
        "    json.dumps({'defaults': DEFAULT_CONFIG, 'patch': ARC3_BOUNDED_PLAN_INSTALL}, indent=2) + '\\n')\n"
        "print('036 bounded executable plan installed:', ARC3_BOUNDED_PLAN_INSTALL)\n"))
    if "source_entries = _source_path_entries(BUNDLE_DIR)" not in native_sources[12]:
        raise ValueError("009 source import location changed")
    insertion_index = 13
    notebook["cells"][insertion_index:insertion_index] = inserts
    metadata.update(id=config["kernel_id"], title=config["kernel_title"])
    out = args.output_dir.resolve() if args.output_dir else ROOT / "notebooks" / config["id"]
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "submission.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=1) + "\n")
    if notebook_path.stat().st_size > 1_000_000:
        raise ValueError("036 source exceeds the bounded Kaggle notebook upload size")
    metadata_path = out / "kernel-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    changed = {0, 2, 21, 22}
    mapping = [{"baseline_009_index": i,
                "generated_index": i + (len(inserts) if i >= insertion_index else 0),
                "baseline_source_sha256": baseline_builder.sha256(source),
                "generated_source_sha256": baseline_builder.sha256("".join(
                    notebook["cells"][i + (len(inserts) if i >= insertion_index else 0)]["source"])),
                "changed": i in changed} for i, source in enumerate(native_sources)]
    if any(item["baseline_source_sha256"] != item["generated_source_sha256"]
           for item in mapping if not item["changed"]):
        raise ValueError("036 unexpectedly changed an inherited 009 cell")
    manifest = {
        "id": config["id"], "revision": config["revision"], "config": config, "source_hashes": hashes,
        "baseline_builder_reused": "scripts/build_submission.py (unchanged local builder, temporary output)",
        "baseline_009_notebook_sha256": inherited["notebook_sha256"],
        "notebook_sha256": baseline_builder.sha256(notebook_path.read_bytes()),
        "metadata_sha256": baseline_builder.sha256(metadata_path.read_bytes()),
        "cell_count": len(notebook["cells"]), "base_009_cell_count": len(native_sources),
        "cells": mapping, "inserted_cell_indices": list(range(insertion_index, insertion_index + len(inserts))),
        "helper_files": [str(path.relative_to(ROOT)) for path in helpers],
        "formal_game_selection": "unchanged _competition_games() enumerates live gateway available_environments",
        "formal_and_save_solver_interventions": ["bounded_executable_plan; shared module DEFAULT_CONFIG"],
        "runtime_changes_from_009": [
            "Formal soft_end now uses first-cell total time, including cold loading, with 300s cleanup reserve",
            "Formal per-game runtime is clamped to total remaining time; cancellation drain is bounded to120s",
            "Save startup cap4200s and total cap5400s; same two public games and300s real-play validation",
        ],
        "formal_runtime_budget": budget, "fork_inputs_bundled": False,
        "native_helper_writefile_cells": True, "cell_exec_compile_eval_wrappers": False,
        "kernel_owner_provenance": provenance, "research_transfer_risks": config["research_transfer_risks"],
        "state": "built_locally_not_run_not_pushed_not_submitted",
        "push_timeout_seconds": 32400,
        "submission_command_template": (
            f"kaggle competitions submit arc-prize-2026-arc-agi-3 -k {config['kernel_id']} "
            "-v <actual-successful-gpu-smoke-version> -f submission.parquet -m <frozen-source-description>"),
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for relative in hashes:
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() != (ROOT / relative).resolve():
            shutil.copyfile(ROOT / relative, destination)
    print(json.dumps({"notebook": str(notebook_path), "sha256": manifest["notebook_sha256"],
                      "bytes": notebook_path.stat().st_size, "cells": manifest["cell_count"],
                      "state": manifest["state"]}, indent=2))


if __name__ == "__main__":
    main()
