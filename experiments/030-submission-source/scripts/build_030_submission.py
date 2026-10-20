"""Prepare 030 formal/save notebook from unchanged 009 v2; never run or upload."""
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
HELPERS = ("__init__.py", "persistent_python.py")
REMOTE_SRC = "/kaggle/persistent_submission/src"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/030-persistent-submission.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    if config["kernel_id"].split("/", 1)[0] != "zhuating":
        raise ValueError("030 GPU save and formal runs must target the user's zhuating account")
    baseline_path = ROOT / config["baseline_config"]
    baseline_config = json.loads(baseline_path.read_text())
    if baseline_builder.sha256(baseline_path.read_bytes()) != config["baseline_config_sha256"]:
        raise ValueError("The frozen 009 baseline configuration changed")
    # Keep formal/save semantics inherited from 009. Identity and the one solver
    # intervention are the only meaningful overrides, not a 12-game research run.
    for key in ("base_notebook", "base_source_sha256", "hard_limit_seconds", "machine_shape",
                "enable_internet", "input_resolution_timeout_seconds", "formal_mode", "save_mode",
                "save_placeholder_is_scored", "formal_submission_file_owner", "official_save_protocol",
                "revision", "save_smoke"):
        if config[key] != baseline_config[key]:
            raise ValueError(f"030 must retain 009 submission setting: {key}")
    expected_solver = {**baseline_config["solver"], "research_interventions": ["persistent_python"]}
    if config["solver"] != expected_solver or any(k in config for k in ("games", "game_ids", "arm_order")):
        raise ValueError("030 formal solver differs only by persistent_python; no research-pool override")
    # Invoke the existing local builder in an isolated temporary destination.
    # This executes builder code only, never any notebook cell or model code.
    with tempfile.TemporaryDirectory(prefix="arc3-030-base-") as temporary:
        subprocess.run([sys.executable, str(ROOT / "scripts/build_submission.py"),
                        "--config", str(baseline_path), "--output-dir", temporary],
                       check=True, capture_output=True, text=True)
        base_dir = Path(temporary)
        notebook = json.loads((base_dir / "submission.ipynb").read_text())
        metadata = json.loads((base_dir / "kernel-metadata.json").read_text())
        inherited = json.loads((base_dir / "build-manifest.json").read_text())
    native_sources = ["".join(c["source"]) for c in notebook["cells"]]
    helpers = [ROOT / "src/arc3_research" / name for name in HELPERS]
    tracked = [*(ROOT / name for name in inherited["source_hashes"]), Path(__file__), config_path, *helpers]
    hashes = {str(path.relative_to(ROOT)): baseline_builder.sha256(path.read_bytes()) for path in tracked}
    notebook["cells"][0] = baseline_builder.code_cell(
        "# 030 candidate configuration; unchanged 009 v2 save and formal protocol.\n"
        "ARC3_SUBMISSION_CONFIG = " + pformat(config, width=100, sort_dicts=False) + "\n\n"
        "ARC3_SUBMISSION_SOURCE_HASHES = " + pformat(hashes, width=100, sort_dicts=False) + "\n\n"
        + baseline_builder.BOOTSTRAP.replace("009 v2 save smoke", "030 persistent-python save smoke")
    )
    introduction = (
        "# ARC3 030 — persistent Python computation within each level\n\n"
        "Prepared locally; no run or formal submission is implied by this source. The single solver "
        "intervention retains Python computation within each level. Model, serving, "
        "scheduler, warmup, runtime and gateway protocol inherit 009 v2. Save mode runs the original "
        "two-game 300-second GPU smoke, then writes only the organizer's unscored placeholder. Formal "
        "reruns enumerate the actual live gateway game list with the original 31,920-second solver "
        "budget and 9-hour notebook limit. No 12-game research filter, FP8 PLE, checked execution, "
        "probe policy, or 018 prompt is installed.\n\n"
    )
    # Retain the original Franzen attribution without the obsolete 009 preface.
    original = json.loads((ROOT / config["base_notebook"]).read_text())
    notebook["cells"][2]["source"] = (introduction + "".join(original["cells"][0]["source"])).splitlines(keepends=True)
    inserts = [baseline_builder.code_cell(
        "# Readable standalone helper files, before benchmark loading/agent construction.\n"
        f"Path({REMOTE_SRC + '/arc3_research'!r}).mkdir(parents=True, exist_ok=True)\n")]
    for path in helpers:
        source = path.read_text()
        if not source.endswith("\n"):
            raise ValueError(f"Native helper source must end with LF: {path}")
        inserts.append(baseline_builder.code_cell(f"%%writefile {REMOTE_SRC}/arc3_research/{path.name}\n" + source))
    inserts.append(baseline_builder.code_cell(
        "# Same persistent Python implementation in save smoke and real gateway reruns.\n"
        f"sys.path.insert(0, {REMOTE_SRC!r})\n"
        "from arc3_research.persistent_python import install_persistent_python\n"
        "ARC3_PERSISTENT_PYTHON_PATCH = install_persistent_python()\n"
        "ARC3_PERSISTENT_PYTHON_SNAPSHOT = ARC3_PERSISTENT_PYTHON_PATCH.snapshot()\n"
        "(ARC3_SUBMISSION_WORKING / 'persistent-python-install.json').write_text(\n"
        "    json.dumps(ARC3_PERSISTENT_PYTHON_SNAPSHOT, indent=2) + '\\n')\n"
        "print('030 persistent Python installed:', ARC3_PERSISTENT_PYTHON_SNAPSHOT)\n"))
    # 009 cell 12 exposes the bundled inference imports. Insert before serving,
    # and before cell 16 unpickles benchmark/solver objects.
    if "source_entries = _source_path_entries(BUNDLE_DIR)" not in native_sources[12]:
        raise ValueError("009 source import location changed")
    insertion_index = 13
    notebook["cells"][insertion_index:insertion_index] = inserts
    metadata.update(id=config["kernel_id"], title=config["kernel_title"])
    out = args.output_dir.resolve() if args.output_dir else ROOT / "notebooks" / config["id"]
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "submission.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=1) + "\n")
    metadata_path = out / "kernel-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    mapping = [{"baseline_009_index": i,
                "generated_index": i + (len(inserts) if i >= insertion_index else 0),
                "baseline_source_sha256": baseline_builder.sha256(source),
                "generated_source_sha256": baseline_builder.sha256("".join(notebook["cells"][i + (len(inserts) if i >= insertion_index else 0)]["source"])),
                "changed": i in (0, 2)} for i, source in enumerate(native_sources)]
    manifest = {
        "id": config["id"], "revision": config["revision"], "config": config, "source_hashes": hashes,
        "baseline_builder_reused": "scripts/build_submission.py (unchanged subprocess builder, temporary output)",
        "baseline_009_notebook_sha256": inherited["notebook_sha256"],
        "notebook_sha256": baseline_builder.sha256(notebook_path.read_bytes()),
        "metadata_sha256": baseline_builder.sha256(metadata_path.read_bytes()),
        "cell_count": len(notebook["cells"]), "base_009_cell_count": len(native_sources),
        "cells": mapping, "inserted_cell_indices": list(range(insertion_index, insertion_index + len(inserts))),
        "helper_files": [str(path.relative_to(ROOT)) for path in helpers],
        "formal_game_selection": "unchanged _competition_games() enumerates live gateway available_environments",
        "formal_and_save_solver_interventions": ["persistent Python computation within each level"],
        "inherited_009_solver_settings": {key: config["solver"][key] for key in (
            "n_passes", "concurrency", "active_streams", "max_runtime_s_per_game", "warmup_action_games")},
        "research_helpers_not_installed": ["request_deadline", "inference_timing", "scheduler_observer"],
        "research_comparison_requirement": "Research A/B must retain the same solver-affecting baseline behavior or separately report any deadline/warmup difference; no diagnostic cut or public game filter is installed here.",
        "native_helper_writefile_cells": True, "cell_exec_compile_eval_wrappers": False,
        "runtime_note": "Persistent Python reuses the original sandbox IPC per agent/level and refreshes the original runtime state; no repair, scheduler, request-deadline, or observation-interface patch is installed.",
        "state": "built_locally_not_run_not_pushed_not_submitted",
        "push_timeout_seconds": config["hard_limit_seconds"],
        "submission_command_template": (
            f"kaggle competitions submit arc-prize-2026-arc-agi-3 -k {config['kernel_id']} "
            "-v <actual-successful-gpu-smoke-version> -f submission.parquet -m <message>"),
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Save all small local inputs needed to inspect or reproduce this builder.
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
