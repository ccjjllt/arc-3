#!/usr/bin/env python3
"""Manual CPU orchestration probes using synthetic child processes and HTTP.

No model, GPU, game engine, or network. Checks the real session runner's
configuration, subprocess arguments, failure stops and cleanup behavior.
"""
from __future__ import annotations

import copy
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research import session_runner as runner
from arc3_research.experiment_config import validate_config, parse_arm_environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/014-session-checks.json")
    args = parser.parse_args()
    config = json.loads((ROOT / "experiments/014-tail-allocation.json").read_text())
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise AssertionError(name)

    validate_config(config)
    for bad in ({"OPENAI_API_KEY": "no"}, {"ARC3_PRIORITY_PACE": 0},
                {"ARC3_PRIORITY_TAIL_LOOKUP": "guess"}):
        try:
            parse_arm_environment(json.dumps(bad))
        except ValueError:
            check("reject_unapproved_override_" + str(len(checks)), True)
        else:
            check("reject_bad_override", False)

    class Process:
        def __init__(self, code=None):
            self.returncode = code
            self.pid = -1
        def poll(self):
            return self.returncode

    class Monitor:
        def __init__(self):
            self.phases = []
            self.stopped = False
        def set_phase(self, phase):
            self.phases.append(phase)
        def stop(self):
            self.stopped = True
            return {"stopped": True, "synthetic": True}

    class Response:
        def __init__(self, status=200, body=b"Cache flushed."):
            self.status = status
            self.body = body
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, n):
            return self.body[:n]

    # Test the real cache boundary with a virtual clock and synthetic HTTP.
    # No sleeping, model, service API, network or GPU is required.
    cache_scenarios = []
    for scenario in ("busy_then_success", "always_busy", "nonbusy_error",
                     "large_backend_log", "default_single_attempt", "hard_deadline",
                     "stale_backend_confirmation"):
        with tempfile.TemporaryDirectory(prefix="arc3-cache-drain-") as temp:
            log = Path(temp) / "serve.log"
            log.write_text("old Cache flushed successfully!\n")
            clock, calls, entry = [100.0], [], {}
            cfg = {"require_cache_flush": True, "require_cache_flush_log": True}
            if scenario != "default_single_attempt":
                cfg["cache_flush_wait_seconds"] = 3.0

            def sleep(seconds):
                clock[0] += seconds

            def cache_http(request, **kwargs):
                calls.append(kwargs["timeout"])
                if scenario in ("always_busy", "default_single_attempt", "hard_deadline") or (scenario == "busy_then_success" and len(calls) == 1):
                    with log.open("a") as stream:
                        stream.write("Cache not flushed because there are pending requests.\n")
                    raise runner.HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO(b"pending requests"))
                if scenario == "nonbusy_error":
                    raise runner.HTTPError(request.full_url, 503, "Unavailable", {}, io.BytesIO(b"unexpected backend failure"))
                with log.open("ab") as stream:
                    if scenario == "large_backend_log":
                        stream.write(b"x" * 300000)
                    if scenario != "stale_backend_confirmation":
                        stream.write(b"Cache flushed successfully!\n")
                return Response()

            error = None
            deadline = 100.5 if scenario == "hard_deadline" else 110.0
            with patch.object(runner, "urlopen", cache_http), patch.object(runner.time, "monotonic", lambda: clock[0]), \
                 patch.object(runner.time, "sleep", sleep):
                try:
                    runner.flush_cache("http://synthetic", log, Process(), cfg, entry,
                                       deadline=deadline, save=lambda: None)
                except RuntimeError as exc:
                    error = str(exc)
            success = scenario in ("busy_then_success", "large_backend_log")
            check("cache_" + scenario + "_outcome", (error is None) == success)
            expected_calls = {"busy_then_success": 2, "always_busy": 3, "nonbusy_error": 1,
                              "large_backend_log": 1, "default_single_attempt": 1, "hard_deadline": 1,
                              "stale_backend_confirmation": 1}
            check("cache_" + scenario + "_attempts", len(calls) == expected_calls[scenario])
            check("cache_" + scenario + "_bounded", clock[0] <= min(deadline, 103.0))
            if scenario == "busy_then_success":
                check("cache_busy_status_body_saved", entry["cache_flush_attempts"][0]["http_status"] == 400
                      and entry["cache_flush_attempts"][0]["body"] == "pending requests")
                check("cache_independent_offsets", entry["cache_flush_attempts"][1]["log_offset"] > entry["cache_flush_attempts"][0]["log_offset"])
            cache_scenarios.append({"scenario": scenario, "attempts": len(calls), "error": error, "evidence": entry})

    for scenario in ("paired_success", "strict_budget", "flush_http_failure",
                     "missing_backend_confirmation", "incomplete_baseline", "lingering_baseline",
                     "cpu_cleanup_failure"):
        with tempfile.TemporaryDirectory(prefix="arc3-014-session-") as temp:
            root = Path(temp)
            if scenario != "missing_backend_confirmation":
                (root / "serve.log").write_text("synthetic server ready\n")
            server, monitor, launches = Process(), Monitor(), []
            cfg = copy.deepcopy(config)
            namespace = {"WORKING_DIR": root, "ARC3_EXPERIMENT": cfg, "proc": server,
                         "ARC3_SESSION_START": time.time() - (14000 if scenario == "strict_budget" else 0),
                         "SERVED_MODEL_PORT": 8001, "ARC3_GPU_MONITOR": monitor,
                         "ARC3_SOURCE_HASHES": {}, "ARC3_CHILD_PROCESSES": [],
                         "BUNDLE_DIR": root / "synthetic-bundle"}

            def stop(process, *args, **kwargs):
                if scenario == "cpu_cleanup_failure" and process is not server:
                    raise RuntimeError("Synthetic CPU cleanup failure")
                process.returncode = 0 if process.returncode is None else process.returncode
                return True

            def http(request, **kwargs):
                url = request if isinstance(request, str) else request.full_url
                if url.endswith("/flush_cache"):
                    if scenario == "flush_http_failure":
                        return Response(503)
                    if scenario != "missing_backend_confirmation":
                        with (root / "serve.log").open("a") as stream:
                            stream.write("Cache flushed successfully!\n")
                return Response()

            def spawn(command, **kwargs):
                launches.append(command)
                out = Path(command[command.index("--working-dir") + 1])
                arm = command[command.index("--arm") + 1]
                env = json.loads(command[command.index("--environment-json") + 1])
                results = [{"game_id": game, "state": "won"} for game in cfg["games"]]
                if scenario == "incomplete_baseline":
                    results[-1]["state"] = "crashed"
                metadata = {"game_results": results, "environment_overrides": env,
                            "lingering_worker_threads": ["synthetic-live"] if scenario == "lingering_baseline" else [],
                            "game_state_counts": {"won": len(results)}}
                (out / "arm-metadata.json").write_text(json.dumps(metadata))
                (out / "benchmark.json").write_text("{}\n")
                check(scenario + "_" + arm + "_overrides", env == cfg["arm_environment"][arm])
                check(scenario + "_" + arm + "_budget", command[command.index("--budget-seconds") + 1] == "7254")
                check(scenario + "_" + arm + "_same_hooks",
                      all(flag in command for flag in ("--inference-timing", "--scheduler-observer", "--request-deadline")))
                return Process(0)

            failed = None
            with patch.object(runner, "urlopen", http), patch.object(runner, "stop_group", stop), \
                 patch.object(runner.subprocess, "Popen", spawn):
                try:
                    result = runner.run_session(namespace)
                except RuntimeError as exc:
                    failed = str(exc)
            # Existing runner policy: a lingering-thread snapshot is diagnostic
            # once its disposable CPU process group has verifiably stopped.
            expected_success = scenario in {"paired_success", "lingering_baseline"}
            expected_count = 2 if expected_success else 1 if scenario in {
                "incomplete_baseline", "cpu_cleanup_failure"} else 0
            check(scenario + "_launch_count", len(launches) == expected_count)
            check(scenario + "_outcome", (failed is None) == expected_success)
            check(scenario + "_server_and_monitor_stop", server.returncode is not None and monitor.stopped)
            saved = json.loads((root / "experiment-manifest.json").read_text())
            check(scenario + "_saved_status", saved["status"] == ("completed" if failed is None else "failed"))
            if scenario == "paired_success":
                check("one_shared_server_two_cpu_arms", len(namespace["ARC3_CHILD_PROCESSES"]) == 2
                      and all("arc3_research.run_arm" in command for command in launches))
                check("two_backend_confirmations", all(a["cache_flush_backend_confirmed"] for a in result["arms"]))
            if scenario == "cpu_cleanup_failure":
                check("cpu_cleanup_failure_still_stops_gpu_and_saves", bool(saved["cleanup_errors"])
                      and saved["gpu_server_process_group_stopped"] is True)

    # Spend actual virtual time in HTTP and each CPU allowance. The old adaptive
    # allocation left zero seconds for the first flush in these exact-fit caps.
    budget_scenarios = []
    for scenario in ("adaptive_flush_budget", "adaptive_opt_in_budget", "strict_flush_budget"):
        with tempfile.TemporaryDirectory(prefix="arc3-boundary-budget-") as temp:
            root = Path(temp)
            (root / "serve.log").write_text("synthetic server ready\n")
            cfg = copy.deepcopy(config)
            cfg.update(arm_order=["baseline", "control"], arm_environment={},
                       hard_limit_seconds=2000, requested_arm_seconds=820,
                       strict_arm_budget=scenario == "strict_flush_budget")
            if scenario == "adaptive_opt_in_budget":
                cfg["cache_flush_wait_seconds"] = 120
            clock, launches, boundaries = [1000.0], [], []
            server, monitor = Process(), Monitor()
            namespace = {"WORKING_DIR": root, "ARC3_EXPERIMENT": cfg, "proc": server,
                         "ARC3_SESSION_START": clock[0], "SERVED_MODEL_PORT": 8001,
                         "ARC3_GPU_MONITOR": monitor, "ARC3_SOURCE_HASHES": {},
                         "ARC3_CHILD_PROCESSES": [], "BUNDLE_DIR": root / "bundle"}
            real_flush = runner.flush_cache

            def flush(*args, deadline, **kwargs):
                boundaries.append({"started": clock[0], "deadline": deadline})
                return real_flush(*args, deadline=deadline, **kwargs)

            def budget_http(request, **kwargs):
                url = request if isinstance(request, str) else request.full_url
                if url.endswith("/flush_cache"):
                    check(scenario + "_http_has_full_timeout_" + str(len(boundaries)), kwargs["timeout"] == 30)
                    clock[0] += 10
                    with (root / "serve.log").open("a") as stream:
                        stream.write("Cache flushed successfully!\n")
                return Response()

            def budget_spawn(command, **kwargs):
                budget = int(command[command.index("--budget-seconds") + 1])
                launches.append(budget)
                out = Path(command[command.index("--working-dir") + 1])
                (out / "benchmark.json").write_text("{}\n")
                (out / "arm-metadata.json").write_text(json.dumps({
                    "game_results": [{"game_id": game, "state": "won"} for game in cfg["games"]],
                    "game_state_counts": {"won": len(cfg["games"])},
                }))
                clock[0] += budget + 150
                return Process(0)

            error = None
            with patch.object(runner, "urlopen", budget_http), patch.object(runner, "stop_group", stop), \
                 patch.object(runner, "flush_cache", flush), patch.object(runner.subprocess, "Popen", budget_spawn), \
                 patch.object(runner.time, "time", lambda: clock[0]), \
                 patch.object(runner.time, "monotonic", lambda: clock[0]):
                try:
                    result = runner.run_session(namespace)
                except RuntimeError as exc:
                    error = str(exc)
            saved = json.loads((root / "experiment-manifest.json").read_text())
            if scenario == "strict_flush_budget":
                check("strict_boundary_rejected_before_flush_or_cpu", error is not None and not boundaries and not launches)
                check("strict_boundary_saved_failure", saved["status"] == "failed")
            else:
                allowance = 120 if scenario == "adaptive_opt_in_budget" else 60
                expected_budget = (2000 - 360 - 2 * allowance) // 2
                check(scenario + "_completed", error is None and saved["status"] == "completed")
                check(scenario + "_full_equal_cpu_allowances", launches == [expected_budget] * 2)
                check(scenario + "_reserves_later_boundary", boundaries[0]["deadline"] - boundaries[0]["started"] == allowance)
                check(scenario + "_cpu_starts_after_flush", all(
                    arm["started_at_epoch"] == boundary["started"] + 10
                    for arm, boundary in zip(result["arms"], boundaries)))
                check(scenario + "_hard_cap_and_cleanup", clock[0] + 60 <= 3000)
            check(scenario + "_cleanup", server.returncode is not None and monitor.stopped)
            budget_scenarios.append({"scenario": scenario, "error": error,
                                     "cpu_budgets": launches, "boundaries": boundaries,
                                     "elapsed_seconds": clock[0] - 1000})

    sources = ["src/arc3_research/session_runner.py", "src/arc3_research/experiment_config.py",
               "scripts/checks/check_014_session.py", "experiments/014-tail-allocation.json"]
    report = {"status": "passed", "check_count": len(checks), "checks": checks,
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
              "boundary": "Real runner with synthetic CPU child/HTTP/monitor. No GPU/network/game/model; not a performance result."}
    report["cache_scenarios"] = cache_scenarios
    report["budget_scenarios"] = budget_scenarios
    path = args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(checks), "report": str(path)}))


if __name__ == "__main__":
    main()
