"""Build the private research notebook; run manually before kaggle kernels push."""
from __future__ import annotations

import copy
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
    original = ROOT / "research/notebooks/cli-baseline"
    source = original / "arc-agi-3-milestone-2-solution.ipynb"
    notebook = json.loads(source.read_text())
    config = json.loads((ROOT / "experiments/003-goal-evidence.json").read_text())
    payload_paths = [*sorted((ROOT / "src/arc3_research").glob("*.py")),
                     ROOT / "scripts/summarize_experiment.py"]
    required = {"run_arm.py", "goal_evidence.py", "session_runner.py"}
    if not required.issubset(p.name for p in payload_paths):
        raise RuntimeError("Research modules are not ready")
    payload = {}
    for path in payload_paths:
        destination = ("scripts/" + path.name if path.parent.name == "scripts"
                       else "src/arc3_research/" + path.name)
        payload[destination] = path.read_text()
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [source, *payload_paths]}

    intro = """# ARC3 003 Goal Evidence AB

Private public-environment research. One GPU model load, two isolated harness
processes, 16 games per arm, equal 4642-second solver budgets. Total session
hard limit: 3 hours. This notebook does not submit to the competition.

Base: [Daniel Franzen Milestone 2 v3](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)
and [Tufa Duck](https://github.com/Tufalabs/duck-harness). Original harness and
serving code are retained with attribution; source repository license is
Apache-2.0. Model and third-party runtime licenses remain their own.

Treatment changes only goal-evidence feedback. Prompt-cache flushing cannot
remove order effects from warmed GPU kernels. Scores are public-development
screening observations, not hidden-leaderboard or statistically confirmed gains.
"""
    setup = '''import json, os, sys, time, threading, signal
from pathlib import Path
ARC3_SESSION_START = time.time()
ARC3_CHILD_PROCESSES = []
ARC3_EXPERIMENT = json.loads(CONFIG_JSON)
ARC3_SOURCE_HASHES = json.loads(HASHES_JSON)
if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").lower() in {"1", "true"}:
    raise RuntimeError("This is a bounded public research notebook, not a submission")
Path("/kaggle/working").mkdir(parents=True, exist_ok=True)

def _research_watchdog():
    time.sleep(ARC3_EXPERIMENT["hard_limit_seconds"] - 30)
    Path("/kaggle/working/hard-limit.json").write_text(json.dumps({
        "reason": "3h research allocation reached", "elapsed": time.time()-ARC3_SESSION_START}))
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
'''
    setup = ("CONFIG_JSON = " + repr(json.dumps(config)) + "\n"
             + "HASHES_JSON = " + repr(json.dumps(hashes)) + "\n"
             + "PAYLOAD_JSON = " + repr(json.dumps(payload)) + "\n" + setup)
    # Keep the exact inherited patch/install/server cells, replacing only the
    # benchmark execution. No model weights are bundled in the notebook upload.
    inherited = copy.deepcopy(notebook["cells"][1:13])
    for item in inherited:
        if item["cell_type"] == "code":
            item["outputs"] = []
            item["execution_count"] = None
    ending = '''from arc3_research.session_runner import run_session
report = run_session(globals())
print(json.dumps(report, indent=2))
subprocess.run([
    sys.executable, "/kaggle/research/scripts/summarize_experiment.py",
    "baseline=/kaggle/working/baseline/benchmark.json",
    "goal_evidence=/kaggle/working/goal_evidence/benchmark.json",
    "--reference", "baseline", "--source-kind", "local-experiment",
    "--output-dir", "/kaggle/working/summary",
], check=True)
print(Path("/kaggle/working/summary/summary.md").read_text())
'''
    notebook["cells"] = [cell(intro, "markdown"), cell(setup), *inherited, cell(ending)]
    notebook["metadata"].pop("papermill", None)
    notebook["metadata"].setdefault("kaggle", {})["isGpuEnabled"] = True
    notebook["metadata"]["kaggle"]["isInternetEnabled"] = False
    notebook["nbformat"] = 4
    notebook["nbformat_minor"] = 4
    destination = ROOT / "notebooks/003-goal-evidence-ab"
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "experiment.ipynb"
    output.write_text(json.dumps(notebook, indent=1) + "\n")
    meta = json.loads((original / "kernel-metadata.json").read_text())
    meta.pop("id_no", None)
    meta.update(id="ccjjllt/arc3-003-goal-evidence-ab", title="ARC3 003 Goal Evidence AB",
                code_file="experiment.ipynb", is_private=True, enable_gpu=True,
                enable_internet=False, machine_shape="NvidiaRtxPro6000",
                docker_image_pinning_type="original")
    (destination / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    manifest = {"base_source_sha256": hashes[str(source.relative_to(ROOT))],
                "source_hashes": hashes, "config": config,
                "notebook_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (destination / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {output}; {len(notebook['cells'])} cells, {output.stat().st_size} bytes")
    print(manifest["notebook_sha256"])


if __name__ == "__main__":
    main()
