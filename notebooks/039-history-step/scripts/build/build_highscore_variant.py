"""Build v83 baseline/step-alias notebooks locally; never upload or run them."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from pprint import pformat
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
REMOTE_SRC = "/kaggle/highscore_step/src"
VARIANTS = {"baseline": "038-highscore-baseline", "history_step": "039-history-step"}


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def source(cell: dict) -> str:
    value = cell["source"]
    return "".join(value) if isinstance(value, list) else value


def code_cell(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "source": text.splitlines(keepends=True),
            "execution_count": None, "outputs": []}


def load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("_v83_deployment_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_config(config: dict, adapter_config: dict) -> None:
    variant = config["variant"]
    if variant not in VARIANTS or config["id"] != VARIANTS[variant]:
        raise ValueError("Unknown highscore variant")
    for key in ("base_notebook", "base_source_sha256", "hard_limit_seconds", "machine_shape",
                "enable_internet", "input_resolution_timeout_seconds", "formal_mode", "save_mode",
                "save_placeholder_is_scored", "formal_submission_file_owner", "official_save_protocol",
                "save_smoke", "source_provenance", "source_provenance_sha256", "upstream", "deployment"):
        if config[key] != adapter_config[key]:
            raise ValueError(f"Variant must retain frozen v83 deployment setting: {key}")
    expected = copy.deepcopy(adapter_config["solver"])
    expected["research_interventions"] = [] if variant == "baseline" else ["history_step_compat"]
    if config["solver"] != expected or "segmentation_runs" in config:
        raise ValueError("Unexpected solver intervention or old segmentation configuration")
    if config["kernel_id"].split("/", 1)[0] != "zhuating":
        raise ValueError("Retain the observed owner zhuating")


def validate_cells(notebook: dict, reference: dict, original: dict, config: dict,
                   inserts: list[dict], adapter) -> dict:
    variant = config["variant"]
    insertion = 13
    stripped = copy.deepcopy(notebook)
    if inserts:
        del stripped["cells"][insertion:insertion + len(inserts)]
    if len(stripped["cells"]) != 25:
        raise ValueError("Baseline must contain original23 cells plus2 deployment cells")
    changed = []
    for i, (left, right) in enumerate(zip(reference["cells"], stripped["cells"])):
        if left["cell_type"] != right["cell_type"]:
            raise ValueError(f"Cell type changed: {i}")
        if source(left) != source(right):
            changed.append(i)
    if changed != [0, 2]:
        raise ValueError(f"Unexpected changes beyond new identity/provenance: {changed}")
    assert source(stripped["cells"][4]) == source(original["cells"][2])
    configuration = adapter.check_customization(
        source(original["cells"][16]), source(stripped["cells"][18]), config)
    compiled = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        text = source(cell)
        if "from arc3_research.segmentation_runs" in text or "install_segmentation_runs()" in text:
            raise ValueError("Old exact-pixels intervention leaked into output")
        if text.startswith("%%writefile "):
            header, text = text.split("\n", 1)
            if header.endswith(".patch"):
                continue
        # Retained native shell-magic lines were already reviewed in v83.
        text = "\n".join("pass  # retained IPython shell syntax" if line.lstrip().startswith("!") else line
                         for line in text.splitlines())
        compile(text, f"<highscore-variant-cell-{index}>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compiled.append(index)
    if variant == "baseline":
        assert not inserts
        assert not any("install_history_step_compat()" in source(c) for c in notebook["cells"])
    else:
        assert len(inserts) == 4
        assert sum("ARC3_HISTORY_STEP_PATCH = install_history_step_compat()" in source(c)
                   for c in notebook["cells"]) == 1
        assert "source_entries = _source_path_entries(BUNDLE_DIR)" in source(notebook["cells"][12])
        assert "with open" in source(notebook["cells"][20])
    return {
        "status": "passed_local_static_only", "variant": variant,
        "compiled_code_cell_indices": compiled,
        "original_v83_harness_patch_retained": True,
        "removed_all_four_037_segmentation_cells": True,
        "segmentation_runs_not_installed": True,
        "formal_configuration_equals_original_v83": True,
        "formal_configuration_fixture": configuration,
        "unchanged_deployment_cells_except_identity": True,
        "baseline_identity_cell_changes": changed,
        "native_payload_cells": True,
        "new_helper_before_benchmark_unpickle": bool(inserts),
        "gpu_or_model_run": False, "formal_score_known": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    adapter_config_path = ROOT / config["adapter_037_config"]
    adapter_builder_path = ROOT / config["adapter_037_builder"]
    if (sha256(adapter_config_path.read_bytes()) != config["adapter_037_config_sha256"]
            or sha256(adapter_builder_path.read_bytes()) != config["adapter_037_builder_sha256"]):
        raise ValueError("The validated037 deployment adapter changed")
    adapter_config = json.loads(adapter_config_path.read_text())
    validate_config(config, adapter_config)
    adapter = load_adapter(adapter_builder_path)
    variant = config["variant"]
    source_path = ROOT / config["base_notebook"]
    if sha256(source_path.read_bytes()) != config["base_source_sha256"]:
        raise ValueError("Frozen scoredv83 source changed")
    original = json.loads(source_path.read_text())

    # Reuse only the already validated input/save adaptation. The intermediate
    # notebook is never run, uploaded, or delivered with its segmentation patch.
    with tempfile.TemporaryDirectory(prefix="arc3-v83-adapter-") as tmp:
        subprocess.run([sys.executable, str(adapter_builder_path), "--config", str(adapter_config_path),
                        "--output-dir", tmp], check=True, capture_output=True, text=True)
        intermediate = json.loads((Path(tmp) / "submission.ipynb").read_text())
        inherited = json.loads((Path(tmp) / "build-manifest.json").read_text())
        metadata = json.loads((Path(tmp) / "kernel-metadata.json").read_text())
    if inherited["inserted_cell_indices"] != [13, 14, 15, 16]:
        raise ValueError("037 helper cell mapping changed")
    if "install_segmentation_runs()" not in source(intermediate["cells"][16]):
        raise ValueError("Expected the explicit037 installation block")
    reference = copy.deepcopy(intermediate)
    del reference["cells"][13:17]
    notebook = copy.deepcopy(reference)

    tracked = [ROOT / p for p in inherited["source_hashes"]]
    tracked.extend([Path(__file__).resolve(), config_path])
    helper_path = None
    if variant == "history_step":
        helper_path = ROOT / config["history_step_compat"]["implementation"]
        if sha256(helper_path.read_bytes()) != config["history_step_compat"]["implementation_sha256"]:
            raise ValueError("Pinned history-step helper changed")
        tracked.append(helper_path)
    hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in tracked}
    number = config["id"].split("-", 1)[0]
    notebook["cells"][0] = code_cell(
        f"# {number} configuration and scored v83 provenance.\n"
        "ARC3_SUBMISSION_CONFIG = " + pformat(config, width=100, sort_dicts=False) + "\n\n"
        "ARC3_SUBMISSION_SOURCE_HASHES = " + pformat(hashes, width=100, sort_dicts=False) + "\n\n"
        + adapter.BOOTSTRAP.replace("037 save smoke", f"{number} save smoke"))
    description = (
        "This is the unmodified v83 solver with the verified deployment/save adapter."
        if variant == "baseline" else
        "The only solver change is a read-only HistoryEntryView.step alias for its existing frame.step.")
    intro = (
        f"# ARC3 {number} — {config['kernel_title']}\n\n"
        "Based on Roman Tamrazov's The AGI Boys v83 (scriptVersionId359573474), whose "
        "displayed historical public score is35.35. Full credit remains with Roman Tamrazov, "
        "Daniel Franzen, Jeroen Cottaar and Tufa Labs. " + description + " "
        "The model, image, input versions, serving, sampling, scheduler, formal gateway and "
        "31920-second solver budget retain v83 settings. The two-game300-second GPU save smoke "
        "checks execution only and does not establish a leaderboard score.\n\n"
        + source(original["cells"][0]))
    notebook["cells"][2]["source"] = intro.splitlines(keepends=True)
    inserts = []
    if helper_path is not None:
        inserts.append(code_cell(
            "# Install only the read-only history step compatibility alias.\n"
            f"Path({REMOTE_SRC + '/arc3_research'!r}).mkdir(parents=True, exist_ok=True)\n"))
        for path in (ROOT / "src/arc3_research/__init__.py", helper_path):
            body = path.read_text()
            if not body.endswith("\n"):
                raise ValueError("Native helper source must end in LF")
            inserts.append(code_cell(f"%%writefile {REMOTE_SRC}/arc3_research/{path.name}\n" + body))
        inserts.append(code_cell(
            f"sys.path.insert(0, {REMOTE_SRC!r})\n"
            "from arc3_research.history_step_compat import install_history_step_compat\n"
            "ARC3_HISTORY_STEP_PATCH = install_history_step_compat()\n"
            "ARC3_HISTORY_STEP_SNAPSHOT = ARC3_HISTORY_STEP_PATCH.snapshot()\n"
            "assert ARC3_HISTORY_STEP_SNAPSHOT['active']\n"
            "(ARC3_SUBMISSION_WORKING / 'history-step-install.json').write_text(\n"
            "    json.dumps(ARC3_HISTORY_STEP_SNAPSHOT, indent=2) + '\\n')\n"
            "print('039 history step compatibility installed:', ARC3_HISTORY_STEP_SNAPSHOT)\n"))
        notebook["cells"][13:13] = inserts
    metadata.update(id=config["kernel_id"], title=config["kernel_title"])
    out = args.output_dir.resolve() if args.output_dir else ROOT / "notebooks" / config["id"]
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "submission.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=1) + "\n")
    metadata_path = out / "kernel-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    checks = validate_cells(notebook, reference, original, config, inserts, adapter)
    if notebook_path.stat().st_size >= 1000000:
        raise ValueError("Notebook exceeds Kaggle1MB source limit")
    if metadata["docker_image"] != config["deployment"]["docker_image"]:
        raise ValueError("Pinned v83 image changed")
    checks["notebook_sha256"] = sha256(notebook_path.read_bytes())
    checks["private_offline_RTX_PRO6000"] = (
        metadata["is_private"] and metadata["enable_gpu"] and not metadata["enable_internet"]
        and metadata["machine_shape"] == "NvidiaRtxPro6000")
    assert checks["private_offline_RTX_PRO6000"]
    manifest = {
        "id": config["id"], "variant": variant, "config": config, "source_hashes": hashes,
        "notebook_sha256": checks["notebook_sha256"],
        "metadata_sha256": sha256(metadata_path.read_bytes()),
        "cell_count": len(notebook["cells"]), "base_source_sha256": config["base_source_sha256"],
        "upstream": config["upstream"], "deployment_metadata": metadata,
        "original_patch_cell_sha256": sha256(source(original["cells"][2])),
        "generated_patch_cell_sha256": sha256(source(notebook["cells"][4])),
        "intermediate037_notebook_executed": False,
        "intermediate037_notebook_sha256": inherited["notebook_sha256"],
        "removed037_cell_indices": [13, 14, 15, 16],
        "inserted_cell_indices": list(range(13, 13 + len(inserts))),
        "sole_solver_change": None if variant == "baseline" else "history_step_compat_v1",
        "segmentation_runs_installed": False,
        "build_dependency_note": "Some source hashes identify037's local adapter dependencies, including its unused segmentation helper; that helper has no payload/import/install cell in this delivered notebook.",
        "formal_branch_configuration_check": checks["formal_configuration_fixture"],
        "remote_input_ids_must_match": config["deployment"]["expected_data_sources"],
        "push_timeout_seconds": config["hard_limit_seconds"],
        "submission_command_template": (
            f"kaggle competitions submit arc-prize-2026-arc-agi-3 -k {config['kernel_id']} "
            "-v <actual-successful-gpu-smoke-version> -f submission.parquet -m <message>"),
        "state": "built_locally_not_pushed_not_submitted",
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "static-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    for relative in hashes:
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() != (ROOT / relative).resolve():
            shutil.copyfile(ROOT / relative, destination)
    print(json.dumps({"notebook": str(notebook_path), "variant": variant,
                      "sha256": manifest["notebook_sha256"], "bytes": notebook_path.stat().st_size,
                      "cells": len(notebook["cells"]), "remote_operations": 0}, indent=2))


if __name__ == "__main__":
    main()
