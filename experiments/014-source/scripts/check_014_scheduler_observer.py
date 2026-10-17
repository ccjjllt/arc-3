#!/usr/bin/env python3
"""Manual CPU/thread checks of the real frozen gate; no model or game run."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-path", type=Path, required=True)
    parser.add_argument("--extra-python-path", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/014-scheduler-checks")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(args.sdk_path), str(ROOT / "src"),
                   str(ROOT / "research/runtime-bundle/src/ARC3-Inference")]
    sys.path.extend(str(path) for path in args.extra_python_path)
    os.environ.update({"MPLBACKEND": "Agg", "MPLCONFIGDIR": "/private/tmp/arc3-014-mpl",
                       "LOCAL_ANALYZER_MODEL_ID": "cpu-no-model", "ARC3_PRIORITY_REFRESH_QUEUE": "1",
                       "ARC3_PRIORITY_TAIL_FADE": "0", "ARC3_PRIORITY_TAIL_LOOKUP": "remaining",
                       "ARC3_PRIORITY_SCORE_NORMALIZATION": "1", "ARC3_PRIORITY_PACE": "0"})
    import requests
    import inference.agent.tool_agent as module
    from arc3_research.inference_timing import install_inference_timing
    from arc3_research.scheduler_observer import install_scheduler_observer, _HOOK, _EXPECTED

    def no_http(*a, **kw):
        raise AssertionError("CPU scheduler check prohibits HTTP")
    requests.sessions.Session.request = no_http
    Gate, Agent, Snapshot = module._PriorityGate, module.ToolAgent, module.PrioritySnapshot
    report = {"checks": [], "scenarios": {}, "model_called": False, "game_called": False,
              "gate_source": str(Path(inspect.getsourcefile(Gate)).resolve()),
              "source_sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
                  "src/arc3_research/scheduler_observer.py", "src/arc3_research/inference_timing.py",
                  "scripts/check_014_scheduler_observer.py")}}

    def save():
        (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    def check(name, ok, **fields):
        report["checks"].append({"name": name, "passed": bool(ok), **fields})
        save()
        if not ok:
            raise AssertionError(name)

    class CpuGateSession:
        """Only play's CPU body is synthetic; Gate and timing implementation are real."""
        def __init__(self, name, body):
            self.body = body
            self.game = SimpleNamespace(game_run=SimpleNamespace(game_id=name))
            self.game_index = 0
            self.pass_index = 0
            self.started_at = time.monotonic()

        def play(self):
            return self.body()

    original_methods = {name: getattr(Gate, name) for name in
                        ("acquire", "handover", "release", "_enqueue_and_wait", "_pump")}
    original_codes = {name: method.__code__ for name, method in original_methods.items()}
    timing = install_inference_timing(Agent, CpuGateSession)
    timing_methods = {name: getattr(Gate, name) for name in original_methods}

    def wait_queue(gate, length):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with gate._cond:
                if len(gate._waiting) == length:
                    return
            time.sleep(0.001)
        raise AssertionError(f"Queue never reached {length}")

    def threaded_case(*, snapshots=False, observer=None, priorities=(10, 30, 30)):
        gate = Gate(1)
        gate.acquire(1000)
        order, errors, workers = [], [], []
        states = [Snapshot(1, 100, 80000, 1.0, 8), Snapshot(6, 5, 100, 1.0, 8),
                  Snapshot(6, 5, 100, 1.0, 8)]
        expected_priority = {}
        for i, priority in enumerate(priorities):
            name = f"worker-{i}"
            state = states[i] if snapshots else None
            expected_priority[name] = gate._snapshot_priority(state, time.monotonic()) if snapshots else priority
            def body(name=name, priority=priority, state=state):
                try:
                    if state is None:
                        gate.acquire(priority)
                    else:
                        with gate._cond:
                            gate._enqueue_and_wait(priority, state)
                    order.append(name)
                    gate.release()
                except BaseException as error:
                    errors.append({"name": name, "type": type(error).__name__, "message": str(error)})
            worker = threading.Thread(target=CpuGateSession(name, body).play, daemon=True)
            workers.append(worker)
            worker.start()
            wait_queue(gate, i + 1)
        # Keep the original Condition held after release's actual pump. A selected
        # waiter cannot return from _enqueue_and_wait until this scope exits.
        with gate._cond:
            gate.release()
            order_before_unlock = list(order)
            if observer is not None:
                selection_before_unlock = [event for event in observer.snapshot()["events"]
                                           if event["kind"] == "selection"][-1]
            else:
                selection_before_unlock = None
        for worker in workers:
            worker.join(5)
        return {"order": order, "expected_priority": expected_priority, "errors": errors,
                "threads_finished": all(not w.is_alive() for w in workers),
                "order_before_unlock": order_before_unlock,
                "selection_before_unlock": selection_before_unlock,
                "gate_drained": gate._free == 1 and not gate._waiting and not gate._admitted and not gate._snapshots}

    def handover_case():
        gate = Gate(1)
        gate.acquire(1000)
        order = []
        def other():
            gate.acquire(20)
            order.append("waiter")
            gate.release()
        thread = threading.Thread(target=CpuGateSession("handover-waiter", other).play, daemon=True)
        thread.start()
        wait_queue(gate, 1)
        def current():
            gate.handover(5)
            order.append("holder")
            gate.release()
        CpuGateSession("handover-holder", current).play()
        thread.join(5)
        return {"order": order, "thread_finished": not thread.is_alive(),
                "gate_drained": gate._free == 1 and not gate._waiting and not gate._admitted}

    def failures():
        results = []
        class OriginalError(RuntimeError):
            pass
        sentinel = OriginalError("original int conversion failure")
        class BadPriority:
            def __int__(self):
                raise sentinel
        gate = Gate(1)
        try:
            gate.acquire(BadPriority())
        except BaseException as error:
            results.append({"case": "priority_int", "same_exception": error is sentinel,
                            "type": type(error).__name__, "message": str(error), "free": gate._free,
                            "waiting": list(gate._waiting), "seq": gate._seq})
        gate = Gate(1)
        os.environ["ARC3_PRIORITY_TAIL_FADE"] = "1"
        try:
            with gate._cond:
                gate._enqueue_and_wait(5, Snapshot(1, 0, 0, 1, 8))
        except BaseException as error:
            results.append({"case": "original_reprice", "type": type(error).__name__,
                            "message": str(error), "free": gate._free,
                            "waiting": list(gate._waiting), "seq": gate._seq,
                            "snapshots": list(gate._snapshots)})
        finally:
            os.environ["ARC3_PRIORITY_TAIL_FADE"] = "0"
        return results

    observer = None
    try:
        baseline = threaded_case()
        baseline_reprice = threaded_case(snapshots=True, priorities=(1000, 1, 1))
        baseline_handover = handover_case()
        baseline_failures = failures()
        observer = install_scheduler_observer(Agent, timing_patch=timing, max_gates=32, max_events=4096)
        check("idempotent_same_settings", install_scheduler_observer(Agent, timing_patch=timing,
              max_gates=32, max_events=4096) is observer)
        check("timing_wrapper_identity_unchanged", all(getattr(Gate, k) is v for k, v in timing_methods.items()))
        observed = threaded_case(observer=observer)
        observed_reprice = threaded_case(snapshots=True, observer=observer, priorities=(1000, 1, 1))
        observed_handover = handover_case()
        observed_failures = failures()
        report["scenarios"].update(baseline=baseline, observed=observed,
            baseline_reprice=baseline_reprice, observed_reprice=observed_reprice,
            baseline_handover=baseline_handover, observed_handover=observed_handover,
            baseline_failures=baseline_failures, observed_failures=observed_failures)
        check("priority_and_fifo_admission_preserved", baseline["order"] == observed["order"] ==
              ["worker-1", "worker-2", "worker-0"])
        check("real_snapshot_reprice_preserved", baseline_reprice["order"] == observed_reprice["order"] ==
              ["worker-1", "worker-2", "worker-0"])
        check("handover_atomic_competition_preserved", baseline_handover == observed_handover and
              observed_handover["order"] == ["waiter", "holder"])
        check("original_errors_and_partial_state_preserved", baseline_failures == observed_failures and
              len(observed_failures) == 2 and observed_failures[0]["same_exception"])
        check("all_threads_and_slots_drained", all(x["threads_finished"] and x["gate_drained"] and
              not x["errors"] for x in (baseline, observed, baseline_reprice, observed_reprice)))
        first = observed_reprice["selection_before_unlock"]
        check("selection_precedes_waiter_return", observed_reprice["order_before_unlock"] == [] and
              first["selected"]["session"]["game_id"] == "worker-1" and first["candidate_count"] == 3)
        check("selected_true_priority_and_snapshot", first["selected"]["priority"] ==
              observed_reprice["expected_priority"]["worker-1"] and first["selected"]["snapshot"]["level"] == 6)
        check("waiting_owner_not_release_thread", {row["session"]["game_id"] for row in first["candidates"]} ==
              {"worker-0", "worker-1", "worker-2"})
        data = observer.snapshot()
        check("real_reprice_timestamp_recorded", any(e["kind"] == "reprice" and
              e["scored_at_monotonic"] is not None for e in data["events"]))
        (args.output_dir / "scheduler-snapshot.json").write_text(json.dumps(data, indent=2) + "\n")
        original_record = observer._record
        def broken_record(*a, **kw):
            raise RuntimeError("injected observer failure")
        observer._record = broken_record
        faulted = threaded_case()
        check("record_failure_does_not_change_admission", faulted["order"] == baseline["order"] and
              faulted["gate_drained"] and observer._record_errors > 0)
        observer._record = original_record
        original_hook = module.__dict__[_HOOK]
        def broken_hook(*a, **kw):
            raise BaseException("injected call-site hook failure")
        module.__dict__[_HOOK] = broken_hook
        hook_faulted = handover_case()
        check("call_site_failure_does_not_change_handover", hook_faulted == baseline_handover)
        module.__dict__[_HOOK] = original_hook
        observer.uninstall()
        check("uninstall_restores_original_code_inside_timing", all(method.__code__ is original_codes[k]
              for k, method in original_methods.items()) and all(getattr(Gate, k) is v for k,v in timing_methods.items()))
        observer = install_scheduler_observer(Agent, timing_patch=timing, max_gates=4, max_events=8, max_candidates=2)
        bounded = threaded_case(observer=observer)
        data = observer.snapshot()
        check("bounded_events_candidates_and_explicit_omissions", len(data["events"]) <= 8 and
              data["events_dropped"] > 0 and all(len(e["candidates"]) <= 2 for e in data["events"]) and
              bounded["selection_before_unlock"]["candidates_omitted"] == 1)
        (args.output_dir / "bounded-snapshot.json").write_text(json.dumps(data, indent=2) + "\n")
        observer.uninstall()
        observer = None
        # Deliberate source mismatch must fail before either original function
        # changes. Restore the test replacement regardless of the outcome.
        pump_wrapper = Gate._pump
        def unaudited_pump(self):
            return None
        Gate._pump = unaudited_pump
        mismatch = None
        try:
            install_scheduler_observer(Agent, timing_patch=timing)
        except ValueError as error:
            mismatch = str(error)
        finally:
            Gate._pump = pump_wrapper
        check("source_mismatch_fails_before_mutation", mismatch is not None and _HOOK not in module.__dict__ and
              all(method.__code__ is original_codes[k] for k,method in original_methods.items()))
        saved_hash = _EXPECTED["_pump"]
        _EXPECTED["_pump"] = "0" * 64
        mismatch = None
        try:
            install_scheduler_observer(Agent, timing_patch=timing)
        except ValueError as error:
            mismatch = str(error)
        finally:
            _EXPECTED["_pump"] = saved_hash
        check("second_function_hash_failure_is_atomic", mismatch is not None and "audited _pump source" in mismatch
              and _HOOK not in module.__dict__ and all(method.__code__ is original_codes[k]
              for k,method in original_methods.items()))
        # CPU cost only, not a GPU throughput claim.
        def microbenchmark(count):
            gate = Gate(1)
            started = time.perf_counter()
            for _ in range(count):
                gate.acquire(5)
                gate.release()
            return time.perf_counter() - started
        count = 3000
        plain_seconds = microbenchmark(count)
        observer = install_scheduler_observer(Agent, timing_patch=timing, max_events=32)
        instrumented_seconds = microbenchmark(count)
        report["cpu_cost"] = {"uncontended_acquire_release_pairs": count,
            "timing_only_seconds": plain_seconds, "timing_and_observer_seconds": instrumented_seconds,
            "extra_seconds_per_pair": (instrumented_seconds-plain_seconds)/count,
            "is_gpu_throughput_measurement": False}
        observer.uninstall()
        observer = None
    finally:
        if observer is not None:
            observer.uninstall()
        timing.uninstall()
        check("reverse_uninstall_restores_all_class_methods", all(getattr(Gate,k) is v for k,v in original_methods.items()))
        save()
    report["all_passed"] = all(x["passed"] for x in report["checks"])
    save()
    print(json.dumps({"checks": len(report["checks"]), "all_passed": report["all_passed"],
                      "report": str(args.output_dir/"report.json")}))


if __name__ == "__main__":
    main()
