#!/usr/bin/env python3
"""Manual CPU orchestration probes using synthetic child processes and HTTP.

No model, GPU, game engine, or network. Checks the real session runner's
configuration, subprocess arguments, failure stops and cleanup behavior.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research import session_runner as runner
from arc3_research.experiment_config import validate_config, parse_arm_environment


def main() -> None:
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
        def __init__(self, status=200):
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, n):
            return b"Cache flushed."

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
            expected_count = 2 if scenario == "paired_success" else 1 if scenario in {
                "incomplete_baseline", "lingering_baseline", "cpu_cleanup_failure"} else 0
            check(scenario + "_launch_count", len(launches) == expected_count)
            check(scenario + "_outcome", (failed is None) == (scenario == "paired_success"))
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

    sources = ["src/arc3_research/session_runner.py", "src/arc3_research/experiment_config.py",
               "scripts/check_014_session.py", "experiments/014-tail-allocation.json"]
    report = {"status": "passed", "check_count": len(checks), "checks": checks,
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
              "boundary": "Real runner with synthetic CPU child/HTTP/monitor. No GPU/network/game/model; not a performance result."}
    path = ROOT / "experiments/014-session-checks.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(checks), "report": str(path)}))


if __name__ == "__main__":
    main()
