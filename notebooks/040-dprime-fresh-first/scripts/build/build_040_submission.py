"""Build 040 from the exact scored 009v2 notebook; no remote operations."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from pprint import pformat
import shutil
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5"
REMOTE_SRC = "/kaggle/dprime_candidate/src"


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def source(cell: dict) -> str:
    value = cell["source"]
    return "".join(value) if isinstance(value, list) else value


def code(text: str) -> dict:
    return {"cell_type": "code", "source": text.splitlines(keepends=True),
            "metadata": {}, "execution_count": None, "outputs": []}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected unique source anchor: {old[:90]!r}")
    return text.replace(old, new, 1)


def formal_config(cell: dict) -> dict:
    # Inspected assignment-only configuration, isolated from all runtime code.
    bm = SimpleNamespace(solver=SimpleNamespace())
    scope = {"bm": bm, "TRUE_SUBMISSION": True, "USE_PRIORITY_SCHEDULING": True,
             "print": lambda *args: None, "__builtins__": {}}
    exec(compile(source(cell), "<040-formal-configuration>", "exec"), scope)
    return {"solver": vars(bm.solver), "n_passes": bm.n_passes,
            "game_weights": bm.game_weights, "demo_excluded_games": scope["demo_excluded_games"]}


def build(config_path: Path, out: Path) -> dict:
    config = json.loads(config_path.read_text())
    base_path = ROOT / config["base_notebook"]
    if digest(base_path.read_bytes()) != BASE_SHA or config["base_source_sha256"] != BASE_SHA:
        raise ValueError("Use exact formal009v2 source")
    if (config["id"] != "040-dprime-fresh-first"
            or config["kernel_id"] != "jiyujia/arc3-040-dprime-fresh-first"
            or config["hard_limit_seconds"] != 32400
            or config["solver"]["research_interventions"] != ["dprime_priority_fresh_first"]
            or config["dprime"]["price_fresh"] is not False
            or config["dprime"]["fade_fraction"] != 0.4):
        raise ValueError("Unexpected candidate identity or intervention")
    base = json.loads(base_path.read_text())
    if len(base["cells"]) != 25:
        raise ValueError("Expected25-cell009v2")
    helper = ROOT / config["dprime"]["implementation"]
    if digest(helper.read_bytes()) != config["dprime"]["implementation_sha256"]:
        raise ValueError("Pinned helper changed")
    public_path = ROOT / config["dprime"]["public_source"]
    if digest(public_path.read_bytes()) != config["dprime"]["public_source_sha256"]:
        raise ValueError("Public source snapshot changed")
    public = json.loads(public_path.read_text())
    if digest(source(public["cells"][17])) != config["dprime"]["public_cell_source_sha256"]:
        raise ValueError("Public D-prime source cell changed")
    oldmeta_path = base_path.parent / "kernel-metadata.json"
    oldmeta = json.loads(oldmeta_path.read_text())
    if oldmeta["docker_image"] != config["deployment"]["docker_image"]:
        raise ValueError("Retain009 image for this candidate")
    package_init = ROOT / "src/arc3_research/__init__.py"
    tracked = [base_path, oldmeta_path, config_path, Path(__file__).resolve(),
               helper, package_init, public_path,
               ROOT / config["dprime"]["independent_formula_review"],
               ROOT / config["deployment"]["input_pins_evidence"]]
    hashes = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in tracked}
    notebook = copy.deepcopy(base)
    bootstrap = source(base["cells"][0])
    bootstrap = bootstrap[bootstrap.index("# Readable save-smoke support."):]
    bootstrap = bootstrap.replace('"revision": 2,', '"revision": ARC3_SUBMISSION_CONFIG["revision"],')
    bootstrap = bootstrap.replace("009 v2 save smoke", "040 save smoke")
    notebook["cells"][0] = code(
        "# 040 configuration and frozen source provenance.\nARC3_SUBMISSION_CONFIG = "
        + pformat(config, width=100, sort_dicts=False)
        + "\n\nARC3_SUBMISSION_SOURCE_HASHES = " + pformat(hashes, width=100, sort_dicts=False)
        + "\n\n" + bootstrap)
    notebook["cells"][2]["source"] = (
        "# ARC3 040 — D-prime with baseline fresh-first admission\n\n"
        "Based on our exact009v2 solver (highest observed formal public31.16), Daniel Franzen, "
        "Jeroen Cottaar and Tufa Labs. D-prime formula/mean-token pace/tail fade are adapted "
        "from tantan0327's publicv2 and the Affectify D-prime proposal. All original attribution "
        "remains below. PRICE_FRESH=False retains009 initial-game admission; this is an "
        "unproven modified scheduler candidate and does not claim to reproduce a public33.55. "
        "Model, prompts,10streams, serving,009 Docker, formal gateway, one pass and31920s remain "
        "unchanged. Two-game300s save smoke proves execution only.\n\n"
        + source(base["cells"][2])).splitlines(keepends=True)
    run_cell = source(base["cells"][22])
    run_cell = replace_once(run_cell, "        arc3_validate_save_benchmark()\n",
        "        arc3_validate_save_benchmark()\n"
        "        ARC3_DPRIME_FINAL = ARC3_DPRIME_PATCH.snapshot()\n"
        "        if not ARC3_DPRIME_FINAL['active'] or ARC3_DPRIME_FINAL['price_fresh']:\n"
        "            raise RuntimeError('040 scheduler identity changed during save')\n"
        "        (WORKING_DIR / 'dprime-final.json').write_text(\n"
        "            json.dumps(ARC3_DPRIME_FINAL, indent=2) + '\\n')\n"
        "        ARC3_SAVE_REPORT['dprime_snapshot'] = ARC3_DPRIME_FINAL\n")
    notebook["cells"][22]["source"] = run_cell.splitlines(keepends=True)
    inserts = [code("# Install D-prime after benchmark configuration, before any sessions.\n"
                    f"Path({REMOTE_SRC + '/arc3_research'!r}).mkdir(parents=True, exist_ok=True)\n")]
    for path in (package_init, helper):
        body = path.read_text()
        if not body.endswith("\n"):
            raise ValueError("Native source payload must end inLF")
        inserts.append(code(f"%%writefile {REMOTE_SRC}/arc3_research/{path.name}\n" + body))
    inserts.append(code(
        f"sys.path.insert(0, {REMOTE_SRC!r})\n"
        "from arc3_research.dprime_priority import install_dprime_priority\n"
        "ARC3_DPRIME_PATCH = install_dprime_priority(price_fresh=False)\n"
        "ARC3_DPRIME_INITIAL = ARC3_DPRIME_PATCH.snapshot()\n"
        "assert ARC3_DPRIME_INITIAL['active'] and not ARC3_DPRIME_INITIAL['price_fresh']\n"
        "(WORKING_DIR / 'dprime-install.json').write_text(\n"
        "    json.dumps(ARC3_DPRIME_INITIAL, indent=2) + '\\n')\n"
        "print('040 D-prime installed:', ARC3_DPRIME_INITIAL, flush=True)\n"))
    notebook["cells"][19:19] = inserts
    for cell in notebook["cells"]:
        cell["metadata"] = {}
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    metadata = copy.deepcopy(oldmeta)
    metadata.pop("id_no", None)
    metadata.update(id=config["kernel_id"], title=config["kernel_title"],
                    code_file="submission.ipynb", is_private=True, enable_gpu=True,
                    enable_tpu=False, enable_internet=False,
                    machine_shape="NvidiaRtxPro6000", docker_image_pinning_type="original")
    for key in ("docker_image", "dataset_sources", "model_sources", "competition_sources"):
        metadata[key] = config["deployment"][key]
    notebook["metadata"].setdefault("kaggle", {}).update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False,
        dataSources=config["deployment"]["expected_data_sources"])
    stripped = copy.deepcopy(notebook)
    del stripped["cells"][19:23]
    changed = [i for i, (left, right) in enumerate(zip(base["cells"], stripped["cells"]))
               if source(left) != source(right)]
    if changed != [0, 2, 22]:
        raise ValueError(f"Unexpected009 changes: {changed}")
    if formal_config(stripped["cells"][18]) != formal_config(base["cells"][18]):
        raise ValueError("Formal configuration changed")
    # The formal branch and native await call are retained verbatim.
    original_formal = "if TRUE_SUBMISSION:\n    await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)\n"
    if original_formal not in run_cell:
        raise ValueError("Formal gateway invocation changed")
    compiled = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        text = source(cell)
        if text.startswith("%%writefile "):
            header, text = text.split("\n", 1)
            if header.endswith(".patch"):
                continue
        text = "\n".join("pass  # retained shell magic" if line.lstrip().startswith("!") else line
                         for line in text.splitlines())
        compile(text, f"<040-cell-{index}>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        compiled.append(index)
    checks = {"status": "passed_local_static_only", "baseline009_sha_verified": True,
              "native_cells": True, "unmodified009_code_cells_except": [0, 22],
              "insertion_indices": [19, 20, 21, 22], "installed_after_unpickle_before_run": True,
              "formal_config_unchanged": formal_config(stripped["cells"][18]),
              "formal_gateway_invocation_unchanged": True,
              "fresh_first_retained": True, "compiled_cell_indices": compiled,
              "same009_docker": True, "explicit_input_version_pins": True,
              "gpu_run": False, "formal_score_known": False}
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "submission.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=1) + "\n")
    if notebook_path.stat().st_size >= 1_000_000:
        raise ValueError("Notebook source exceeds1MB")
    (out / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    manifest = {"id": config["id"], "kernel_ref": config["kernel_id"],
                "notebook_sha256": digest(notebook_path.read_bytes()),
                "metadata_sha256": digest((out / "kernel-metadata.json").read_bytes()),
                "source_hashes": hashes, "cell_count": len(notebook["cells"]),
                "bytes": notebook_path.stat().st_size, "changed009_cell_indices": changed,
                "insertion_indices": [19, 20, 21, 22],
                "sole_solver_change": "dprime_formula_mean_token_pace_fade0.4_fresh_first",
                "formal_config": checks["formal_config_unchanged"],
                "expected_remote_input_ids": config["deployment"]["expected_data_sources"],
                "push_timeout_seconds": 32400,
                "state": "built_locally_not_pushed_not_submitted"}
    (out / "static-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for relative in hashes:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/040-dprime-fresh-first.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "notebooks/040-dprime-fresh-first")
    args = parser.parse_args()
    manifest = build(args.config.resolve(), args.output_dir.resolve())
    print(json.dumps({key: manifest[key] for key in ("kernel_ref", "notebook_sha256", "bytes", "cell_count", "state")}, indent=2))


if __name__ == "__main__":
    main()
