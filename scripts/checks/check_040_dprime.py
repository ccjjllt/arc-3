"""CPU checks of D-prime formula parity and real frozen admission gate.

No game actions, HTTP, model, GPU, or score measurement. Pure source oracle
comes from the archived public patch; real runtime gate/session code is used.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "research/runtime-bundle/src/ARC3-Inference"
PUBLIC = ROOT / "research/snapshots/2026-10-25-strategy/notebook-sources/tantan0327__arc3-franzen-dprime/arc3-franzen-dprime.ipynb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/040-preparation/dprime-cpu-check.json")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "checking", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "checks": [], "network_attempts": 0, "model_calls": 0, "game_actions": 0,
              "gpu_calls": 0, "limits": ["CPU parity and scheduling compatibility, not score/throughput evidence.",
                "No hidden game data or real environment actions used.",
                "Optional fresh-pricing=True checked for parity; candidate default False preserves baseline fresh protection."]}

    def check(name, condition, **detail):
        report["checks"].append({"name": name, "passed": bool(condition), **detail})
        if not condition:
            raise AssertionError(name)

    def audit(event, _args):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            report["network_attempts"] += 1
            raise RuntimeError("040 CPU checks prohibit network")
    sys.addaudithook(audit)
    sdk = Path(tempfile.mkdtemp(prefix="arc3-040-check-sdk-"))
    for wheel in (ROOT / "research/data/extracted/arc_agi_3_wheels").glob("*.whl"):
        if wheel.name.startswith(("arcengine-", "arc_agi-", "flask-", "blinker-", "click-",
                                  "python_dotenv-", "itsdangerous-", "werkzeug-", "markupsafe-", "jinja2-")):
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(sdk)
    sys.path[:0] = [str(ROOT / "src"), str(RUNTIME),
                   str(ROOT / "research/runtime-bundle/src/tufa-arc-agi-framework/src"), str(sdk)]
    spec = importlib.util.spec_from_file_location("baseline_setup_040", ROOT / "scripts/checks/check_018_grounding.py")
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    os.environ.update(setup.baseline_environment())
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MPLCONFIGDIR"] = str(sdk / "mpl")
    from inference.agent import tool_agent as ta
    from inference.framework import solver as sv
    from arc3_research import dprime_priority as dp
    original = (ta.priority_value, ta.ProgressPace, ta._PriorityGate.acquire, sv._HarnessGameSession.play)
    original_env = {key: os.environ.get(key) for key in dp.ENVIRONMENT}
    notebook = json.loads(PUBLIC.read_text())
    public_cell = next("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
                       for cell in notebook["cells"] if "class PaceTracker" in "".join(cell["source"]))
    tree = ast.parse(public_cell)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {"norm_levels", "value_dprime", "priority_value"}]
    nodes += [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PaceTracker"]
    params = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "DPRIME" for t in node.targets))
    oracle = {"DPRIME": params, "SCALE": 1000.0}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<public-dprime-pure-oracle>", "exec"), oracle)
    oracle["VALUE"] = oracle["value_dprime"]
    check("exact_public_parameters", dp.DPRIME == params)
    count = 0
    for level, actions, tokens, pace, total, phi in itertools.product(
            [-1, 1, 3, 6, 10], [-2, 0, 25, 115, 300, 1000], [-1, 0, 62000, 225000, 500000],
            [0, 1, 1000, 30000, 100000, 500000], [None, 0, 6, 8, 10, 12], [None, -0.2, 0, 0.5, 1, 1.2]):
        state = ta.PrioritySnapshot(level, actions, tokens, pace, total)
        actual = dp.priority_value(state, tail_fraction=phi)
        expected = oracle["priority_value"](state, tail_fraction=phi)
        assert actual == expected and type(actual) is int and actual >= 1
        count += 1
    check("exact_integer_priority_matches_public_oracle", True, cases=count)
    left, right = dp.PaceTracker(), oracle["PaceTracker"]()
    assert left.cost_multiplier() == right.cost_multiplier() == 0
    for tokens in [0, -5, 15000, 30000]:
        left.record_completion(tokens, 123); right.record_completion(tokens, 123)
        assert left.cost_multiplier() == right.cost_multiplier()
    check("pace_is_public_mean_not_baseline_ratio", left.cost_multiplier() == 11250)
    with (ROOT / "research/runtime-bundle/benchmark_initial.pkl").open("rb") as f:
        bm = pickle.load(f)
    check("benchmark_unpickled_before_install_without_agents", bm.solver.analyzer_factory is None)
    patch = dp.install_dprime_priority()
    check("default_preserves_original_fresh_methods", ta._PriorityGate.acquire is original[2]
          and sv._HarnessGameSession.play is original[3] and not patch.snapshot()["price_fresh"])
    analyzer = bm.solver._make_analyzer(SimpleNamespace(), 0)
    check("actual_unpickled_solver_constructs_new_pace", type(analyzer._progress_pace) is dp.PaceTracker)
    gate = ta._PriorityGate(1)
    gate.configure_clock(100, 1100)
    state = ta.PrioritySnapshot(3, 0, 500000, 1000, 6)
    fade_values = [gate._snapshot_priority(state, now) for now in [600, 900, 1100]]
    check("real_gate_fade_04_matches_public", fade_values == [19879, 11879, 3879], values=fade_values)
    gate = ta._PriorityGate(1)
    started = time.monotonic(); gate.configure_clock(started, started + 1000)
    gate.acquire(2000000)
    order, errors = [], []

    def worker(name, priority, snapshot=None):
        try:
            if snapshot is None:
                gate.acquire(priority)
            else:
                with gate._cond:
                    gate._enqueue_and_wait(priority, snapshot)
            order.append(name)
            gate.release()
        except Exception as exc:
            errors.append(repr(exc))

    def queued(length):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with gate._cond:
                if len(gate._waiting) == length:
                    return
            time.sleep(0.001)
        raise AssertionError("CPU worker did not queue")
    returning = threading.Thread(target=worker, args=("returning", 1, state), daemon=True)
    fresh = threading.Thread(target=worker, args=("fresh", 1999900), daemon=True)
    returning.start(); queued(1); fresh.start(); queued(2)
    with gate._cond:
        check("fresh_not_repriced_in_default_mode", len(gate._snapshots) == 1)
    gate.release()
    returning.join(5); fresh.join(5)
    check("real_gate_refresh_keeps_fresh_absolute_priority", not errors and order == ["fresh", "returning"]
          and not returning.is_alive() and not fresh.is_alive() and gate._free == 1 and not gate._snapshots,
          order=order, errors=errors)
    check("live_snapshot_records_executed_policy", patch.snapshot()["active"]
          and patch.snapshot()["priority_calls"] > 0 and patch.snapshot()["pace_instances"] > 0
          and patch.snapshot()["fresh_priced"] == 0, snapshot=patch.snapshot())
    patch.uninstall()
    check("uninstall_restores_all_targets_and_environment", original == (
        ta.priority_value, ta.ProgressPace, ta._PriorityGate.acquire, sv._HarnessGameSession.play)
        and original_env == {key: os.environ.get(key) for key in dp.ENVIRONMENT})
    patch = dp.install_dprime_priority(price_fresh=True)
    gate = ta._PriorityGate(1)
    gate.configure_clock(time.monotonic(), time.monotonic() + 1000)
    patch.local.total_levels = 6
    gate.acquire(2000000)
    check("optional_public_fresh_path_executed", patch.fresh_priced == 1 and gate._free == 0)
    gate.release()
    with tempfile.TemporaryDirectory(prefix="arc3-040-play-") as temporary:
        run = SimpleNamespace(number_of_levels=8)
        seen = []
        session = SimpleNamespace(
            game=SimpleNamespace(game_run=run), analyzer=SimpleNamespace(total_tokens=0),
            solver=SimpleNamespace(max_runtime_s_per_game=1000, soft_time_remaining_seconds=lambda: None),
            started_at=time.monotonic(), analysis_html_relpath="cpu.html",
            transcript_path=Path(temporary) / "transcript.jsonl", _queue_position=lambda: 0,
            seed_initial_history=lambda: None, write_runtime_state=lambda: None,
            _append_initial_viewer_event=lambda: None, write_viewer_payload=lambda: None,
            _play_inner=lambda: seen.append(patch.local.total_levels))
        getter = sv._priority_gate
        sv._priority_gate = lambda: gate  # Explicit CPU fixture: use a real local gate, no global singleton.
        try:
            sv._HarnessGameSession.play(session)
        finally:
            sv._priority_gate = getter
        check("optional_play_supplies_public_total_levels_and_clears_tls", seen == [8]
              and patch.local.total_levels is None and gate._free == 1)
    patch.uninstall()
    check("final_uninstall_restores_originals", original == (
        ta.priority_value, ta.ProgressPace, ta._PriorityGate.acquire, sv._HarnessGameSession.play))
    report.update(status="passed", candidate_price_fresh=False,
                  helper_sha256=hashlib.sha256((ROOT / "src/arc3_research/dprime_priority.py").read_bytes()).hexdigest(),
                  public_notebook_sha256=hashlib.sha256(PUBLIC.read_bytes()).hexdigest(),
                  runtime_source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [RUNTIME / "inference/agent/tool_agent.py", RUNTIME / "inference/framework/solver.py"]})
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "formula_cases": count, "helper_sha256": report["helper_sha256"], "report": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
