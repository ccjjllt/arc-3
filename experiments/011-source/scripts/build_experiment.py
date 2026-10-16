"""Build the private research notebook; run manually before kaggle kernels push."""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    arms = config["arm_order"]
    if not arms or len(set(arms)) != len(arms):
        raise ValueError("arm_order must be nonempty with unique output names.")
    if config.get("reference_arm", arms[0]) not in arms:
        raise ValueError("reference_arm must be one of arm_order.")
    for relative, expected in config.get("frozen_source_sha256", {}).items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen comparison source changed: {relative}")
    payload_paths = [*sorted((ROOT / "src/arc3_research").glob("*.py")),
                     ROOT / "scripts/summarize_experiment.py"]
    required = {"run_arm.py", "goal_evidence.py", "session_runner.py"}
    if "retrievable_animation" in arms:
        required.add("retrievable_animation.py")
    if config.get("inference_timing", False):
        required.add("inference_timing.py")
    if not required.issubset(p.name for p in payload_paths):
        raise RuntimeError("Research modules are not ready")
    payload = {}
    for path in payload_paths:
        destination = ("scripts/" + path.name if path.parent.name == "scripts"
                       else "src/arc3_research/" + path.name)
        payload[destination] = path.read_text()
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [source, Path(__file__), *payload_paths]}
    hashes[str(config_path.relative_to(ROOT))] = hashlib.sha256(config_path.read_bytes()).hexdigest()

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
    setup = '''import json, os, sys, time, threading, signal
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
    (destination / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    manifest = {"base_source_sha256": hashes[str(source.relative_to(ROOT))],
                "source_hashes": hashes, "config": config,
                "build_config_path": str(config_path.relative_to(ROOT)),
                "payload_write_mode": "native-writefile" if config.get("native_payload_cells") else "json-source-files",
                "notebook_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (destination / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {output}; {len(notebook['cells'])} cells, {output.stat().st_size} bytes")
    print(manifest["notebook_sha256"])


if __name__ == "__main__":
    main()
