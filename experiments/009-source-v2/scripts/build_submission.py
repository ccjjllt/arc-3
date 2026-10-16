"""Build 009 revision 2 as ordinary, readable notebook cells; never upload or run."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old[:100]!r}")
    return source.replace(old, new, 1)


def code_cell(source: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "source": source.splitlines(keepends=True),
            "execution_count": None, "outputs": []}


BOOTSTRAP = r'''# Readable save-smoke support. No notebook cell is wrapped or dynamically executed.
import atexit
import hashlib
import json
import os
import signal
import threading
import time
from pathlib import Path

ARC3_IS_COMPETITION_RERUN = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
ARC3_SUBMISSION_WORKING = Path("/kaggle/working")
ARC3_SUBMISSION_WORKING.mkdir(parents=True, exist_ok=True)
ARC3_SAVE_STARTED_MONOTONIC = time.monotonic()
ARC3_SAVE_SERVER_PROC = None
ARC3_SAVE_SERVER_PGID = None
ARC3_SAVE_TIMER = None
ARC3_SAVE_CLEANUP_LOCK = threading.Lock()
ARC3_SAVE_REPORT = {
    "revision": 2,
    "mode": "competition_rerun" if ARC3_IS_COMPETITION_RERUN else "save_gpu_smoke",
    "status": "not_applicable" if ARC3_IS_COMPETITION_RERUN else "starting",
    "health_200_observed": False,
    "placeholder_written": False,
    "source_hashes": ARC3_SUBMISSION_SOURCE_HASHES,
    "notebook_hard_limit_seconds": 32400,
    "save_total_limit_seconds": ARC3_SUBMISSION_CONFIG["save_smoke"]["total_timeout_seconds"],
    "formal_submission_file_owner": "Kaggle gateway",
}


def arc3_write_save_report():
    if not ARC3_IS_COMPETITION_RERUN:
        ARC3_SAVE_REPORT["elapsed_seconds"] = time.monotonic() - ARC3_SAVE_STARTED_MONOTONIC
        (ARC3_SUBMISSION_WORKING / "save-smoke-report.json").write_text(
            json.dumps(ARC3_SAVE_REPORT, indent=2) + "\n")


def arc3_stop_save_server():
    # Only this notebook's start_new_session=True Popen owns this process group.
    if ARC3_IS_COMPETITION_RERUN:
        return
    with ARC3_SAVE_CLEANUP_LOCK:
        pgid = ARC3_SAVE_SERVER_PGID
        proc = ARC3_SAVE_SERVER_PROC
        if pgid is None or ARC3_SAVE_REPORT.get("server_cleanup_complete"):
            return
        outcomes = []
        try:
            os.killpg(pgid, signal.SIGTERM)
            outcomes.append("SIGTERM sent to owned process group")
        except ProcessLookupError:
            outcomes.append("owned process group already exited")
        if proc is not None:
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        # The launcher may have exited before its workers. Still target only its group.
        try:
            os.killpg(pgid, signal.SIGKILL)
            outcomes.append("SIGKILL sent to remaining owned process group")
        except ProcessLookupError:
            pass
        if proc is not None:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                outcomes.append("owned process did not reap within 5 seconds")
        ARC3_SAVE_REPORT["server_cleanup_complete"] = True
        ARC3_SAVE_REPORT["server_cleanup"] = outcomes
        arc3_write_save_report()


def arc3_save_deadline_expired():
    if ARC3_SAVE_REPORT.get("status") == "passed":
        return
    ARC3_SAVE_REPORT["status"] = "failed"
    ARC3_SAVE_REPORT["failure"] = "save_total_timeout"
    arc3_write_save_report()
    arc3_stop_save_server()
    print("009 v2 save smoke exceeded its total timeout", flush=True)
    os._exit(124)


def arc3_save_cell_finished(result):
    error = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if error is not None:
        ARC3_SAVE_REPORT["status"] = "failed"
        ARC3_SAVE_REPORT["failure"] = type(error).__name__ + ": " + str(error)
        arc3_write_save_report()
        arc3_stop_save_server()
        if ARC3_SAVE_TIMER is not None:
            ARC3_SAVE_TIMER.cancel()


def arc3_validate_save_benchmark():
    path = ARC3_SUBMISSION_WORKING / "benchmark.json"
    raw = path.read_bytes()
    benchmark = json.loads(raw)
    runs = benchmark.get("game_runs", [])
    expected = ARC3_SUBMISSION_CONFIG["save_smoke"]["game_ids"]
    actual = [run["game_id"] for run in runs]
    if len(actual) != len(expected) or sorted(actual) != sorted(expected):
        raise RuntimeError(f"Save smoke game set mismatch: {actual!r}")
    per_game = []
    for run in runs:
        history = run.get("history", [])
        real_actions = sum(
            entry.get("action", {}).get("id") in {f"ACTION{i}" for i in range(1, 8)}
            for entry in history
        )
        tokens = sum(int(entry.get("generated_tokens", 0) or 0) for entry in history)
        tokens += int(run.get("final_generated_tokens", 0) or 0)
        per_game.append({"game_id": run["game_id"], "state": run.get("state"),
                         "non_reset_actions": real_actions, "generated_tokens": tokens,
                         "levels_completed": run.get("levels_completed"),
                         "offline_score": run.get("final_score")})
    ARC3_SAVE_REPORT["games"] = per_game
    ARC3_SAVE_REPORT["benchmark_sha256"] = hashlib.sha256(raw).hexdigest()
    arc3_write_save_report()
    if not ARC3_SAVE_REPORT["health_200_observed"]:
        raise RuntimeError("Save smoke did not observe model health 200")
    if any(item["state"] not in {"won", "cancelled"} or item["non_reset_actions"] <= 0
           or item["generated_tokens"] <= 0 for item in per_game):
        raise RuntimeError(f"Save smoke requires non-RESET gameplay and generated tokens in both games: {per_game!r}")
    return per_game


(ARC3_SUBMISSION_WORKING / "submission-mode.json").write_text(json.dumps({
    "experiment": ARC3_SUBMISSION_CONFIG["id"], "revision": 2,
    "mode": ARC3_SAVE_REPORT["mode"], "source_hashes": ARC3_SUBMISSION_SOURCE_HASHES,
    "save_smoke_is_leaderboard_validation": False,
    "formal_submission_file_owner": "Kaggle gateway",
}, indent=2) + "\n")
if not ARC3_IS_COMPETITION_RERUN:
    # A fresh failed smoke must not leave a previous version's selectable placeholder.
    (ARC3_SUBMISSION_WORKING / "submission.parquet").unlink(missing_ok=True)
    arc3_write_save_report()
    atexit.register(arc3_stop_save_server)
    get_ipython().events.register("post_run_cell", arc3_save_cell_finished)
    ARC3_SAVE_TIMER = threading.Timer(
        ARC3_SUBMISSION_CONFIG["save_smoke"]["total_timeout_seconds"], arc3_save_deadline_expired)
    ARC3_SAVE_TIMER.daemon = True
    ARC3_SAVE_TIMER.start()
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/009-baseline-submission.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    source_path = ROOT / config["base_notebook"]
    base = json.loads(source_path.read_text())
    if sha256(source_path.read_bytes()) != config["base_source_sha256"] or len(base["cells"]) != 23:
        raise ValueError("Expected the reviewed 23-cell Franzen v3 snapshot")
    if (config["revision"] != 2 or config["hard_limit_seconds"] != 32400
            or config["machine_shape"] != "NvidiaRtxPro6000"
            or config["enable_internet"] is not False or config["solver"]["research_interventions"]):
        raise ValueError("009 v2 requires the offline, unmodified 9-hour formal solver")
    smoke = config["save_smoke"]
    if (smoke["game_ids"] != ["sb26-7fbdac44", "cd82-fb555c5d"]
            or smoke["budget_seconds"] != 300 or smoke["concurrency"] != 2
            or smoke["n_passes"] != 1 or smoke["startup_timeout_seconds"] != 1500
            or smoke["total_timeout_seconds"] != 2400):
        raise ValueError("Unexpected save-smoke scope or budget")
    helper_path = ROOT / "src/arc3_research/submission_inputs.py"
    helper_source = replace_once(helper_path.read_text(), "from __future__ import annotations\n", "")
    support_path = ROOT / config["official_save_protocol"]["source_snapshot"]
    if sha256(support_path.read_bytes()) != config["official_save_protocol"]["source_sha256"]:
        raise ValueError("Official save-protocol snapshot changed")
    metadata_path = source_path.parent / "kernel-metadata.json"
    tracked = [source_path, metadata_path, Path(__file__), config_path, helper_path, support_path]
    hashes = {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in tracked}
    original = ["".join(cell["source"]) for cell in base["cells"]]
    sources = list(original)
    changes = {}
    if not sources[2].startswith("%%writefile /kaggle/harness-changes.patch\n"):
        raise ValueError("Unexpected original patch cell")
    sources[0] = (
        "# ARC3 009 v2 — baseline with a real GPU save smoke\n\n"
        "Ordinary notebook cells retain the original patch and serving source. Save mode loads "
        "the model, waits for health 200, then runs sb26 and cd82 concurrently for 300 seconds. "
        "Both games must generate tokens and perform non-RESET actions before the official "
        "unscored placeholder is written. Formal reruns retain the original live gateway, "
        "one pass, 120-task solver and 31,920-second solver budget. No research interventions.\n\n"
        + original[0]
    )
    changes[0] = ["Add revision 2 identity and truthful GPU save-smoke scope; retain original attribution"]
    path_replacements = {
        "/kaggle/input/datasets/dfranzen/pennyroyal-v253": "wheelhouse",
        "/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy": "bundle",
        "/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1": "model",
        "/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1": "draft",
    }
    for path, key in path_replacements.items():
        sources[4] = replace_once(sources[4], repr(path), f"ARC3_SUBMISSION_INPUTS[{key!r}]")
    changes[4] = ["Resolve four attached input paths; retain original shell magics, warmup, flags and serving settings"]
    sources[8] = replace_once(
        sources[8], '"/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"',
        'ARC3_SUBMISSION_INPUTS["competition_wheels"]',
    )
    changes[8] = ["Resolve mounted competition wheelhouse; install original wheel"]
    sources[12] = replace_once(sources[12], 'print(f"pid {proc.pid} -> {LOG}")',
        'print(f"pid {proc.pid} -> {LOG}")\n'
        'if not TRUE_SUBMISSION:\n'
        '    ARC3_SAVE_SERVER_PROC = proc\n'
        '    ARC3_SAVE_SERVER_PGID = proc.pid\n'
        '    ARC3_SAVE_REPORT["server_pid"] = proc.pid\n'
        '    ARC3_SAVE_REPORT["server_log"] = str(LOG)\n'
        '    arc3_write_save_report()')
    sources[12] = replace_once(sources[12],
        "while time.time() - NOTEBOOK_START_TIME < SERVER_STARTUP_TIMEOUT:",
        "while (time.time() - NOTEBOOK_START_TIME < SERVER_STARTUP_TIMEOUT if TRUE_SUBMISSION\n"
        "       else time.monotonic() - ARC3_SAVE_STARTED_MONOTONIC <\n"
        '       ARC3_SUBMISSION_CONFIG["save_smoke"]["startup_timeout_seconds"]):')
    sources[12] += '''
# Save smoke must observe the real service, not merely fall through the startup loop.
if not TRUE_SUBMISSION:
    if proc.poll() is not None:
        raise RuntimeError(f"Save model server exited before readiness: {proc.returncode}")
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"Save model health was {response.status}, expected 200")
    ARC3_SAVE_REPORT["health_200_observed"] = True
    ARC3_SAVE_REPORT["health_ready_elapsed_seconds"] = time.monotonic() - ARC3_SAVE_STARTED_MONOTONIC
    ARC3_SAVE_REPORT["status"] = "model_ready"
    arc3_write_save_report()
'''
    changes[12] = [
        "Retain serving configuration and native source; record only this save's Popen process group",
        "Formal startup condition unchanged; save allows 1500 seconds from bootstrap and requires health 200",
    ]
    old_else = original[16][original[16].index("else:\n"):original[16].index("# show config")]
    new_else = '''else:
    # Save smoke only. Formal settings above remain the original baseline.
    bm.n_passes = ARC3_SUBMISSION_CONFIG["save_smoke"]["n_passes"]
    bm.solver.concurrency = ARC3_SUBMISSION_CONFIG["save_smoke"]["concurrency"]
    bm.solver.max_runtime_s_per_game = ARC3_SUBMISSION_CONFIG["save_smoke"]["budget_seconds"]
    bm.solver.save_request_logs = True
    if float(getattr(target, 'max_runtime_s', 0.0) or 0.0) != 32400.0:
        raise RuntimeError(f'Expected the 32400-second notebook target, got {target.max_runtime_s!r}.')

'''
    sources[16] = replace_once(sources[16], old_else, new_else)
    changes[16] = ["Replace only non-formal 25x4 demo settings with two games, one pass, concurrency 2 and 300 seconds"]
    sources[20] = replace_once(sources[20],
        'str(Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels").parent / "environment_files")',
        'str(Path(ARC3_SUBMISSION_INPUTS["competition"]) / "environment_files")')
    sources[20] = replace_once(sources[20], "    bm.games = _offline_games(competition_env_files)",
        '    available = {game.env_name: game for game in _offline_games(competition_env_files)}\n'
        '    expected = ARC3_SUBMISSION_CONFIG["save_smoke"]["game_ids"]\n'
        '    missing = [game_id for game_id in expected if game_id not in available]\n'
        '    if missing:\n'
        '        raise RuntimeError(f"Save smoke environments unavailable: {missing}")\n'
        '    bm.games = [available[game_id] for game_id in expected]')
    cutoff = sources[20].index("# Outside a real submission,")
    sources[20] = sources[20][:cutoff] + '''# Formal retains the original deadline behavior; save starts its 300-second window now.
soft_end = None
if not TRUE_SUBMISSION:
    if not ARC3_SAVE_REPORT["health_200_observed"]:
        raise RuntimeError("Cannot start save benchmark before health 200")
    ARC3_SAVE_REPORT["status"] = "playing"
    ARC3_SAVE_REPORT["benchmark_started_elapsed_seconds"] = time.monotonic() - ARC3_SAVE_STARTED_MONOTONIC
    ARC3_SAVE_REPORT["game_ids"] = ARC3_SUBMISSION_CONFIG["save_smoke"]["game_ids"]
    ARC3_SAVE_REPORT["budget_seconds"] = ARC3_SUBMISSION_CONFIG["save_smoke"]["budget_seconds"]
    arc3_write_save_report()
    soft_end = datetime.now() + timedelta(seconds=ARC3_SUBMISSION_CONFIG["save_smoke"]["budget_seconds"])

# Native top-level await remains directly visible to the notebook runtime.
if TRUE_SUBMISSION:
    await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)
else:
    try:
        await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)
        arc3_validate_save_benchmark()
        # Organizer protocol: selectable save artifact only, never a measured hidden score.
        import pandas as pd
        pd.DataFrame([["1_0", "1", True, 1]],
                     columns=["row_id", "game_id", "end_of_game", "score"]).to_parquet(
            WORKING_DIR / "submission.parquet", index=False)
        ARC3_SAVE_REPORT["placeholder_written"] = True
        ARC3_SAVE_REPORT["status"] = "passed"
        arc3_write_save_report()
    except BaseException as exc:
        ARC3_SAVE_REPORT["status"] = "failed"
        ARC3_SAVE_REPORT["failure"] = type(exc).__name__ + ": " + str(exc)
        arc3_write_save_report()
        raise
    finally:
        arc3_stop_save_server()
        if ARC3_SAVE_TIMER is not None:
            ARC3_SAVE_TIMER.cancel()
'''
    changes[20] = [
        "Preserve live competition gateway helper and branch verbatim",
        "Resolve save environment path and select exact sb26/cd82 IDs; no environment code inspection",
        "Begin 300-second save deadline only after successful model readiness; native await bm.run",
        "Require both games to have real non-RESET actions, generated tokens, and won/cancelled state",
        "Write official placeholder only after smoke validation; report failures and clean up owned save server",
    ]
    sources[19] = (
        "## 9. Run the benchmark\n\n"
        "Formal reruns use the original live COMPETITION gateway. A save runs only sb26/cd82 "
        "OFFLINE after model health 200, preserving full benchmark and request logs. The 300-second "
        "save deadline starts here; the entire save has a 2400-second watchdog. A successful save "
        "is a real inference smoke, not a leaderboard or score-gain result."
    )
    changes[19] = ["Describe actual GPU smoke and formal gateway semantics"]
    notebook = copy.deepcopy(base)
    native = []
    for index, cell in enumerate(notebook["cells"]):
        cell["source"] = sources[index].splitlines(keepends=True)
        cell["metadata"] = {}
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        native.append(cell)
    bootstrap = (
        "# 009 revision 2 configuration and provenance, as ordinary Python dictionaries.\n"
        "ARC3_SUBMISSION_CONFIG = " + pformat(config, width=100, sort_dicts=False) + "\n\n"
        "ARC3_SUBMISSION_SOURCE_HASHES = " + pformat(hashes, width=100, sort_dicts=False) + "\n\n"
        + BOOTSTRAP
    )
    input_cell = helper_source + '''
# Definitions above are normal notebook source, not encoded/executed strings.
ARC3_SUBMISSION_INPUTS = resolve_submission_inputs(
    input_root="/kaggle/input",
    timeout_seconds=ARC3_SUBMISSION_CONFIG["input_resolution_timeout_seconds"],
    report_path=ARC3_SUBMISSION_WORKING / "input-paths.json",
)
'''
    notebook["cells"] = [code_cell(bootstrap), code_cell(input_cell), *native]
    notebook["metadata"].pop("papermill", None)
    notebook["metadata"].setdefault("kaggle", {}).update(
        accelerator="nvidiaRtxPro6000", isGpuEnabled=True, isInternetEnabled=False)
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
        "id": config["id"], "revision": 2, "config": config, "source_hashes": hashes,
        "base_source_sha256": config["base_source_sha256"],
        "notebook_sha256": sha256(notebook_path.read_bytes()),
        "metadata_sha256": sha256((out / "kernel-metadata.json").read_bytes()),
        "cell_count": len(notebook["cells"]), "original_cell_count": 23,
        "original_patch_cell_sha256": sha256(original[2]),
        "generated_patch_cell_sha256": sha256(sources[2]),
        "new_cells": [
            {"index": 0, "changes": ["Readable dictionaries, save status, owned-process cleanup and 2400-second timeout"]},
            {"index": 1, "changes": ["Readable input helper definitions; removed only future import for direct embedding"]},
        ],
        "cells": [{"original_index": i, "generated_index": i+2, "cell_type": base["cells"][i]["cell_type"],
                   "original_source_sha256": sha256(original[i]), "generated_source_sha256": sha256(sources[i]),
                   "changes": changes.get(i, [])} for i in range(23)],
        "ordinary_notebook_source": True, "cell_exec_compile_eval_wrappers": False,
        "submission_command_template": (
            f"kaggle competitions submit arc-prize-2026-arc-agi-3 -k {config['kernel_id']} "
            "-v <actual-successful-gpu-smoke-version> -f submission.parquet -m <message>"),
        "push_timeout_seconds": 32400,
        "state": "built_locally_not_pushed_not_submitted",
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"notebook": str(notebook_path), "revision": 2,
                      "sha256": manifest["notebook_sha256"], "bytes": notebook_path.stat().st_size,
                      "cells": len(notebook["cells"])}, indent=2))


if __name__ == "__main__":
    main()
