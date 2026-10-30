"""Exercise the actual042 readiness block with a fake clock, process and HTTP.

No real sleeping, network, model, GPU, gateway, or game actions occur.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
BLOCK = ROOT / "experiments/042-preparation/readiness-wait.py.txt"


class Clock:
    def __init__(self, elapsed):
        self.now = float(elapsed)
        self.sleeps = []

    def time(self):
        return 1_700_000_000.0 + self.now

    def monotonic(self):
        return 1000.0 + self.now

    def sleep(self, seconds):
        assert 0 < seconds <= 3.0
        self.sleeps.append(seconds)
        self.now += seconds


class Process:
    def __init__(self, *, exit_poll=None, exit_code=17):
        self.polls = 0
        self.exit_poll = exit_poll
        self.exit_code = exit_code

    def poll(self):
        self.polls += 1
        return self.exit_code if self.exit_poll is not None and self.polls >= self.exit_poll else None


class Response:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def run_case(name, *, initial_elapsed=100, ready_at=100, nonready="503",
             exit_poll=None, http_delay=0, delayed_status=200, broken_log=False):
    clock = Clock(initial_elapsed)
    process = Process(exit_poll=exit_poll)
    calls = []
    log_tails = []

    def urlopen(url, timeout):
        assert url == "http://127.0.0.1:8001/health"
        assert 0 < timeout <= 5.0
        # Caller must not request a timeout beyond its remaining startup budget.
        assert timeout <= max(0.0, 5400.0 - clock.now) + 1e-8
        calls.append({"at": clock.now, "timeout": timeout})
        if http_delay:
            # Some real requests return just after a timeout boundary. The block
            # must reject even a200 when the total deadline has elapsed.
            clock.now += http_delay
            return Response(delayed_status)
        if ready_at is not None and clock.now >= ready_at:
            return Response(200)
        if nonready == "exception":
            raise urllib.error.URLError("synthetic connection unavailable")
        return Response(503)

    def show_log_tail():
        log_tails.append(clock.now)
        if broken_log:
            raise OSError("synthetic log unavailable")

    with tempfile.TemporaryDirectory(prefix="arc3-042-ready-") as directory:
        namespace = {
            "time": clock,
            "urllib": SimpleNamespace(request=SimpleNamespace(urlopen=urlopen)),
            "proc": process,
            "show_log_tail": show_log_tail,
            "Path": Path,
            "json": json,
            "WORKING_DIR": Path(directory),
            "SERVED_MODEL_PORT": 8001,
            "NOTEBOOK_START_TIME": 1_700_000_000.0,
            "SERVER_STARTUP_TIMEOUT": 5400,
        }
        error = None
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                exec(compile(BLOCK.read_text() + "\nBENCHMARK_RELEASED = True\n", str(BLOCK), "exec"), namespace)
            except (RuntimeError, TimeoutError) as exc:
                error = type(exc).__name__
        report = json.loads((Path(directory) / "startup-readiness.json").read_text())
    return {
        "name": name,
        "report": report,
        "error": error,
        "benchmark_released": namespace.get("BENCHMARK_RELEASED", False),
        "fake_elapsed": clock.now,
        "probe_count": len(calls),
        "max_probe_timeout": max((call["timeout"] for call in calls), default=0),
        "last_probe_timeout": calls[-1]["timeout"] if calls else None,
        "sleep_count": len(clock.sleeps),
        "last_sleep": clock.sleeps[-1] if clock.sleeps else None,
        "log_tail_count": len(log_tails),
        "process_polls": process.polls,
        "stdout_contains_ready": "READY health200" in buffer.getvalue(),
    }


def main():
    cases = []

    result = run_case("immediate_health200_alive")
    assert result["error"] is None and result["benchmark_released"]
    assert result["report"]["status"] == "ready" and result["process_polls"] == 2
    assert result["report"]["process_alive_after_health"]
    cases.append(result)

    result = run_case("ready_after_old12min_before90min", ready_at=1800)
    assert result["error"] is None and result["benchmark_released"]
    assert 1800 <= result["fake_elapsed"] < 1803 and result["fake_elapsed"] > 720
    cases.append(result)

    result = run_case("connection_errors_then_ready", ready_at=900, nonready="exception")
    assert result["error"] is None and result["benchmark_released"]
    assert result["report"]["last_health_error_type"] == "URLError"
    cases.append(result)

    result = run_case("process_already_exited", exit_poll=1)
    assert result["error"] == "RuntimeError" and not result["benchmark_released"]
    assert result["probe_count"] == 0 and result["log_tail_count"] == 1
    assert result["report"]["returncode"] == 17
    cases.append(result)

    result = run_case("process_exits_after_health200", exit_poll=2)
    assert result["error"] == "RuntimeError" and not result["benchmark_released"]
    assert result["report"]["health_200_observed"]
    assert not result["report"]["process_alive_after_health"]
    cases.append(result)

    for nonready in ("503", "exception"):
        result = run_case("never_ready_" + nonready, ready_at=None, nonready=nonready)
        assert result["error"] == "TimeoutError" and not result["benchmark_released"]
        assert result["fake_elapsed"] == 5400
        assert result["report"]["notebook_elapsed_seconds"] == 5400
        assert result["log_tail_count"] == 1
        cases.append(result)

    result = run_case("near_deadline_bounded_http_and_sleep", initial_elapsed=5399.25, ready_at=None)
    assert result["error"] == "TimeoutError" and not result["benchmark_released"]
    assert result["last_probe_timeout"] == 0.75 and result["last_sleep"] == 0.75
    assert result["fake_elapsed"] == 5400
    cases.append(result)

    result = run_case("budget_already_expired", initial_elapsed=5500)
    assert result["error"] == "TimeoutError" and not result["benchmark_released"]
    assert result["probe_count"] == 0 and result["sleep_count"] == 0
    cases.append(result)

    result = run_case("late_health200_rejected", initial_elapsed=5399.25, http_delay=1)
    assert result["error"] == "TimeoutError" and not result["benchmark_released"]
    assert result["report"]["health_200_observed"] and not result["stdout_contains_ready"]
    cases.append(result)

    result = run_case("failed_log_tail_keeps_startup_error", exit_poll=1, broken_log=True)
    assert result["error"] == "RuntimeError" and not result["benchmark_released"]
    assert result["report"]["failure"] == "model_process_exited"
    cases.append(result)

    report = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "checks_passed": len(cases),
        "patch_path": str(BLOCK.relative_to(ROOT)),
        "patch_sha256": hashlib.sha256(BLOCK.read_bytes()).hexdigest(),
        "network_calls": 0, "real_sleeps": 0, "model_calls": 0,
        "gpu_calls": 0, "game_actions": 0, "gateway_calls": 0,
        "cases": cases,
        "limits": [
            "Exercises actual patch block under deterministic CPU fakes; not a real model readiness or leaderboard test.",
            "A process may still fail after the final poll; this gate verifies readiness only at benchmark release.",
            "A request can overrun its socket timeout; a late200 is rejected, but a real OS call cannot be forcibly preempted by this loop.",
            "Does not establish or change Kaggle external inactivity/total-runtime policies.",
        ],
    }
    output = ROOT / "experiments/042-preparation/readiness-cpu-check.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "checks_passed", "patch_sha256")}, indent=2))


if __name__ == "__main__":
    main()
