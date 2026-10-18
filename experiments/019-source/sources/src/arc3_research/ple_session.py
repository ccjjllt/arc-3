"""Bounded, offline BF16 / FP8 PLE / BF16 serving experiment.

This runner never imports a game, unpickles a benchmark or executes model output.
Only an explicit CLI run launches the pinned serving program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import zipfile
from urllib.request import urlopen

from arc3_research.session_runner import start_gpu_sampling, stop_group


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def validate_config(config):
    expected = {"id": "019-fp8-ple", "account": "jiyujia",
                "phase_order": ["bf16_a", "fp8", "bf16_b"],
                "server_seed": 190018, "port": 8001,
                "hard_limit_seconds": 4800, "startup_limit_seconds": 900,
                "phase_budget_seconds": 360, "weight_audit_limit_seconds": 240}
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Frozen 019 setting differs: {key}")
    if config.get("mode") not in {"weights_only", "microbench"}:
        raise ValueError("Unknown 019 execution mode")
    if set(config["inputs"]) != {"bf16", "fp8", "draft", "wheelhouse"}:
        raise ValueError("Expected exactly three model inputs and one wheelhouse")


def resolve_inputs(specs, root="/kaggle/input"):
    root, found = Path(root), {}
    for key, relative in specs.items():
        expected = root / relative
        marker = "requirements.lock" if key == "wheelhouse" else "config.json"
        if expected.is_dir() and (expected / marker).is_file():
            choices = [expected]
        else:
            slug = Path(relative).parts[2]
            choices = [p.parent for p in root.rglob(marker)
                       if slug in p.parts and (key == "wheelhouse" or p.parent.name == "1")]
        if len(choices) != 1:
            raise RuntimeError(f"019 {key}: expected one attached input, got {choices}")
        found[key] = str(choices[0].resolve())
        required = ["wheels", "hot_tokens_64k.pt"] if key == "wheelhouse" else ["model.safetensors.index.json"]
        if any(not (choices[0] / name).exists() for name in required):
            raise FileNotFoundError(f"019 incomplete {key} attachment")
    return found


def normalized_args(args):
    """Only path identity may differ; all effective command switches must match."""
    result = list(args)
    for flag in ("--model-path", "--chat-template", "--speculative-draft-model-path"):
        if flag in result:
            result[result.index(flag) + 1] = "<" + flag[2:] + ">"
    return result


def audit_wheel_sources(wheelhouse, expected):
    wheels = sorted((Path(wheelhouse) / "wheels").glob("sglang-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected one pinned SGLang wheel")
    checks = {}
    with zipfile.ZipFile(wheels[0]) as archive:
        for relative, digest in expected.items():
            observed = hashlib.sha256(archive.read(relative)).hexdigest()
            checks[relative] = {"expected": digest, "observed": observed, "matches": observed == digest}
    return {"wheel": str(wheels[0]), "wheel_bytes": wheels[0].stat().st_size,
            "checks": checks, "passed": all(row["matches"] for row in checks.values())}


def host_sample(groups):
    sample = {"epoch": time.time(), "processes": [], "meminfo_kib": {}}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "Mlocked", "Unevictable", "Cached"}:
                sample["meminfo_kib"][key] = int(value.split()[0])
        for directory in Path("/proc").iterdir():
            if not directory.name.isdigit():
                continue
            try:
                stat = (directory / "stat").read_text().rsplit(")", 1)[1].split()
                if int(stat[2]) not in groups:
                    continue
                fields = {}
                for line in (directory / "status").read_text().splitlines():
                    key, value = line.split(":", 1)
                    if key in {"VmRSS", "VmLck", "VmPin", "VmHWM"}:
                        fields[key + "_kib"] = int(value.split()[0])
                sample["processes"].append({"pid": int(directory.name), "pgid": int(stat[2]), **fields})
            except (OSError, ValueError, IndexError):
                continue
    except OSError as error:
        sample["unavailable"] = str(error)
    sample["note"] = "Per-process RSS may double-count shared pages; VmLck/VmPin do not prove the complete CUDA pinned allocation."
    return sample


def run(config_path, payload_root, output, input_root="/kaggle/input"):
    from arc3_research.ple_microbench import validate_suite, run_phase, compare_phase_reports

    payload_root, output = Path(payload_root), Path(output)
    config = json.loads(Path(config_path).read_text())
    validate_config(config)
    if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").lower() in {"1", "true"}:
        raise RuntimeError("019 is a research microbench, never a competition submission")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use a fresh 019 output directory; never overwrite raw evidence")
    output.mkdir(parents=True, exist_ok=True)
    bundle = json.loads((payload_root / "payload-manifest.json").read_text())
    for relative, expected in bundle["sha256"].items():
        if sha(payload_root / relative) != expected:
            raise ValueError(f"019 payload hash mismatch: {relative}")
    suite = json.loads((payload_root / "suite.json").read_text())
    validate_suite(suite)
    paths = resolve_inputs(config["inputs"], input_root)
    save(output / "input-paths.json", paths)
    started = time.monotonic()
    report = {"config": config, "payload": bundle, "started_at_epoch": time.time(),
              "phases": [], "status": "initializing", "gpu_started": False,
              "competition_submission_created": False}
    done = threading.Event()
    drivers, groups = [], set()
    monitor = None

    def checkpoint():
        report["elapsed_seconds"] = time.monotonic() - started
        save(output / "session.json", report)

    def watchdog():
        if done.wait(config["hard_limit_seconds"] - 30):
            return
        save(output / "hard-limit.json", {"status": "hard_limit", "elapsed_seconds": time.monotonic() - started})
        for process in drivers:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(10)
        # These groups were registered by this session, never discovered by name.
        for pgid in list(groups):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        os._exit(124)

    def host_loop():
        while not done.is_set():
            row = host_sample(set(groups))
            with (output / "host-memory.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            done.wait(10)

    threading.Thread(target=watchdog, daemon=True).start()
    sampler = threading.Thread(target=host_loop, daemon=True)
    sampler.start()
    try:
        checkpoint()
        runtime_audit = audit_wheel_sources(paths["wheelhouse"], config["runtime_source_sha256"])
        save(output / "wheel-source-check.json", runtime_audit)
        if not runtime_audit["passed"]:
            raise RuntimeError("Attached wheel source differs from the audited runtime; no serving")
        # Isolated CPU process imposes a real upper bound on attachment reads.
        command = [sys.executable, "-m", "arc3_research.ple_weights",
                   "--bf16-dir", paths["bf16"], "--fp8-dir", paths["fp8"],
                   "--draft-dir", paths["draft"], "--contract", str(payload_root / "weight-contract.json"),
                   "--output", str(output / "weight-audit.json")]
        with (output / "weight-audit.log").open("w") as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True,
                           timeout=config["weight_audit_limit_seconds"])
        weight_audit = json.loads((output / "weight-audit.json").read_text())
        if weight_audit.get("passed") is not True:
            raise RuntimeError("Mounted weight contract failed; GPU server was not started")
        report["weight_audit_passed"] = True
        if config["mode"] == "weights_only":
            report["status"] = "cpu_preflight_complete"
            return report
        monitor = start_gpu_sampling(output / "gpu-utilization.jsonl", 10)
        common_args = None
        for phase in config["phase_order"]:
            if config["hard_limit_seconds"] - (time.monotonic() - started) < config["startup_limit_seconds"] + config["phase_budget_seconds"] + 60:
                raise RuntimeError("Insufficient remaining session budget for a complete phase; no shortened phase")
            directory = output / phase
            directory.mkdir()
            params = {"model": paths["fp8" if phase == "fp8" else "bf16"],
                      "draft": paths["draft"], "wheelhouse": paths["wheelhouse"],
                      "working_dir": str(directory), "port": config["port"],
                      "seed": config["server_seed"], "startup_limit_seconds": config["startup_limit_seconds"],
                      "runtime_source_sha256": config["runtime_source_sha256"]}
            save(directory / "launch-parameters.json", params)
            monitor.set_phase(phase + ":startup")
            phase_started = time.monotonic()
            entry = {"phase": phase, "started_at_epoch": time.time(), "status": "loading"}
            report["phases"].append(entry)
            checkpoint()
            with (directory / "launcher.log").open("w") as stream:
                driver = subprocess.Popen([sys.executable, str(payload_root / "launch_server.py"),
                                           str(directory / "launch-parameters.json")],
                                          stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            drivers.append(driver)
            groups.add(driver.pid)
            state = {}
            try:
                while time.monotonic() - phase_started < config["startup_limit_seconds"]:
                    state_path = directory / "launcher-state.json"
                    if state_path.exists():
                        state = json.loads(state_path.read_text())
                        if state.get("server_pid"):
                            groups.add(state["server_pid"])
                            report["gpu_started"] = True
                        if state.get("status") == "ready":
                            break
                    if driver.poll() is not None:
                        raise RuntimeError(f"{phase} launcher exited: {driver.returncode}")
                    time.sleep(2)
                else:
                    raise TimeoutError(f"{phase} model startup exceeded frozen limit")
                entry["startup_seconds"] = time.monotonic() - phase_started
                entry["launch_state"] = state
                normalized = normalized_args(state["args"])
                if common_args is not None and normalized != common_args:
                    raise RuntimeError("Serving arguments changed beyond target/template/draft-view paths")
                common_args = normalized
                monitor.set_phase(phase + ":requests")
                entry["status"] = "benchmarking"
                checkpoint()
                phase_report = run_phase(f"http://127.0.0.1:{config['port']}", directory,
                                         suite, time.monotonic() + config["phase_budget_seconds"],
                                         phase=phase, serve_log=directory / "serve.log")
                entry["benchmark_report"] = phase_report
                if phase_report.get("status") != "complete":
                    raise RuntimeError("Frozen request suite incomplete; not starting another model")
                if any(g["id"] != "quality10" and (not g["fixed_lengths_all_match"] or g["cache_condition_observed"] is not True)
                       for g in phase_report["groups"]):
                    raise RuntimeError("Output-length/cache controls not established; not starting another model")
                entry["status"] = "requests_finished"
            finally:
                monitor.set_phase(phase + ":shutdown")
                stopped = stop_group(driver, grace=20)
                groups.discard(driver.pid)
                final_state_path = directory / "launcher-state.json"
                final_state = json.loads(final_state_path.read_text()) if final_state_path.exists() else {}
                server_pid = state.get("server_pid") or final_state.get("server_pid")
                if server_pid:
                    # Driver owns and drains this separate server group.
                    try:
                        os.killpg(server_pid, 0)
                        server_stopped = False
                    except ProcessLookupError:
                        server_stopped = True
                    if not server_stopped:
                        os.killpg(server_pid, signal.SIGKILL)
                        time.sleep(1)
                        raise RuntimeError("Server group did not drain; stopped and refusing next model")
                    groups.discard(server_pid)
                else:
                    server_stopped = final_state.get("server_stopped") is True
                entry["driver_stopped"] = stopped
                entry["server_stopped"] = server_stopped
                entry["elapsed_seconds"] = time.monotonic() - phase_started
                checkpoint()
                if not stopped or not server_stopped:
                    raise RuntimeError("019 owned processes did not stop cleanly")
            entry["status"] = "complete"
            checkpoint()
        report["comparison"] = compare_phase_reports([output / p / "phase-report.json" for p in config["phase_order"]])
        save(output / "comparison.json", report["comparison"])
        report["status"] = "complete"
        return report
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        cleanup_errors = []
        for driver in drivers:
            if driver.poll() is None:
                try:
                    if not stop_group(driver, grace=20):
                        cleanup_errors.append({"driver_pid": driver.pid, "error": "driver_not_stopped"})
                except Exception as error:
                    cleanup_errors.append({"driver_pid": driver.pid, "error": repr(error)})
        # A failed state-file read or cleanup exception must not bypass the
        # separate server PGID. Only IDs registered by this session are used.
        for pgid in list(groups):
            try:
                os.killpg(pgid, signal.SIGTERM)
                until = time.monotonic() + 3
                while time.monotonic() < until:
                    time.sleep(.1)
                    os.killpg(pgid, 0)
                os.killpg(pgid, signal.SIGKILL)
                time.sleep(.5)
                os.killpg(pgid, 0)
                cleanup_errors.append({"pgid": pgid, "error": "group_still_observed_after_kill"})
            except ProcessLookupError:
                groups.discard(pgid)
            except Exception as error:
                cleanup_errors.append({"pgid": pgid, "error": repr(error)})
        report["cleanup_errors"] = cleanup_errors
        if cleanup_errors:
            report["status"] = "failed_cleanup"
        if monitor is not None:
            report["gpu_sampling"] = monitor.stop()
        done.set()
        sampler.join(timeout=2)
        checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--payload-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-root", default="/kaggle/input")
    args = parser.parse_args()
    report = run(args.config, args.payload_root, args.output, args.input_root)
    print(json.dumps(report, indent=2))
    if report["status"] not in {"complete", "cpu_preflight_complete"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
