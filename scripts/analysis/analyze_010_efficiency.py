"""Recompute 010 runtime/resource evidence from saved outputs only."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/010-retrievable-animation"
ARCHIVE = ROOT / "experiments/010-source"
ARMS = ("baseline", "retrievable_animation")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def epoch(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def beijing(value):
    return datetime.fromtimestamp(value, ZoneInfo("Asia/Shanghai")).isoformat()


def stats(values):
    return ({"n": len(values), "mean": statistics.mean(values),
             "median": statistics.median(values), "min": min(values), "max": max(values)}
            if values else {"n": 0})


def gpu_window(samples, start, end):
    observed = [s for s in samples if start <= s["time"] <= end]
    area = [0.0, 0.0, 0.0]
    covered = 0.0
    for a, b in zip(samples, samples[1:]):
        left, right = max(start, a["time"]), min(end, b["time"])
        if right <= left or b["time"] <= a["time"]:
            continue
        span = b["time"] - a["time"]
        for i, field in enumerate(("util", "memory_mib", "power_watts")):
            vl = a[field] + (b[field] - a[field]) * (left - a["time"]) / span
            vr = a[field] + (b[field] - a[field]) * (right - a["time"]) / span
            area[i] += (vl + vr) * (right-left) / 2
        covered += right-left
    low_runs, pending = [], []
    def flush():
        if len(pending) >= 3 and pending[-1]["time"] - pending[0]["time"] >= 19.5:
            low_runs.append({"start_beijing": beijing(pending[0]["time"]),
                             "end_beijing": beijing(pending[-1]["time"]),
                             "samples": len(pending),
                             "observed_span_seconds": pending[-1]["time"] - pending[0]["time"],
                             "utilization": [s["util"] for s in pending]})
        pending.clear()
    for s in observed:
        if s["util"] >= 50 or (pending and s["time"] - pending[-1]["time"] > 16):
            flush()
        if s["util"] < 50:
            pending.append(s)
    flush()
    return {"start_beijing": beijing(start), "end_beijing": beijing(end),
            "wall_seconds": end-start, "sample_count": len(observed),
            "utilization_samples": stats([s["util"] for s in observed]),
            "covered_seconds": covered,
            "time_weighted_util_percent": area[0]/covered if covered else None,
            "time_weighted_memory_mib": area[1]/covered if covered else None,
            "time_weighted_power_watts": area[2]/covered if covered else None,
            "peak_sampled_memory_mib": max((s["memory_mib"] for s in observed), default=None),
            "sustained_low_util_candidates": low_runs}


def main():
    manifest = read(RUN / "experiment-manifest.json")
    config = manifest["experiment"]
    build = read(ARCHIVE / "build-manifest.json")
    archive_index = read(ARCHIVE / "source-hashes.json")
    inputs = read(RUN / "input-paths.json")
    source_paths = [Path(__file__), RUN / "experiment-manifest.json", RUN / "gpu-utilization.jsonl",
                    RUN / "serve.log", RUN / "input-paths.json", RUN / "arc3-010-retrievable-animation.log",
                    ARCHIVE / "build-manifest.json", ARCHIVE / "source-hashes.json"]
    raw_samples = [json.loads(line) for line in (RUN / "gpu-utilization.jsonl").read_text().splitlines()]
    samples = []
    for s in raw_samples:
        try:
            util, memory, total, power = map(float, s["metrics"].split(","))
            if s["returncode"] != 0:
                continue
            samples.append({**s, "util": util, "memory_mib": memory,
                            "memory_total_mib": total, "power_watts": power})
        except (KeyError, ValueError):
            continue
    samples.sort(key=lambda x: x["time"])
    requests, batches, flushes, non200, startup_parts, warnings = [], [], [], [], [], []
    seen = set()
    # Progress bars contain carriage returns. Preserve physical newline-based
    # line numbers for inspectable source references.
    serve_lines = (RUN / "serve.log").read_bytes().decode().split("\n")
    for lineno, line in enumerate(serve_lines, 1):
        stamp = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\]", line)
        timestamp = epoch(stamp.group(1)) if stamp else None
        if "ReqTimeStats(" in line:
            rid = re.search(r"rid=([^,]+)", line).group(1)
            fields = dict(re.findall(r"(input_len|cached_input_len|output_len|entry_time|queue_duration|initial_prefill_elapsed)=([\d.]+)", line))
            key = (rid, fields.get("entry_time"))
            if key not in seen:
                seen.add(key)
                requests.append({"line": lineno, "rid": rid, "completed_log_epoch": timestamp,
                                 **{k: float(v) for k, v in fields.items()}})
        if "Decode batch," in line or "Prefill batch," in line:
            fields = dict(re.findall(r"(#running-req|accept len|gen throughput \(token/s\)): ([\d.]+)", line))
            batches.append({"line": lineno, "epoch": timestamp, "decode": "Decode batch," in line,
                            **{k: float(v) for k, v in fields.items()}})
        if "Cache flushed successfully!" in line:
            flushes.append({"line": lineno, "epoch": timestamp, "beijing": beijing(timestamp)})
        if 'HTTP/1.1"' in line and 'HTTP/1.1" 200' not in line:
            non200.append({"line": lineno, "text": line})
        if ("Load weight end." in line or "CUDA graph end." in line) and "elapsed=" in line:
            startup_parts.append({"line": lineno, "text": line,
                                  "elapsed_seconds": float(re.search(r"elapsed=([\d.]+)", line).group(1))})
        if re.search(r"ModuleNotFoundError|Warning: Data race|RuntimeWarning|SIGTERM received|crashed|SIGQUIT received|CUDA out of memory|OutOfMemoryError|Traceback \(most recent", line):
            warnings.append({"line": lineno, "text": line[:1000]})
    kernel_rows = read(RUN / "arc3-010-retrievable-animation.log")
    gpu_identification = [r["data"].strip() for r in kernel_rows
                          if r.get("data", "").startswith("GPU: NVIDIA")]
    start = manifest["started_at_epoch"]
    finish = start + manifest["elapsed_seconds"]
    source_matches = {name: (ARCHIVE / name).is_file() and digest(ARCHIVE / name) == expected
                      for name, expected in manifest["source_hashes"].items()}
    archive_matches = {name: digest(ARCHIVE / name) == expected
                       for name, expected in archive_index["files"].items()}
    result = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Completed 010 public 12-game paired run; offline log analysis only.",
        "runtime": {"started_beijing": beijing(start), "finished_beijing": beijing(finish),
                    "elapsed_seconds": manifest["elapsed_seconds"], "wall_hours": manifest["elapsed_seconds"]/3600,
                    "model_ready_seconds": manifest["model_ready_seconds"],
                    "startup_fraction": manifest["model_ready_seconds"]/manifest["elapsed_seconds"],
                    "planned_solve_seconds": 2*config["requested_arm_seconds"],
                    "remaining_preparation_drain_shutdown_seconds": manifest["elapsed_seconds"]-manifest["model_ready_seconds"]-2*config["requested_arm_seconds"],
                    "status": manifest["status"], "gpu_server_stopped": manifest["gpu_server_stopped"],
                    "gpu_identification": gpu_identification, "startup_parts": startup_parts,
                    "input_resolution": inputs},
        "validity": {"runtime_source_hashes_match_frozen_archive": source_matches,
                     "archive_index_matches_files": archive_matches,
                     "manifest_source_map_matches_build_manifest": manifest["source_hashes"] == build["source_hashes"],
                     "manifest_config_matches_build_config": config == build["config"],
                     "frozen_notebook_sha256": archive_index["notebook_sha256"],
                     "cache_flush_success_log_records": flushes},
        "gpu": {"raw_samples": len(raw_samples), "valid_samples": len(samples),
                "invalid_samples": len(raw_samples)-len(samples),
                "phases": dict(Counter(s["phase"] for s in raw_samples)),
                "sampling_seconds": stats([s["sampling_seconds"] for s in samples]),
                "whole_session": gpu_window(samples, start, finish),
                "startup": gpu_window(samples, start, start+manifest["model_ready_seconds"])},
        "server": {"http_non200": non200, "warnings_and_shutdown": warnings,
                   "fatal_oom_or_traceback": [w for w in warnings if re.search(r"CUDA out of memory|OutOfMemoryError|Traceback \(most recent", w["text"])],
                   "request_count": len(requests),
                   "network_boundary": "Observed HTTP logs concern local serving. Internet disabled in notebook metadata; logs are not a full network audit."},
        "arms": {},
    }
    for parent in manifest["arms"]:
        name = parent["arm"]
        meta_path, benchmark_path, log_path = [RUN / name / f for f in ("arm-metadata.json", "benchmark.json", "run.log")]
        source_paths += [meta_path, benchmark_path, log_path]
        m, b, log = read(meta_path), read(benchmark_path), log_path.read_text()
        begin, deadline = epoch(m["benchmark_started_utc"]), epoch(m["soft_end_local"])
        parent_begin, parent_end = parent["started_at_epoch"], parent["started_at_epoch"]+parent["elapsed_seconds"]
        reqs = [r for r in requests if parent_begin <= r["entry_time"] < parent_end]
        decode = [r for r in batches if r["decode"] and begin <= r["epoch"] <= deadline]
        timeline = [r for r in batches if parent_begin <= r["epoch"] < parent_end]
        input_tokens, cached_tokens, output_tokens = [sum(int(r[k]) for r in reqs) for k in ("input_len", "cached_input_len", "output_len")]
        games = []
        for run in b["game_runs"]:
            entries = run["history"]
            run_start = epoch(run["started_at"])
            action_times = [run_start+e["wallclock_seconds"] for e in entries]
            tokens = sum(int(e.get("generated_tokens", 0) or 0) for e in entries) + int(run.get("final_generated_tokens", 0) or 0)
            note = re.search(r"tokens=(\d+)", run.get("solver_note", ""))
            boundary, completed_after = 0, []
            for level, count in enumerate(run["actions_per_level"][:run["levels_completed"]], 1):
                boundary += count
                if boundary and action_times[boundary-1] > deadline:
                    completed_after.append(level)
            games.append({"game_id": run["game_id"], "state": run["state"],
                          "levels_completed": run["levels_completed"], "score": run["final_score"],
                          "recorded_tokens": tokens, "analyzer_tokens": int(note.group(1)) if note else None,
                          "actions": len(entries), "reset_actions": sum(e["action"]["id"] == "RESET" for e in entries),
                          "first_action": entries[0]["action"] if entries else None,
                          "first_action_seconds_from_benchmark": min(action_times)-begin if action_times else None,
                          "last_action_seconds_from_benchmark": max(action_times)-begin if action_times else None,
                          "post_deadline_actions": [{"index": i+1, "seconds_after": t-deadline} for i, t in enumerate(action_times) if t > deadline],
                          "post_deadline_completed_levels": completed_after,
                          "actions_per_level_sum_matches_history": sum(run["actions_per_level"]) == len(entries)})
        generations_after = [r for r in reqs if r["entry_time"] > deadline]
        crossings = [{"line": r["line"], "entry_seconds_before_deadline": deadline-r["entry_time"],
                      "completion_log_seconds_after_deadline": r["completed_log_epoch"]-deadline,
                      "whole_request_output_tokens_not_tail_only": int(r["output_len"])}
                     for r in reqs if r["entry_time"] <= deadline < r["completed_log_epoch"]]
        disabled = {}
        for filename in ("goal-evidence.json", "transient-history.json", "program-state.json"):
            p = RUN / name / filename
            if p.exists():
                source_paths.append(p)
                obj = read(p)
                disabled[filename] = {"enabled": obj.get("enabled"), "counts": obj.get("counts"),
                                      "events": len(obj.get("events", [])), "calls_observed": obj.get("calls_observed")}
            else:
                disabled[filename] = {"local_artifact_available": False}
        result["arms"][name] = {
            "pid": m["pid"], "status": m["status"], "exit_code": m["exit_code"],
            "budget_seconds": m["budget_seconds"], "parent_arm_wall_seconds": parent["elapsed_seconds"],
            "benchmark_wall_seconds": m["benchmark_wall_seconds"], "budget_window_seconds": deadline-begin,
            "post_deadline_parent_seconds": parent_end-deadline, "soft_deadline_fired": m["soft_deadline_fired"],
            "deadline_beijing": beijing(deadline), "forced_exit": m["forced_cpu_process_exit"],
            "lingering_workers": m["lingering_worker_threads"], "game_state_counts": m["game_state_counts"],
            "game_order_sha256": m["game_order_sha256"], "game_order_matches_config": m["game_ids"] == config["games"],
            "environment": m["environment"], "source_sha256": m["source_sha256"],
            "active_streams": m["active_streams"], "concurrency": m["concurrency"], "n_passes": m["n_passes"],
            "warmup_action_games": m["warmup_action_games"],
            "all_first_actions_are_non_reset": all(g["first_action"] and g["first_action"]["id"] != "RESET" for g in games),
            "post_deadline_actions": sum(len(g["post_deadline_actions"]) for g in games),
            "post_deadline_completed_levels": sum(len(g["post_deadline_completed_levels"]) for g in games),
            "old_intervention_reports": disabled,
            "gpu_budget_window": gpu_window(samples, begin, deadline),
            "gpu_drain_window": gpu_window(samples, deadline, parent_end),
            "server": {"requests": len(reqs), "output_tokens": output_tokens, "input_tokens": input_tokens,
                       "cached_input_tokens": cached_tokens, "uncached_input_tokens": input_tokens-cached_tokens,
                       "input_token_weighted_cache_hit_percent": 100*cached_tokens/input_tokens if input_tokens else None,
                       "output_tokens_per_benchmark_second": output_tokens/m["benchmark_wall_seconds"],
                       "queue_ms": stats([r["queue_duration"] for r in reqs]),
                       "initial_prefill_ms": stats([r["initial_prefill_elapsed"] for r in reqs]),
                       "decode_running_requests": stats([r["#running-req"] for r in decode]),
                       "decode_accept_length": stats([r["accept len"] for r in decode if "accept len" in r]),
                       "last_batch_seconds_after_deadline": timeline[-1]["epoch"]-deadline if timeline else None,
                       "max_batch_log_gap_seconds": max((b["epoch"]-a["epoch"] for a,b in zip(timeline,timeline[1:])), default=None)},
            "server_recorded_entry_after_deadline": generations_after,
            "requests_crossing_deadline": crossings,
            "analyzer_tokens": sum(g["analyzer_tokens"] for g in games),
            "recorded_tokens": sum(g["recorded_tokens"] for g in games),
            "diagnostics_render_seconds": [float(x) for x in re.findall(r"regenerated diagnostics .*? in ([\d.]+)s", log)],
            "client_read_timeouts": len(re.findall(r"analyzer request timed out", log)),
            "warmup_log_lines": [s for s in log.splitlines() if "warmup RESET" in s],
            "games": games,
        }
    a, b = (result["arms"][name] for name in ARMS)
    result["validity"].update({"separate_arm_pids": a["pid"] != b["pid"],
                               "same_environment": a["environment"] == b["environment"],
                               "same_game_order_hash": a["game_order_sha256"] == b["game_order_sha256"]})
    result["paired_resource_comparison"] = {
        "server_output_tokens_B_over_A": b["server"]["output_tokens"]/a["server"]["output_tokens"],
        "analyzer_tokens_B_over_A": b["analyzer_tokens"]/a["analyzer_tokens"],
        "server_throughput_B_over_A": b["server"]["output_tokens_per_benchmark_second"]/a["server"]["output_tokens_per_benchmark_second"],
    }
    archive_path = RUN / "retrievable_animation/retrievable-animation.json"
    archive = read(archive_path)
    source_paths.append(archive_path)
    result["archive_overhead"] = {k: archive[k] for k in ("limits", "counts", "stored_frame_json_bytes", "peak_frame_json_bytes", "capture_cpu_seconds", "query_cpu_seconds")}
    result["combined_arm_server_output_tokens"] = sum(x["server"]["output_tokens"] for x in result["arms"].values())
    result["gross_session_tokens_per_second"] = result["combined_arm_server_output_tokens"]/manifest["elapsed_seconds"]
    result["sources"] = {str(p.relative_to(ROOT)): {"sha256": digest(p), "bytes": p.stat().st_size} for p in source_paths}
    result["methods"] = [
        "Naive timestamps in benchmark/server logs are UTC; display timezone Asia/Shanghai.",
        "GPU interpolation uses timestamp=time, clipped trapezoids between actual samples, with no extrapolation. Sparse samples are not continuous kernel measurements.",
        "Low-util candidates require at least 3 consecutive samples below 50%, spanning at least 19.5 seconds with gaps at most 16 seconds.",
        "Server requests are deduplicated by rid+entry_time, attributed by entry_time within each parent arm. Completed log timestamps have one-second resolution.",
        "A server entry_time after the deadline does not establish when the client sent the request or identify its game; no such attribution is assumed.",
        "Whole output of a request crossing the deadline is not output generated only after that deadline.",
        "Action absolute time = game.started_at + history.wallclock_seconds. First-action delay may include waiting, action-free inference and CPU processing; it does not establish the first LLM request, GPU-slot admission or queue time.",
        "Capture/query CPU counters exclude thread lock waiting and total IPC/child processing; stored JSON bytes are not process RSS.",
        "No account-balance delta is attributed to this run. Session wall hours are measured duration, not a billing claim.",
        "A single baseline-first paired run with stochastic decoding/shared admission does not establish intervention efficacy.",
    ]
    target = ROOT / "experiments/010-efficiency.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({"output": str(target), "runtime": result["runtime"],
                      "paired": result["paired_resource_comparison"],
                      "arms": {n: {k: x[k] for k in ("benchmark_wall_seconds", "analyzer_tokens", "recorded_tokens", "post_deadline_actions", "client_read_timeouts")} for n,x in result["arms"].items()}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
