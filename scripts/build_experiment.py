"""Build the private research notebook; run manually before kaggle kernels push."""
from __future__ import annotations

import copy
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research.experiment_config import validate_config


def cell(source: str, kind: str = "code") -> dict:
    result = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path,
                        help="Experiment JSON; notebook destination defaults to notebooks/<id>.")
    parser.add_argument("--output-dir", type=Path,
                        help="Optional destination override for a local build.")
    args = parser.parse_args()
    config_path = args.config.resolve()
    original = ROOT / "research/notebooks/cli-baseline"
    source = original / "arc-agi-3-milestone-2-solution.ipynb"
    notebook = json.loads(source.read_text())
    config = json.loads(config_path.read_text())
    validate_config(config)
    arms = config["arm_order"]
    if not arms or len(set(arms)) != len(arms):
        raise ValueError("arm_order must be nonempty with unique output names.")
    if config.get("reference_arm", arms[0]) not in arms:
        raise ValueError("reference_arm must be one of arm_order.")
    for relative, expected in config.get("frozen_source_sha256", {}).items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen comparison source changed: {relative}")
    # Bundle this experiment's dependencies, not unrelated weight audits or
    # community tooling. Kaggle's source upload is bounded to 1 MB.
    required = {"__init__.py", "experiment_config.py", "input_paths.py",
                "run_arm.py", "goal_evidence.py", "transient_history.py",
                "program_state.py", "session_runner.py"}
    if "retrievable_animation" in arms:
        required.add("retrievable_animation.py")
    if "current_data" in arms:
        required.add("current_data.py")
    if any(a in ("native_values", "native") for a in arms):
        required.add("native_values.py")
    if "observation_grounding" in arms:
        required.add("observation_grounding.py")
    if "grounded_state" in arms:
        required.update({"grounded_state.py", "observation_representation.py"})
    if "checked_execution" in arms or "expect_check" in arms:
        required.update({"checked_action.py", "checked_execution.py"})
    if config.get("community_development"):
        required.add("community.py")
    if "stall_probe" in arms:
        required.update({"stall_probe.py", "bounded_probe.py", "checked_execution.py"})
    if "repair_A" in arms or "repair_B" in arms:
        required.update({"failure_repair.py", "probe_budget.py"})
    if "admission_009" in arms:
        required.add("admission_order.py")
    if "repair_forks" in arms:
        required.update({"program_repair.py", "program_repair_forks.py"})
    if "program_repair" in arms:
        required.add("program_repair.py")
    if "persistent_python" in arms:
        required.add("persistent_python.py")
    if "segmentation_runs" in arms:
        required.add("segmentation_runs.py")
    if "solved_level_memory" in arms:
        required.add("solved_level_memory.py")
    if any(arm in ("controller_repair_A", "controller_repair_B") for arm in arms):
        required.update({"controller_repair.py", "controller_repair_forks.py", "program_repair.py"})
    if any(arm in ("segmentation_forks_A", "segmentation_forks_B") for arm in arms):
        required.update({"segmentation_runs.py", "segmentation_forks.py"})
    if any(arm in ("executable_plan", "executable_plan_A", "executable_plan_B") for arm in arms):
        required.update({"executable_plan.py", "executable_plan_contract.py", "program_repair.py"})
    plan_forks = any(arm in ("executable_plan_A", "executable_plan_B") for arm in arms)
    if plan_forks:
        required.add("executable_plan_forks.py")
    if config.get("inference_timing", False):
        required.add("inference_timing.py")
    for key in ("scheduler_observer", "request_deadline"):
        if config.get(key, False):
            required.add(key + ".py")
    if config.get("preflight_before_serving"):
        required.add("preflight.py")
    payload_paths = [*(ROOT / "src/arc3_research" / name for name in sorted(required)),
                     ROOT / "scripts/summarize_experiment.py"]
    if not all(p.is_file() for p in payload_paths):
        raise RuntimeError("Research modules are not ready")
    payload = {}
    for path in payload_paths:
        destination = ("scripts/" + path.name if path.parent.name == "scripts"
                       else "src/arc3_research/" + path.name)
        payload[destination] = path.read_text()
    if "repair_A" in arms or "repair_B" in arms:
        fork_inputs_path = ROOT / "experiments/026-fork-inputs.json"
        payload["experiments/026-fork-inputs.json"] = fork_inputs_path.read_text()
        fork_conv_path = ROOT / "experiments/026-fork-conv.json.gz.b64"
        payload["experiments/026-fork-conv.json.gz.b64"] = fork_conv_path.read_text()
    if "repair_forks" in arms or any(
            arm in ("segmentation_forks_A", "segmentation_forks_B",
                    "controller_repair_A", "controller_repair_B") for arm in arms):
        fork_package = ROOT / "experiments/028-fork-package.json.gz.b64"
        payload["experiments/028-fork-package.json.gz.b64"] = fork_package.read_text()
    plan_input_sources = {}
    if plan_forks:
        # The original 028 pack contains three large transcripts. Keep the
        # selected ft09 entry byte-equivalent as data without uploading unused
        # games; the su15 researcher-only audit is deliberately not bundled.
        original_pack = ROOT / "experiments/028-fork-package.json.gz.b64"
        original_data = json.loads(gzip.decompress(base64.b64decode(original_pack.read_text())))
        ft09 = original_data["forks"]["ft09-0d8bbf25"]
        subset = {"schema_version": 1, "forks": {"ft09-0d8bbf25": ft09},
                  "source_package_sha256": hashlib.sha256(original_pack.read_bytes()).hexdigest()}
        raw = json.dumps(subset, ensure_ascii=False, separators=(",", ":")).encode()
        payload["experiments/034-fork-inputs/ft09-package.json.gz.b64"] = (
            base64.b64encode(gzip.compress(raw, mtime=0)).decode() + "\n")
        su15_pack = ROOT / "experiments/034-fork-inputs/su15-package.json.gz.b64"
        payload[str(su15_pack.relative_to(ROOT))] = su15_pack.read_text()
        for path in (original_pack, su15_pack):
            plan_input_sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [source, Path(__file__), *payload_paths]}
    hashes[str(config_path.relative_to(ROOT))] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    hashes.update(plan_input_sources)

    title = config.get("kernel_title", "ARC3 " + config["id"].replace("-", " ").title())
    intro = f"""# {title}

Private public-environment research. One GPU model load, {len(arms)} isolated
harness process(es), {len(config['games'])} games per arm, requested
{config['requested_arm_seconds']}-second solver budgets. Total session hard
limit: {config['hard_limit_seconds']} seconds ({config['hard_limit_seconds']/3600:g} hours).
Arm order: {', '.join(arms)}. This notebook does not submit to the competition.

Purpose: {config.get('purpose', 'Public-environment research')}.

Base: [Daniel Franzen Milestone 2 v3](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)
and [Tufa Duck](https://github.com/Tufalabs/duck-harness). Original harness and
serving code are retained with attribution; source repository license is
Apache-2.0. Model and third-party runtime licenses remain their own.

{config.get('comparison_note', 'Scores are public-development observations, not hidden-leaderboard results.')}
"""
    setup = '''import json, os, subprocess, sys, time, threading, signal
from pathlib import Path
ARC3_SESSION_START = time.time()
ARC3_CHILD_PROCESSES = []
ARC3_SESSION_DONE = threading.Event()
ARC3_EXPERIMENT = json.loads(CONFIG_JSON)
ARC3_SOURCE_HASHES = json.loads(HASHES_JSON)
if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").lower() in {"1", "true"}:
    raise RuntimeError("This is a bounded public research notebook, not a submission")
Path("/kaggle/working").mkdir(parents=True, exist_ok=True)

def _research_watchdog():
    if ARC3_SESSION_DONE.wait(max(0, ARC3_EXPERIMENT["hard_limit_seconds"] - 30)):
        return
    Path("/kaggle/working/hard-limit.json").write_text(json.dumps({
        "reason": "Research session hard limit reached",
        "hard_limit_seconds": ARC3_EXPERIMENT["hard_limit_seconds"],
        "elapsed": time.time()-ARC3_SESSION_START}))
    for child in [*ARC3_CHILD_PROCESSES, globals().get("proc")]:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    os._exit(124)
threading.Thread(target=_research_watchdog, daemon=True).start()

for relative, content in json.loads(PAYLOAD_JSON).items():
    path = Path("/kaggle/research") / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
sys.path.insert(0, "/kaggle/research/src")
from arc3_research.session_runner import start_gpu_sampling
ARC3_GPU_MONITOR = start_gpu_sampling(
    Path("/kaggle/working/gpu-utilization.jsonl"),
    interval_seconds=ARC3_EXPERIMENT.get("gpu_sample_interval_seconds", 10),
)
from arc3_research.input_paths import resolve_inputs
ARC3_INPUT_PATHS = resolve_inputs(report_path="/kaggle/working/input-paths.json")
os.environ["ARC3_RESEARCH_ENV_DIR"] = ARC3_INPUT_PATHS["environment_files"]
_community_root = ARC3_EXPERIMENT.get("community_source_root")
if _community_root:
    _community_path = Path(_community_root)
    _nested = _community_path / "environment_files"
    # Kaggle stored this dataset with game folders at the dataset root.
    _env_dir = _nested if _nested.is_dir() else _community_path
    if not _env_dir.is_dir():
        raise FileNotFoundError("Community environment directory not found: " + str(_community_path))
    sys.path.insert(0, str(_community_path))
    os.environ["ARC3_RESEARCH_ENV_DIR"] = str(_env_dir)
    os.environ["ARC3_COMMUNITY_DEVELOPMENT"] = "1"
    _allowed = set(ARC3_EXPERIMENT.get("community_allowlist") or [])
    if set(ARC3_EXPERIMENT["games"]) - _allowed:
        raise RuntimeError("Community games are outside the development allowlist")
if ARC3_EXPERIMENT.get("require_rtx_pro6000"):
    _gpu_probe = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True)
    _gpu_totals = [int(line.strip()) for line in _gpu_probe.stdout.splitlines() if line.strip()]
    print("GPU_MEMORY_TOTAL_MIB", _gpu_totals)
    if _gpu_probe.returncode != 0 or len(_gpu_totals) != 1 or _gpu_totals[0] < 90000:
        raise SystemExit("refusing non-RTX session: " + repr(_gpu_totals))
'''
    parameters = ("CONFIG_JSON = " + repr(json.dumps(config)) + "\n"
                  + "HASHES_JSON = " + repr(json.dumps(hashes)) + "\n")
    if config.get("native_payload_cells", False):
        # Keep helper source readable in the notebook. Use the original
        # IPython writefile semantics, including the final newline, instead
        # of wrapping executable cells in exec/compile or escaped JSON.
        payload_writer = '''for relative, content in json.loads(PAYLOAD_JSON).items():
    path = Path("/kaggle/research") / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
'''
        if setup.count(payload_writer) != 1:
            raise RuntimeError("Native helper-cell setup anchor changed")
        bootstrap, activate = setup.split(payload_writer)
        parents = sorted({str((Path("/kaggle/research") / name).parent)
                          for name in payload})
        mkdirs = "\n".join(f"Path({parent!r}).mkdir(parents=True, exist_ok=True)"
                           for parent in parents) + "\n"
        setup_cells = [cell(parameters + bootstrap + mkdirs)]
        for relative, content in payload.items():
            if not content.endswith("\n"):
                raise ValueError(f"Native helper source must end with LF: {relative}")
            setup_cells.append(cell(f"%%writefile /kaggle/research/{relative}\n" + content))
        setup_cells.append(cell(activate))
    else:
        setup = parameters + "PAYLOAD_JSON = " + repr(json.dumps(payload)) + "\n" + setup
        setup_cells = [cell(setup)]
    # Keep inherited solver/serving behavior; resolve input roots before use.
    # No model weights are bundled in the notebook upload.
    inherited = copy.deepcopy(notebook["cells"][1:13])
    input_literals = {
        "/kaggle/input/datasets/dfranzen/pennyroyal-v253": "wheelhouse",
        "/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy": "bundle",
        "/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1": "model",
        "/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1": "draft",
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels": "competition_wheels",
    }
    for item in inherited:
        if item["cell_type"] == "code":
            item["outputs"] = []
            item["execution_count"] = None
            code = "".join(item["source"])
            # Only the original path declarations/install cell need changes;
            # the large inherited git patch must remain byte-for-byte intact.
            if "ORIG_BUNDLE_DIR   =" in code or "# Install the ARC runtime" in code:
                for literal, key in input_literals.items():
                    for quote in ("'", '"'):
                        code = code.replace(quote + literal + quote,
                                            f'ARC3_INPUT_PATHS[{key!r}]')
                item["source"] = code
            if config.get("skip_blanket_model_precache") and code.startswith("# Paste this entire file into the launcher cell."):
                # SGLang already prefetches its current/next weight shard.
                # Keep that loader path; avoid a second whole-directory read
                # competing with it. This changes startup I/O, not inference.
                anchor = "precache_model_thread.start()"
                if code.count(anchor) != 1:
                    raise ValueError("Blanket model-precache launcher anchor changed")
                item["source"] = code.replace(anchor,
                    'print("Blanket model precache disabled; SGLang shard prefetch retained.")', 1)
    if config.get("preflight_before_serving"):
        preflight = '''# Fail on incompatible CPU hooks before loading GPU model weights.
ARC3_GPU_MONITOR.set_phase("cpu_preflight")
ARC3_PREFLIGHT_CONFIG = Path("/kaggle/working/research-config.json")
ARC3_PREFLIGHT_CONFIG.write_text(json.dumps(ARC3_EXPERIMENT, indent=2) + "\\n")
try:
    subprocess.run([sys.executable, "-m", "arc3_research.preflight",
                    "--bundle-dir", str(BUNDLE_DIR),
                    "--config", str(ARC3_PREFLIGHT_CONFIG),
                    "--report", "/kaggle/working/cpu-preflight.json"],
                   env={**os.environ, "PYTHONPATH": "/kaggle/research/src" + os.pathsep + os.environ.get("PYTHONPATH", "")},
                   check=True, timeout=120)
except BaseException:
    ARC3_SESSION_DONE.set()
    ARC3_GPU_MONITOR.stop()
    raise
ARC3_GPU_MONITOR.set_phase("model_startup")
'''
        serving_indices = [i for i, item in enumerate(inherited)
                           if "".join(item["source"]).startswith("# Paste this entire file into the launcher cell.")]
        if len(serving_indices) != 1:
            raise RuntimeError("Cannot locate the unchanged model launcher for CPU preflight.")
        inherited.insert(serving_indices[0], cell(preflight))
    ending = '''from arc3_research.session_runner import run_session
try:
    report = run_session(globals())
    print(json.dumps(report, indent=2))
    summary_args = [sys.executable, "/kaggle/research/scripts/summarize_experiment.py"]
    summary_args += [f"{arm}=/kaggle/working/{arm}/benchmark.json"
                     for arm in ARC3_EXPERIMENT["arm_order"]]
    if len(ARC3_EXPERIMENT["arm_order"]) > 1:
        summary_args += ["--reference", ARC3_EXPERIMENT.get(
            "reference_arm", ARC3_EXPERIMENT["arm_order"][0])]
    summary_args += ["--source-kind", "local-experiment",
                     "--output-dir", "/kaggle/working/summary"]
    subprocess.run(summary_args, check=True)
    print(Path("/kaggle/working/summary/summary.md").read_text())
finally:
    ARC3_SESSION_DONE.set()
'''
    notebook["cells"] = [cell(intro, "markdown"), *setup_cells, *inherited, cell(ending)]
    notebook["metadata"].pop("papermill", None)
    notebook["metadata"].setdefault("kaggle", {})["isGpuEnabled"] = True
    notebook["metadata"]["kaggle"]["isInternetEnabled"] = False
    notebook["nbformat"] = 4
    notebook["nbformat_minor"] = 4
    destination = args.output_dir.resolve() if args.output_dir else ROOT / "notebooks" / config["id"]
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "experiment.ipynb"
    output.write_text(json.dumps(notebook, indent=1) + "\n")
    meta = json.loads((original / "kernel-metadata.json").read_text())
    meta.pop("id_no", None)
    meta.update(id=config.get("kernel_id", "ccjjllt/arc3-" + config["id"]), title=title,
                code_file="experiment.ipynb", is_private=True, enable_gpu=True,
                enable_internet=False, machine_shape="NvidiaRtxPro6000",
                docker_image_pinning_type="original")
    extra_datasets = config.get("extra_dataset_sources") or []
    if extra_datasets:
        meta["dataset_sources"] = list(dict.fromkeys([*meta.get("dataset_sources", []), *extra_datasets]))
    (destination / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    manifest = {"base_source_sha256": hashes[str(source.relative_to(ROOT))],
                "source_hashes": hashes, "config": config,
                "build_config_path": str(config_path.relative_to(ROOT)),
                "payload_write_mode": "native-writefile" if config.get("native_payload_cells") else "json-source-files",
                "notebook_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    if plan_forks:
        manifest["fork_input_payload_sha256"] = {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in payload.items() if name.startswith("experiments/034-fork-inputs/")}
        manifest["diagnostic_only"] = True
    (destination / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {output}; {len(notebook['cells'])} cells, {output.stat().st_size} bytes")
    print(manifest["notebook_sha256"])


if __name__ == "__main__":
    main()
