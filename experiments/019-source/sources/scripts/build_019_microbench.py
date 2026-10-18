"""Build the bounded 019 CPU preflight or GPU microbench from pinned sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research.ple_session import validate_config


def sha(data):
    return hashlib.sha256(data).hexdigest()


def server_driver(original):
    """Keep the serving implementation, with explicit seed and owned cleanup."""
    precache = "".join(original["cells"][6]["source"])
    launch = "".join(original["cells"][12]["source"])
    anchors = {
        '# ---- validate target and create the read-only draft\'s SGLang view ----':
            '_audit_installed_runtime()\n\n# ---- validate target and create the read-only draft\'s SGLang view ----',
        'precache_model_thread.start()':
            'args += ["--random-seed", str(PARAMETERS["seed"])]\nprecache_model_thread.start()',
        'print(f"pid {proc.pid} -> {LOG}")':
            'print(f"pid {proc.pid} -> {LOG}")\n_write_state("loading")',
    }
    for anchor, replacement in anchors.items():
        if launch.count(anchor) != 1:
            raise ValueError(f"Pinned launcher anchor changed: {anchor}")
        launch = launch.replace(anchor, replacement)
    header = '''# Derived from Daniel Franzen Milestone 2 v3 serving cell (Apache-2.0 harness).
# CPU metadata only until the original pinned launcher starts its owned server.
import hashlib, json, os, signal, sys, time
from pathlib import Path
from arc3_research.session_runner import stop_group
from arc3_research.ple_session import save

PARAMETERS = json.loads(Path(sys.argv[1]).read_text())
MODEL_DIR, DRAFT_MODEL_DIR = PARAMETERS["model"], PARAMETERS["draft"]
WHEELHOUSE_DIR, WORKING_DIR = PARAMETERS["wheelhouse"], Path(PARAMETERS["working_dir"])
SERVED_MODEL_NAME, SERVED_MODEL_PORT = "flashnext", PARAMETERS["port"]
NOTEBOOK_START_TIME = time.time()
SERVER_STARTUP_TIMEOUT = PARAMETERS["startup_limit_seconds"]
proc = None
RUNTIME_AUDIT = {}

def _audit_installed_runtime():
    expected = PARAMETERS["runtime_source_sha256"]
    roots = list(Path(VENV).glob("lib/python*/site-packages"))
    for relative, digest in expected.items():
        paths = [r / relative for r in roots if (r / relative).is_file()]
        if len(paths) != 1:
            raise RuntimeError("Pinned runtime source absent or ambiguous: " + relative)
        observed = hashlib.sha256(paths[0].read_bytes()).hexdigest()
        RUNTIME_AUDIT[relative] = {"expected": digest, "observed": observed, "matches": observed == digest}
        if observed != digest:
            save(WORKING_DIR / "runtime-source-check.json", RUNTIME_AUDIT)
            raise RuntimeError("Installed serving source differs from audited pinned source: " + relative)
    save(WORKING_DIR / "runtime-source-check.json", RUNTIME_AUDIT)

def _write_state(status, **extra):
    metadata_files = ["config.json", "model.safetensors.index.json", "tokenizer.json", "chat_template.jinja"]
    save(WORKING_DIR / "launcher-state.json", {
        "status": status, "epoch": time.time(), "launcher_pid": os.getpid(),
        "server_pid": proc.pid if proc is not None else None,
        "args": globals().get("args"), "runtime_source_check": RUNTIME_AUDIT,
        "target_metadata_sha256": {n: hashlib.sha256(Path(MODEL_DIR, n).read_bytes()).hexdigest()
            for n in metadata_files if Path(MODEL_DIR, n).is_file()},
        "environment": {k: v for k, v in globals().get("env", {}).items()
            if k.startswith("SGLANG_") or k in {"OMP_NUM_THREADS", "MKL_NUM_THREADS", "CUDA_VISIBLE_DEVICES"}},
        **extra})

def _terminate(signum, frame):
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, _terminate)
signal.signal(signal.SIGINT, _terminate)
try:
'''
    tail = '''
    if proc.poll() is not None:
        raise RuntimeError("Model server exited during startup")
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("Model server was not healthy")
    precache_model_thread.join(timeout=max(0, SERVER_STARTUP_TIMEOUT-(time.time()-NOTEBOOK_START_TIME)))
    if precache_model_thread.is_alive():
        raise TimeoutError("Background weight prefetch still active; benchmark cannot start")
    _write_state("ready", background_prefetch_joined=True)
    code = proc.wait()
    if code:
        raise RuntimeError("Model server exited: " + str(code))
finally:
    stopped = True if proc is None else stop_group(proc, grace=10)
    _write_state("stopped", server_stopped=stopped)
'''
    result = header + textwrap.indent(precache + "\n" + launch, "    ") + tail
    compile(result, "launch_server.py", "exec")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["weights_only", "microbench"], default="weights_only")
    parser.add_argument("--suite", type=Path, default=ROOT / "experiments/019-suite.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    import nbformat
    from arc3_research.ple_microbench import validate_suite

    base = ROOT / "research/notebooks/cli-baseline/arc-agi-3-milestone-2-solution.ipynb"
    original = nbformat.read(base, as_version=4)
    validate_suite(json.loads(args.suite.read_text()))
    contract = ROOT / "experiments/019-weight-contract.json"
    config = {"id": "019-fp8-ple", "account": "jiyujia", "mode": args.mode,
        "phase_order": ["bf16_a", "fp8", "bf16_b"], "server_seed": 190018, "port": 8001,
        "hard_limit_seconds": 4800, "startup_limit_seconds": 900,
        "phase_budget_seconds": 360, "weight_audit_limit_seconds": 240,
        "inputs": {
            "bf16": "models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1",
            "fp8": "models/dfranzen/albucino-qwen3.8-flash-next-w4a16-fp8ple/transformers/default/1",
            "draft": "models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1",
            "wheelhouse": "datasets/dfranzen/pennyroyal-v253"},
        "runtime_source_sha256": {},
        "scope": "Frozen requests, not a game or leaderboard score. PLE precision changes model numerics. Second BF16 controls drift; startup includes cache/JIT order effects, not a clean cold-load estimate."}
    upstream = ROOT / "research/notebooks/2026-10-18/fp8-ple/pennyroyal/python"
    for relative in ["sglang/srt/models/qwen4_exp.py", "sglang/kernels/ops/qwen4_ple.py",
                     "sglang/srt/environ.py", "sglang/srt/model_loader/loader.py"]:
        config["runtime_source_sha256"][relative] = sha((upstream / relative).read_bytes())
    validate_config(config)
    root = Path("/kaggle/working/019-code")
    files = {"config.json": json.dumps(config, indent=2) + "\n",
             "weight-contract.json": contract.read_text(), "suite.json": args.suite.read_text(),
             "launch_server.py": server_driver(original)}
    source_paths = [Path(__file__), base, contract, args.suite]
    for name in ["__init__.py", "experiment_config.py", "session_runner.py", "ple_weights.py", "ple_microbench.py", "ple_session.py"]:
        path = ROOT / "src/arc3_research" / name
        files["src/arc3_research/" + name] = path.read_text()
        source_paths.append(path)
    payload_manifest = {"sha256": {key: sha(value.encode()) for key, value in files.items()},
                        "base_notebook_sha256": sha(base.read_bytes()),
                        "original_precache_sha256": sha("".join(original["cells"][6]["source"]).encode()),
                        "original_serving_sha256": sha("".join(original["cells"][12]["source"]).encode()),
                        "changes_to_serving": ["same explicit server seed in all phases", "installed source identity gate", "owned process cleanup and readiness report", "join checkpoint prefetch before requests"]}
    files["payload-manifest.json"] = json.dumps(payload_manifest, indent=2) + "\n"
    note = "CPU attachment/weight preflight only; no server or GPU workload is started." if args.mode == "weights_only" else "GPU serving microbench; BF16 → FP8 PLE → BF16; hard limit 80 minutes, not a target runtime."
    cells = [nbformat.v4.new_markdown_cell(f"""# ARC3 019 — FP8 PLE feasibility

{note}

Research account: **jiyujia**. Private, offline. No competition submission,
game engine, benchmark pickle, or execution of model-generated code.
Preserves the [Franzen Milestone 2 v3](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)
Pennyroyal launcher and independent drafter. Source license attribution remains
Apache-2.0 for the harness; model and third-party licenses remain their own.

## Method and boundaries
CPU checks compare mounted metadata, sampled PLE dequantization and non-PLE bytes.
The GPU mode uses the same frozen requests, seed, context, cache and service settings.
Synthetic exact-answer quality and tool format are smoke checks, not hidden-game quality.
Loading order/page cache/JIT effects are recorded. High GPU utilization alone is no speedup.
Outputs are written under `019-results`; inputs and responses are retained with hashes.
"""), nbformat.v4.new_code_cell(f"""from pathlib import Path
import json, os, subprocess, sys
if os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').lower() in {{'1', 'true'}}:
    raise RuntimeError('Research notebook cannot run as a competition submission')
ROOT_019 = Path({str(root)!r})
if ROOT_019.exists():
    raise FileExistsError('Use a fresh Kaggle session for 019')
ROOT_019.mkdir(parents=True)
(ROOT_019 / 'src/arc3_research').mkdir(parents=True)
""")]
    for name, content in files.items():
        if not content.endswith("\n"):
            content += "\n"
            # Reject rather than silently change source/provenance identity.
            raise ValueError("Source needs final newline: " + name)
        cells.append(nbformat.v4.new_code_cell(f"%%writefile {root / name}\n" + content))
    cells += [nbformat.v4.new_markdown_cell("## Execute the frozen checks\n\nFailure stops this run; no automatic retry or promotion."),
              nbformat.v4.new_code_cell("""environment_019 = os.environ.copy()
environment_019['PYTHONPATH'] = str(ROOT_019 / 'src')
subprocess.run([sys.executable, '-m', 'arc3_research.ple_session',
    '--config', str(ROOT_019 / 'config.json'), '--payload-root', str(ROOT_019),
    '--output', '/kaggle/working/019-results'], env=environment_019, check=True)
"""), nbformat.v4.new_markdown_cell("## Recorded outcome\n\nRead the actual status and evidence; this notebook does not claim an unmeasured benefit."),
              nbformat.v4.new_code_cell("""result_019 = json.loads(Path('/kaggle/working/019-results/session.json').read_text())
print(json.dumps({k: result_019.get(k) for k in ['status','elapsed_seconds','weight_audit_passed','gpu_started']}, indent=2))
for item_019 in result_019.get('phases', []):
    print(item_019['phase'], item_019['status'], item_019.get('startup_seconds'), item_019.get('server_stopped'))
""")]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.validate(notebook)
    suffix = "019-fp8-ple-cpu" if args.mode == "weights_only" else "019-fp8-ple"
    destination = args.output_dir or ROOT / "notebooks" / suffix
    destination.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, destination / "experiment.ipynb")
    base_meta = json.loads((base.parent / "kernel-metadata.json").read_text())
    meta = {k: v for k, v in base_meta.items() if k not in {"id_no", "model_sources", "dataset_sources", "competition_sources"}}
    meta.update(id="jiyujia/arc3-" + suffix, title="ARC3 019 FP8 PLE " + ("CPU Preflight" if args.mode == "weights_only" else "Microbench"),
        code_file="experiment.ipynb", is_private=True, enable_gpu=args.mode == "microbench", enable_tpu=False, enable_internet=False,
        dataset_sources=["dfranzen/pennyroyal-v253"], competition_sources=[], kernel_sources=[],
        model_sources=[config["inputs"][k].removeprefix("models/").replace("/transformers/", "/Transformers/") for k in ["bf16", "fp8", "draft"]])
    if args.mode == "microbench":
        meta.update(machine_shape="NvidiaRtxPro6000", docker_image_pinning_type="original")
    else:
        meta.pop("machine_shape", None)
    (destination / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    manifest = {"config": config, "payload": payload_manifest,
                "source_sha256": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in source_paths},
                "notebook_sha256": sha((destination / "experiment.ipynb").read_bytes()),
                "kernel_metadata_sha256": sha((destination / "kernel-metadata.json").read_bytes())}
    (destination / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"path": str(destination), "cells": len(cells), "sha256": manifest["notebook_sha256"], "mode": args.mode}))


if __name__ == "__main__":
    main()
