"""Run two isolated CPU harnesses against one already-loaded GPU server."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import Request, urlopen


def stop_group(process: subprocess.Popen, grace: float = 10.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
    except ProcessLookupError:
        pass


def gpu_sample(path: Path, phase: str) -> None:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=15,
    )
    with path.open("a") as file:
        file.write(json.dumps({"time": time.time(), "phase": phase,
                               "metrics": result.stdout.strip(),
                               "returncode": result.returncode}) + "\n")


def run_session(namespace: dict) -> dict:
    root = Path(namespace["WORKING_DIR"])
    config = namespace["ARC3_EXPERIMENT"]
    server = namespace["proc"]
    start = namespace["ARC3_SESSION_START"]
    server_url = "http://127.0.0.1:" + str(namespace["SERVED_MODEL_PORT"])
    report = {"experiment": config, "started_at_epoch": start,
              "arms": [], "source_hashes": namespace["ARC3_SOURCE_HASHES"]}
    report_path = root / "experiment-manifest.json"

    def save():
        report["elapsed_seconds"] = time.time() - start
        report_path.write_text(json.dumps(report, indent=2))

    save()
    try:
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
        arm_budget = min(config["requested_arm_seconds"], int((remaining - 360) / 2))
        if arm_budget < 600:
            raise RuntimeError("Insufficient budget left for the paired experiment")
        report["equal_arm_budget_seconds"] = arm_budget
        save()
        for arm in config["arm_order"]:
            out = root / arm
            out.mkdir(parents=True, exist_ok=True)
            entry = {"arm": arm, "budget_seconds": arm_budget,
                     "started_at_epoch": time.time()}
            report["arms"].append(entry)
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

            command = [sys.executable, "-u", "-m", "arc3_research.run_arm",
                       "--arm", arm, "--bundle-dir", str(namespace["BUNDLE_DIR"]),
                       "--working-dir", str(out), "--game-list", ",".join(config["games"]),
                       "--budget-seconds", str(arm_budget)]
            env = os.environ.copy()
            env["PYTHONPATH"] = "/kaggle/research/src" + os.pathsep + env.get("PYTHONPATH", "")
            print(f"Starting {arm}: {len(config['games'])} games, {arm_budget}s, shared GPU", flush=True)
            with (out / "run.log").open("w") as log:
                child = subprocess.Popen(command, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                namespace["ARC3_CHILD_PROCESSES"].append(child)
                try:
                    next_sample = 0.0
                    while child.poll() is None:
                        now = time.time()
                        if now >= next_sample:
                            gpu_sample(root / "gpu-utilization.jsonl", arm)
                            print(f"{arm}: elapsed {now-entry['started_at_epoch']:.0f}s; "
                                  f"session {now-start:.0f}s", flush=True)
                            next_sample = now + 60
                        if now - entry["started_at_epoch"] > arm_budget + 150:
                            entry["parent_timeout"] = True
                            stop_group(child)
                            break
                        time.sleep(3)
                finally:
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
            tail = (out / "run.log").read_text(errors="replace")[-5000:]
            print(tail, flush=True)
            save()
            if entry["exit_code"] != 0:
                # A broken baseline gives no useful paired comparison. Stop
                # the session instead of spending another arm on that failure.
                raise RuntimeError(f"Arm {arm} exited {entry['exit_code']}; see {arm}/run.log")
            if entry.get("all_games_failed_to_run") or not entry["benchmark_exists"]:
                raise RuntimeError(f"Arm {arm} produced no usable game runs; see {arm}/run.log")
        report["status"] = "completed"
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        for child in namespace["ARC3_CHILD_PROCESSES"]:
            stop_group(child)
        stop_group(server)
        report["gpu_server_stopped"] = server.poll() is not None
        save()
    return report
