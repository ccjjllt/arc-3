"""Build 009's independent formal baseline; this command never uploads or runs it."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old[:100]!r}")
    return source.replace(old, new, 1)


def guard(source: str, index: int) -> str:
    # Indenting raw Python changes the contents of embedded multiline strings
    # (including the serving launcher's scripts). Compile the unchanged body.
    filename = f"009-baseline-cell-{index}"
    compiled = compile(source, filename, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    if compiled.co_flags & inspect.CO_COROUTINE:
        return ("if ARC3_IS_COMPETITION_RERUN:\n"
                "    import ast\n"
                f"    await eval(compile({source!r}, {filename!r}, 'exec', "
                "flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), globals())\n")
    return ("if ARC3_IS_COMPETITION_RERUN:\n"
            f"    exec(compile({source!r}, {filename!r}, 'exec'), globals())\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/009-baseline-submission.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    source_path = ROOT / config["base_notebook"]
    base = json.loads(source_path.read_text())
    if sha256(source_path.read_bytes()) != config["base_source_sha256"]:
        raise ValueError("Baseline notebook differs from the reviewed Franzen v3 snapshot")
    if len(base["cells"]) != 23:
        raise ValueError("Expected all 23 baseline cells")
    if config["hard_limit_seconds"] != 32400 or config["machine_shape"] != "NvidiaRtxPro6000":
        raise ValueError("009 preserves the 9-hour RTX PRO 6000 formal baseline")
    if config["enable_internet"] is not False or config["solver"]["research_interventions"]:
        raise ValueError("009 must remain offline and free of research interventions")
    helper_path = ROOT / "src/arc3_research/submission_inputs.py"
    helper_source = helper_path.read_text()
    support_path = ROOT / config["official_save_protocol"]["source_snapshot"]
    if sha256(support_path.read_bytes()) != config["official_save_protocol"]["source_sha256"]:
        raise ValueError("Official save-protocol source snapshot differs from the reviewed file")
    metadata_path = source_path.parent / "kernel-metadata.json"
    tracked = [source_path, metadata_path, Path(__file__), config_path, helper_path, support_path]
    hashes = {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in tracked}
    notebook = copy.deepcopy(base)
    changes: dict[int, list[str]] = {}
    cells = notebook["cells"]
    sources = ["".join(cell["source"]) for cell in cells]
    sources[0] = (
        "# ARC3 009 — Formal baseline submission\n\n"
        "Save mode only emits the organizer starter's unscored placeholder; it does not load a model, "
        "play games, or validate leaderboard performance. Kaggle's competition rerun executes the "
        "full Franzen v3 GPU baseline against the live gateway, which owns the real submission file. "
        "No 003/006/007 research interventions are enabled. Inputs resolve by actual mounted files.\n\n"
        + sources[0]
    )
    changes[0] = ["Prepend 009 identity and explicit save-versus-scoring distinction; retain attribution"]
    patch_header, separator, patch_source = sources[2].partition("\n")
    if patch_header != "%%writefile /kaggle/harness-changes.patch" or not separator:
        raise ValueError("Unexpected baseline patch cell")
    bootstrap = f'''import json, os, time
from pathlib import Path

ARC3_IS_COMPETITION_RERUN = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {{"1", "true"}}
ARC3_SUBMISSION_CONFIG = json.loads({json.dumps(config)!r})
ARC3_SUBMISSION_SOURCE_HASHES = json.loads({json.dumps(hashes)!r})
ARC3_SUBMISSION_WORKING = Path("/kaggle/working" if ARC3_IS_COMPETITION_RERUN else os.environ.get("ARC3_SAVE_OUTPUT_DIR", "/kaggle/working"))
ARC3_SUBMISSION_WORKING.mkdir(parents=True, exist_ok=True)
ARC3_SUBMISSION_MODE = {{
    "experiment": ARC3_SUBMISSION_CONFIG["id"],
    "mode": "competition_rerun" if ARC3_IS_COMPETITION_RERUN else "save_only",
    "placeholder": not ARC3_IS_COMPETITION_RERUN,
    "source_hashes": ARC3_SUBMISSION_SOURCE_HASHES,
    "save_is_performance_validation": False,
    "formal_submission_file_owner": "Kaggle gateway",
    "notebook_hard_limit_seconds": 32400,
}}
(ARC3_SUBMISSION_WORKING / "submission-mode.json").write_text(json.dumps(ARC3_SUBMISSION_MODE, indent=2) + "\\n")
_input_namespace = {{}}
exec(compile({helper_source!r}, "submission_inputs.py", "exec"), _input_namespace)
ARC3_SUBMISSION_INPUTS = _input_namespace["resolve_submission_inputs"](
    input_root="/kaggle/input" if ARC3_IS_COMPETITION_RERUN else os.environ.get("ARC3_SAVE_INPUT_ROOT", "/kaggle/input"),
    timeout_seconds=ARC3_SUBMISSION_CONFIG["input_resolution_timeout_seconds"],
    report_path=ARC3_SUBMISSION_WORKING / "input-paths.json",
)
if ARC3_IS_COMPETITION_RERUN:
    Path("/kaggle/harness-changes.patch").write_text({patch_source!r})
    print("009: formal competition rerun; the gateway will produce the scored submission.", flush=True)
else:
    # Organizer starter protocol: this file only makes the save version selectable.
    # It is not a measured score and this branch never executes in a competition rerun.
    # https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter/blob/main/scripts/build_notebook.py
    import pandas as pd
    pd.DataFrame([["1_0", "1", True, 1]],
                 columns=["row_id", "game_id", "end_of_game", "score"]).to_parquet(
        ARC3_SUBMISSION_WORKING / "submission.parquet", index=False)
    print("009: SAVE ONLY — unscored official-starter placeholder; no model load or game actions.", flush=True)
'''
    sources[2] = bootstrap
    changes[2] = [
        "Strict platform rerun gate; non-rerun uses the official organizer save-only placeholder",
        "Resolve read-only input markers during save and rerun; no requirement for public environment_files",
        "Replace writefile magic with Path.write_text of the byte-identical original patch",
        "Record mode and build source hashes; no scored-file write in the rerun branch",
    ]
    path_replacements = {
        "/kaggle/input/datasets/dfranzen/pennyroyal-v253": "wheelhouse",
        "/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy": "bundle",
        "/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1": "model",
        "/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1": "draft",
    }
    for path, key in path_replacements.items():
        sources[4] = replace_once(sources[4], repr(path), f"ARC3_SUBMISSION_INPUTS[{key!r}]")
    sources[4] = replace_once(sources[4], "!rm -Rf $BUNDLE_DIR", 'subprocess.run(["rm", "-Rf", str(BUNDLE_DIR)], check=True)')
    sources[4] = replace_once(sources[4], "!cp -a $ORIG_BUNDLE_DIR $BUNDLE_DIR", 'subprocess.run(["cp", "-a", str(ORIG_BUNDLE_DIR), str(BUNDLE_DIR)], check=True)')
    changes[4] = [
        "Resolve four attached input roots; retain warmup RESET, all solver env and serving config",
        "Replace two shell magics with checked subprocess calls so the body compiles as Python",
    ]
    sources[8] = replace_once(
        sources[8], '"/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"',
        'ARC3_SUBMISSION_INPUTS["competition_wheels"]',
    )
    changes[8] = ["Install the same competition arc-agi wheel from its resolved mounted root"]
    sources[16] = (
        'if float(getattr(target, "max_runtime_s", 0.0) or 0.0) != 32400.0:\n'
        '    raise RuntimeError(f"Expected the 32400-second submission target, got {target.max_runtime_s!r}")\n\n'
        + sources[16]
    )
    changes[16] = ["Assert the original target is also 32400 seconds during formal rerun; original solver settings retained"]
    offline_start = sources[20].index("# Build the offline game list")
    offline_end = sources[20].index("# The gateway can take a while")
    sources[20] = sources[20][:offline_start] + sources[20][offline_end:]
    offline_branch_start = sources[20].index("else:\n    # Interactive run:")
    offline_branch_end = sources[20].index("# Outside a real submission,")
    sources[20] = sources[20][:offline_branch_start] + sources[20][offline_branch_end:]
    soft_start = sources[20].index("# Outside a real submission,")
    soft_end = sources[20].index("# Play the benchmark;")
    sources[20] = sources[20][:soft_start] + "# Preserve the original competition deadline behavior.\nsoft_end = None\n\n" + sources[20][soft_end:]
    placeholder_start = sources[20].index("if not TRUE_SUBMISSION:\n    # An offline run isn't scored")
    sources[20] = sources[20][:placeholder_start]
    changes[20] = [
        "Remove public OFFLINE game enumeration and branch; formal gateway code retained",
        "Remove non-submission soft deadline and duplicate placeholder writer; formal soft_end remains None",
    ]
    sources[19] = (
        "## 9. Run the formal benchmark\n\n"
        "Only a Kaggle competition rerun executes this cell: it waits for the live gateway and "
        "plays the COMPETITION Arcade. Save mode performs input marker checks and emits the "
        "official starter's unscored placeholder in cell 2; it does not play public or hidden games."
    )
    changes[19] = ["Document the actual formal-only execution and light save behavior"]
    body_hashes = {}
    for index, cell in enumerate(cells):
        cell["metadata"] = {}
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
            if index != 2:
                body_hashes[index] = sha256(sources[index])
                sources[index] = guard(sources[index], index)
                changes.setdefault(index, []).append("Guard a compile/exec of the exact body; await coroutine cells; skipped during save")
        cell["source"] = sources[index]
    notebook["metadata"].pop("papermill", None)
    notebook["metadata"].setdefault("kaggle", {}).update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False,
    )
    notebook["nbformat"] = 4
    notebook["nbformat_minor"] = 4
    meta = json.loads(metadata_path.read_text())
    meta.pop("id_no", None)
    meta.update(id=config["kernel_id"], title=config["kernel_title"], code_file="submission.ipynb",
                is_private=True, enable_gpu=True, enable_tpu=False, enable_internet=False,
                machine_shape=config["machine_shape"], docker_image_pinning_type="original")
    out = args.output_dir.resolve() if args.output_dir else ROOT / "notebooks" / config["id"]
    out.mkdir(parents=True, exist_ok=True)
    notebook_path = out / "submission.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=1) + "\n")
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    manifest = {
        "id": config["id"], "config": config, "source_hashes": hashes,
        "base_source_sha256": config["base_source_sha256"],
        "notebook_sha256": sha256(notebook_path.read_bytes()),
        "metadata_sha256": sha256((out / "kernel-metadata.json").read_bytes()),
        "cell_count": len(cells), "original_patch_sha256": sha256(patch_source),
        "generated_patch_sha256": sha256(patch_source),
        "cells": [{
            "index": i, "cell_type": cell["cell_type"],
            "original_source_sha256": sha256("".join(base["cells"][i]["source"])),
            "generated_source_sha256": sha256(sources[i]),
            "rerun_body_sha256": body_hashes.get(i),
            "changes": changes.get(i, []),
        } for i, cell in enumerate(cells)],
        "submission_command_template": (
            f"kaggle competitions submit arc-prize-2026-arc-agi-3 -k {config['kernel_id']} "
            "-v <actual-successful-saved-version> -f submission.parquet -m <message>"
        ),
        "push_timeout_seconds": 32400,
        "state": "built_locally_not_pushed_not_submitted",
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"notebook": str(notebook_path), "sha256": manifest["notebook_sha256"],
                      "bytes": notebook_path.stat().st_size, "cells": len(cells)}, indent=2))


if __name__ == "__main__":
    main()
