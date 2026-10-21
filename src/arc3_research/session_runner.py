"""Run configured isolated CPU harnesses against one loaded GPU server."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

from arc3_research.experiment_config import validate_config


def stop_group(process: subprocess.Popen, grace: float = 10.0) -> bool:
    """Stop an owned start_new_session group, even after its leader exits."""
    if getattr(process, "_stopped_group_verified", False):
        return True

    def signal_group(sig: int) -> bool:
        # Reap our leader before probing. On macOS a zombie leader can make a
        # vanished group report EPERM until poll() reaps it. Retry that race once;
        # a genuine permission error remains an error, never a success claim.
        for attempt in range(2):
            process.poll()
            try:
                os.killpg(process.pid, sig)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                if attempt:
                    raise
        return False

    def group_exists() -> bool:
        return signal_group(0)

    if not signal_group(signal.SIGTERM):
        process._stopped_group_verified = True
        return True
    until = time.monotonic() + max(0.0, grace)
    while group_exists() and time.monotonic() < until:
        process.poll()  # reap our leader without assuming its children exited
        time.sleep(0.05)
    if group_exists():
        signal_group(signal.SIGKILL)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        return False
    until = time.monotonic() + 2.0
    while group_exists() and time.monotonic() < until:
        time.sleep(0.05)
    stopped = not group_exists()
    if stopped:
        # Never send a signal to this old PGID again after an hours-long arm.
        process._stopped_group_verified = True
    return stopped


def gpu_sample(path: Path, phase: str) -> dict:
    started = time.time()
    sample = {"time": started, "phase": phase}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        sample.update(metrics=result.stdout.strip(), returncode=result.returncode)
        if result.returncode:
            sample["error"] = result.stderr.strip()[:500]
    except (OSError, subprocess.TimeoutExpired) as exc:
        sample.update(metrics="", returncode=-1, error=str(exc))
    sample["observed_at_epoch"] = time.time()
    sample["sampling_seconds"] = sample["observed_at_epoch"] - started
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as file:
        file.write(json.dumps(sample) + "\n")
    return sample


class GPUSampler:
    """Append every observation through startup, solving and shutdown."""

    def __init__(self, path: Path, interval_seconds: float = 10.0) -> None:
        self.path = Path(path)
        self.interval_seconds = max(1.0, float(interval_seconds))
        self.phase = "startup"
        self.samples = 0
        self.errors = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample_loop,
                                        name="research-gpu-sampler", daemon=True)
        self._thread.start()

    def sample_now(self) -> None:
        with self._lock:
            sample = gpu_sample(self.path, self.phase)
            self.samples += 1
            self.errors += sample["returncode"] != 0

    def set_phase(self, phase: str) -> None:
        with self._lock:
            self.phase = phase
        self.sample_now()

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            self.sample_now()
            self._stop.wait(max(0.0, self.interval_seconds - (time.monotonic() - started)))

    def stop(self) -> dict:
        self._stop.set()
        self._thread.join(timeout=6)
        self.sample_now()
        return {"path": str(self.path), "interval_seconds": self.interval_seconds,
                "sample_count": self.samples, "error_count": self.errors,
                "stopped": not self._thread.is_alive()}


def start_gpu_sampling(path: Path, interval_seconds: float = 10.0) -> GPUSampler:
    return GPUSampler(path, interval_seconds)


def run_session(namespace: dict) -> dict:
    root = Path(namespace["WORKING_DIR"])
    config = namespace["ARC3_EXPERIMENT"]
    server = namespace["proc"]
    start = namespace["ARC3_SESSION_START"]
    server_url = "http://127.0.0.1:" + str(namespace["SERVED_MODEL_PORT"])
    arms = config["arm_order"]
    monitor = namespace.get("ARC3_GPU_MONITOR")
    if monitor is None:
        monitor = start_gpu_sampling(root / "gpu-utilization.jsonl",
                                     config.get("gpu_sample_interval_seconds", 10))
    report = {"experiment": config, "started_at_epoch": start,
              "arms": [], "source_hashes": namespace["ARC3_SOURCE_HASHES"]}
    report_path = root / "experiment-manifest.json"

    def save():
        report["elapsed_seconds"] = time.time() - start
        report_path.write_text(json.dumps(report, indent=2))

    save()
    try:
        validate_config(config)
        if not arms or len(set(arms)) != len(arms):
            raise ValueError("arm_order must be nonempty with unique output names")
        monitor.set_phase("waiting_for_server")
        # The inherited launcher may return before the model is ready. Do not
        # spend the full research allocation on failed loading/retrying.
        ready = False
        while time.time() < start + config["startup_limit_seconds"]:
            if server.poll() is not None:
                raise RuntimeError("Model server exited during startup; inspect serve.log")
            try:
                with urlopen(server_url + "/health", timeout=5) as response:
                    ready = response.status == 200
                if ready:
                    break
            except Exception:
                pass
            time.sleep(5)
        if not ready:
            raise RuntimeError("Model was not ready within the startup allocation")

        report["model_ready_seconds"] = time.time() - start
        remaining = config["hard_limit_seconds"] - (time.time() - start)
        # Each CPU runner has at most 120s drain + 30s output allowance.
        # Reserve another minute for outer shutdown and the notebook watchdog.
        cleanup_reserve = 150 * len(arms) + 60
        arm_budget = min(config["requested_arm_seconds"],
                         int((remaining - cleanup_reserve) / len(arms)))
        if config.get("strict_arm_budget") and arm_budget != config["requested_arm_seconds"]:
            raise RuntimeError("Startup consumed the frozen solver budget; aborting instead of shortening the comparison.")
        if arm_budget < 600:
            raise RuntimeError("Insufficient budget left for the configured experiment")
        report["equal_arm_budget_seconds"] = arm_budget
        report["cleanup_reserve_seconds"] = cleanup_reserve
        report["arm_count"] = len(arms)
        save()
        for arm in arms:
            out = root / arm
            out.mkdir(parents=True, exist_ok=True)
            entry = {"arm": arm, "budget_seconds": arm_budget,
                     "started_at_epoch": time.time()}
            report["arms"].append(entry)
            monitor.set_phase(arm + "_cache_flush")
            serve_log = root / "serve.log"
            flush_offset = serve_log.stat().st_size if serve_log.is_file() else None
            # Flush prompt caches only, retaining weights and compiled kernels.
            # If unsupported, report the limitation rather than reload the GPU.
            try:
                request = Request(server_url + "/flush_cache", data=b"", method="POST")
                with urlopen(request, timeout=30) as response:
                    entry["cache_flush_http_status"] = response.status
                    entry["cache_flush_body"] = response.read(512).decode(errors="replace")
            except Exception as exc:
                entry["cache_flush_error"] = str(exc)
            save()
            if config.get("require_cache_flush") and entry.get("cache_flush_http_status") != 200:
                raise RuntimeError(f"Cache flush failed before {arm}; refusing unmatched cache state.")
            if config.get("require_cache_flush_log"):
                # This SGLang version returns HTTP200 even when active requests
                # prevent flushing. Require its new backend success log too.
                confirmed = False
                if flush_offset is not None:
                    until = time.monotonic() + 30.0
                    while time.monotonic() < until:
                        with serve_log.open("rb") as stream:
                            stream.seek(flush_offset)
                            recent = stream.read(131072)
                        if b"Cache flushed successfully!" in recent:
                            confirmed = True
                            break
                        if server.poll() is not None:
                            break
                        time.sleep(0.2)
                entry["cache_flush_backend_confirmed"] = confirmed
                save()
                if not confirmed:
                    raise RuntimeError(f"Backend did not confirm cache flush before {arm}; aborting comparison.")

            command = [sys.executable, "-u", "-m", "arc3_research.run_arm",
                       "--arm", arm, "--bundle-dir", str(namespace["BUNDLE_DIR"]),
                       "--working-dir", str(out), "--game-list", ",".join(config["games"]),
                       "--budget-seconds", str(arm_budget),
                       "--warmup-action-games", str(config.get("warmup_action_games", 0))]
            if config.get("inference_timing", False):
                command.append("--inference-timing")
            if config.get("request_deadline", False):
                command.append("--request-deadline")
            if config.get("scheduler_observer", False):
                command.append("--scheduler-observer")
            command.extend(["--environment-json", json.dumps(config.get("arm_environment", {}).get(arm, {}))])
            env = os.environ.copy()
            env["PYTHONPATH"] = "/kaggle/research/src" + os.pathsep + env.get("PYTHONPATH", "")
            print(f"Starting {arm}: {len(config['games'])} games, {arm_budget}s, shared GPU", flush=True)
            monitor.set_phase(arm)
            with (out / "run.log").open("w") as log:
                child = subprocess.Popen(command, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                namespace["ARC3_CHILD_PROCESSES"].append(child)
                try:
                    next_status = 0.0
                    while child.poll() is None:
                        now = time.time()
                        if server.poll() is not None:
                            entry["model_server_exited_during_arm"] = server.returncode
                            stop_group(child)
                            break
                        if now >= next_status:
                            print(f"{arm}: elapsed {now-entry['started_at_epoch']:.0f}s; "
                                  f"session {now-start:.0f}s", flush=True)
                            next_status = now + 60
                        if now - entry["started_at_epoch"] > arm_budget + 150:
                            entry["parent_timeout"] = True
                            stop_group(child)
                            break
                        time.sleep(3)
                finally:
                    monitor.set_phase(arm + "_cleanup")
                    stop_group(child)
                entry["exit_code"] = child.returncode
            entry["elapsed_seconds"] = time.time() - entry["started_at_epoch"]
            entry["benchmark_exists"] = (out / "benchmark.json").exists()
            arm_meta_path = out / "arm-metadata.json"
            if arm_meta_path.exists():
                arm_meta = json.loads(arm_meta_path.read_text())
                entry["game_state_counts"] = arm_meta.get("game_state_counts", {})
                results = arm_meta.get("game_results", [])
                entry["all_games_failed_to_run"] = not results or all(
                    game.get("state") in {"crashed", "not_started"} for game in results
                )
                entry["lingering_worker_threads"] = arm_meta.get("lingering_worker_threads", [])
                entry["environment_overrides"] = arm_meta.get("environment_overrides", {})
                entry["complete_pool"] = (
                    len(results) == len(config["games"])
                    and {game.get("game_id") for game in results} == set(config["games"])
                    # Terminal states are won/cancelled/gave_up; crashes/not_started fail.
                    # gave_up carries valid score/levels (016 baseline: 8 gave_up with
                    # scores, not crashes) and must not waste a full session.
                    and all(game.get("state") in {"won", "cancelled", "gave_up"} for game in results)
                    and not any(game.get("state") in {"crashed", "not_started"} for game in results)
                )
            tail = (out / "run.log").read_text(errors="replace")[-5000:]
            print(tail, flush=True)
            save()
            if entry["exit_code"] != 0:
                # A broken baseline gives no useful paired comparison. Stop
                # the session instead of spending another arm on that failure.
                raise RuntimeError(f"Arm {arm} exited {entry['exit_code']}; see {arm}/run.log")
            if entry.get("all_games_failed_to_run") or not entry["benchmark_exists"]:
                raise RuntimeError(f"Arm {arm} produced no usable game runs; see {arm}/run.log")
            if config.get("require_drained_workers") and entry.get("lingering_worker_threads"):
                raise RuntimeError(f"Arm {arm} has undrained workers; stopping before another arm.")
            if config.get("require_complete_pool") and not entry.get("complete_pool"):
                raise RuntimeError(f"Arm {arm} has incomplete/crashed game coverage; stopping before another arm.")
        report["status"] = "completed"
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        monitor.set_phase("shutdown")
        cleanup_errors = []
        for child in namespace["ARC3_CHILD_PROCESSES"]:
            try:
                if not stop_group(child):
                    cleanup_errors.append(f"CPU process group {child.pid} still exists")
            except Exception as exc:
                cleanup_errors.append(f"CPU group cleanup: {type(exc).__name__}: {exc}")
        try:
            report["gpu_server_process_group_stopped"] = stop_group(server)
        except Exception as exc:
            report["gpu_server_process_group_stopped"] = False
            cleanup_errors.append(f"GPU group cleanup: {type(exc).__name__}: {exc}")
        report["gpu_server_leader_exited"] = server.poll() is not None
        report["gpu_server_stopped"] = report["gpu_server_process_group_stopped"]
        if cleanup_errors or not report["gpu_server_stopped"]:
            report["status"] = "failed"
            report["cleanup_errors"] = cleanup_errors
        monitor.set_phase("finished")
        report["gpu_sampling"] = monitor.stop()
        save()
    if report["status"] != "completed":
        raise RuntimeError("Session cleanup did not confirm all owned process groups stopped.")
    return report
