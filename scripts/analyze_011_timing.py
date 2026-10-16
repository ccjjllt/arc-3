#!/usr/bin/env python3
"""Read-only 011 timing/resource audit; never executes logged model code."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics


def read(path):
    return json.loads(path.read_text())


def utc(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def source(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def occupancy(intervals):
    edges = sorted([(a, 1) for a, b in intervals] + [(b, -1) for a, b in intervals])
    active = maximum = 0
    for _, delta in edges:
        active += delta
        maximum = max(maximum, active)
    return {"max_concurrent": maximum, "final_open": active,
            "sum_interval_seconds": sum(b - a for a, b in intervals)}


def session_report(s, run, deadline_t, origin):
    events = s["events"]
    queued, held, requests, http = {}, [], {}, {}
    current_hold = None
    gate_waits, failures = [], []
    for e in events:
        kind = e["kind"]
        if kind == "gate_enqueue_begin":
            queued[e["gate_call_id"]] = e
        elif kind == "gate_admitted_return":
            q = queued.pop(e["gate_call_id"])
            gate_waits.append({"operation": e["operation"], "begin_t": q["t"],
                               "end_t": e["t"], "wait_s": e["t"] - q["t"]})
            if current_hold is not None:
                failures.append("overlapping_slot_admission")
            current_hold = e["t"]
        elif kind == "gate_release_credit":
            if current_hold is None:
                failures.append("release_without_observed_admission")
            else:
                held.append((current_hold, e["t"]))
                current_hold = None
        elif kind == "chat_begin":
            requests[e["request_id"]] = {"begin_t": e["t"], "tools_present": e["tools_present"]}
        elif kind in ("chat_return", "chat_exception"):
            requests[e["request_id"]].update(end_t=e["t"], status=kind,
                generated_tokens=e.get("generated_tokens"), exception_type=e.get("exception_type"))
        elif kind == "http_attempt_begin":
            http[(e["request_id"], e["attempt"])] = {"begin_t": e["t"]}
        elif kind in ("http_attempt_return", "http_attempt_exception"):
            http[(e["request_id"], e["attempt"])].update(end_t=e["t"], status=kind,
                exception_type=e.get("exception_type"))
    if queued or current_hold is not None:
        failures.append("unclosed_gate_interval")
    if any("end_t" not in r for r in [*requests.values(), *http.values()]):
        failures.append("unclosed_request")
    if any(not any(a <= r["begin_t"] <= b for a, b in held) for r in http.values()):
        failures.append("http_outside_observed_slot")
    counts = Counter(e["kind"] for e in events)
    if any(s["counts"].get(k) != n for k, n in counts.items()):
        failures.append("event_counter_mismatch")
    if any(a["t"] > b["t"] for a, b in zip(events, events[1:])):
        failures.append("nonmonotonic_event_time")
    if [e["seq"] for e in events] != list(range(1, s["events_observed"] + 1)):
        failures.append("missing_event_sequence")
    known_tokens = sum(r.get("generated_tokens") or 0 for r in requests.values())
    note = re.fullmatch(r"tokens=(\d+)", run.get("solver_note") or "")
    analyzer_tokens = int(note[1]) if note else None
    if analyzer_tokens != known_tokens:
        failures.append("usage_vs_analyzer_note_mismatch")
    session_start = s["session_started_t"]
    first = s["first_times"]
    first_http = first.get("http_attempt_begin")
    first_action = run["history"][0]["wallclock_seconds"] if run["history"] else None
    run_start_t = (utc(run["started_at"]) - origin).total_seconds()
    after = [{"kind": e["kind"], "request_id": e.get("request_id"),
              "seconds_after_soft_end": e["t"] - deadline_t}
             for e in events if e["kind"] in ("chat_begin", "http_attempt_begin", "gate_admitted_return")
             and e["t"] > deadline_t]
    exceptions = [{"request_id": k, **r, "end_after_soft_end_s": r["end_t"] - deadline_t}
                  for k, r in requests.items() if r.get("status") == "chat_exception"]
    return {
        "game_id": s["game_id"], "game_index": s["game_index"], "session_id": s["session_id"],
        "session_started_t": session_start,
        "first_gate_admission_delay_s": first["gate_admitted_return"] - session_start,
        "first_http_delay_s": s["first_http_delay_from_session_start_s"],
        "first_actual_action_game_elapsed_s": first_action,
        "first_action_minus_first_http_approx_s": (
            run_start_t + first_action - first_http if first_action is not None and first_http is not None else None),
        "initial_gate_wait_s": sum(g["wait_s"] for g in gate_waits if g["operation"] == "acquire"),
        "handover_wait_s": sum(g["wait_s"] for g in gate_waits if g["operation"] == "handover"),
        "total_gate_wait_s": sum(g["wait_s"] for g in gate_waits), "gate_intervals": gate_waits,
        "slot_held_s": sum(b - a for a, b in held), "slot_intervals": held,
        "chat_calls": len(requests), "http_attempts": len(http),
        "chat_seconds_including_exceptions": sum(r["end_t"] - r["begin_t"] for r in requests.values()),
        "http_seconds_including_exceptions": sum(r["end_t"] - r["begin_t"] for r in http.values()),
        "chat_tools_absent_calls": sum(not r["tools_present"] for r in requests.values()),
        "known_generated_tokens": known_tokens, "analyzer_note_tokens": analyzer_tokens,
        "action_attached_tokens": sum(a.get("generated_tokens", 0) for a in run["history"]),
        "successful_returns_without_usage": sum(r.get("status") == "chat_return" and r.get("generated_tokens") is None for r in requests.values()),
        "exceptions": exceptions, "starts_after_global_soft_end": after,
        "last_http_start_before_soft_end_s": deadline_t - max(r["begin_t"] for r in http.values()),
        "completed_returns_after_soft_end": sum(r["end_t"] > deadline_t and r["status"] == "chat_return" for r in requests.values()),
        "deadline_spanning_chats": sum(r["begin_t"] <= deadline_t < r["end_t"] for r in requests.values()),
        "play_exit_after_soft_end_s": first.get("play_return", first.get("play_exception")) - deadline_t,
        "events_observed": s["events_observed"], "events_dropped": s["events_dropped"],
        "observer_errors": s["counts"].get("observer_record_errors", 0),
        "integrity_failures": failures, "score": run["final_score"],
        "levels_completed": run["levels_completed"], "actual_actions": len(run["history"]),
        "http_intervals": [(r["begin_t"], r["end_t"]) for r in http.values()],
    }


def arm_report(root, arm):
    directory = root / arm
    timing, meta, bm = (read(directory / name) for name in
                        ("inference-timing.json", "arm-metadata.json", "benchmark.json"))
    origin = utc(timing["clock_origin_utc"])
    deadline_t = (utc(meta["soft_end_local"]) - origin).total_seconds()
    runs = {r["game_id"]: r for r in bm["game_runs"]}
    games = [session_report(s, runs[s["game_id"]], deadline_t, origin) for s in timing["sessions"]]
    games.sort(key=lambda x: x["game_index"])
    counters = Counter()
    for session in timing["sessions"]:
        counters.update(session["counts"])
    result = {
        "clock_origin_utc": timing["clock_origin_utc"], "global_soft_end_t": deadline_t,
        "benchmark_started_utc": meta["benchmark_started_utc"], "arm_finished_utc": meta["finished_utc"],
        "benchmark_elapsed_s": (utc(bm["end_time"]) - utc(bm["start_time"])).total_seconds(),
        "snapshot_after_soft_end_s": timing["snapshot_t"] - deadline_t,
        "observer_validity": {k: timing.get(k) for k in ("observer", "provisional", "sessions_seen",
            "sessions_recorded", "sessions_omitted_by_limit", "snapshot_after_worker_join", "lingering_worker_threads")},
        "observer_module_sha256": meta["source_sha256"].get("inference_timing.py"),
        "hook_source_sha256": timing["source_sha256"], "counts": dict(counters), "games": games,
        "initial_admission_order": [s["game_id"] for s in sorted(timing["sessions"], key=lambda s:s["first_times"]["gate_admitted_return"])],
        "slot_occupancy": occupancy([p for g in games for p in g["slot_intervals"]]),
        "client_http_occupancy": occupancy([p for g in games for p in g["http_intervals"]]),
        "new_calls_after_global_soft_end": sum(len(g["starts_after_global_soft_end"]) for g in games),
        "events_dropped": sum(g["events_dropped"] for g in games),
        "observer_errors": sum(g["observer_errors"] for g in games),
        "integrity_failures": [{"game_id": g["game_id"], "issues": g["integrity_failures"]} for g in games if g["integrity_failures"]],
    }
    for g in games:
        del g["http_intervals"]  # summaries suffice; all raw events remain in source
    return result


def resources(root, arms):
    gpu = defaultdict(list)
    for line in (root / "gpu-utilization.jsonl").open():
        record = json.loads(line)
        if record.get("returncode") != 0:
            continue
        try:
            values = [float(v.strip()) for v in record["metrics"].split(",")]
        except (KeyError, ValueError):
            continue
        gpu[record["phase"]].append(values)
    gpu_stats = {phase: {"samples": len(rows), "gpu_util_mean_percent": statistics.mean(r[0] for r in rows),
        "gpu_util_median_percent": statistics.median(r[0] for r in rows),
        "samples_at_least_90_percent_fraction": sum(r[0] >= 90 for r in rows) / len(rows),
        "samples_at_most_10_percent_fraction": sum(r[0] <= 10 for r in rows) / len(rows),
        "memory_peak_mib": max(r[1] for r in rows), "power_mean_watts": statistics.mean(r[3] for r in rows)}
        for phase, rows in gpu.items()}
    server = defaultdict(list)
    for line_number, line in enumerate((root / "serve.log").open(), 1):
        if "ReqTimeStats(" not in line:
            continue
        values = dict(re.findall(r"(input_len|cached_input_len|output_len|entry_time|queue_duration|initial_prefill_elapsed|post_prefill_elapsed|forward_duration)=([\d.]+)", line))
        if not {"entry_time", "output_len"} <= values.keys():
            continue
        entry = float(values["entry_time"])
        for arm, data in arms.items():
            if utc(data["benchmark_started_utc"]).timestamp() <= entry <= utc(data["arm_finished_utc"]).timestamp():
                server[arm].append({k: float(v) for k, v in values.items()} | {"source_line": line_number})
    server_stats = {}
    for arm, rows in server.items():
        deadline_epoch = utc(arms[arm]["clock_origin_utc"]).timestamp() + arms[arm]["global_soft_end_t"]
        server_stats[arm] = {"completed_stats_records": len(rows),
            "summed_logged_output_len": sum(int(r["output_len"]) for r in rows),
            "entry_after_soft_end_records": sum(r["entry_time"] > deadline_epoch for r in rows),
            "entries_after_soft_end": [{"source_line": r["source_line"],
                "entry_time_epoch": r["entry_time"], "seconds_after_soft_end": r["entry_time"] - deadline_epoch,
                "output_len": int(r["output_len"])} for r in rows if r["entry_time"] > deadline_epoch],
            "client_usage_residual": sum(int(r["output_len"]) for r in rows) - arms[arm]["counts"]["observed_generated_tokens"],
            "queue_duration_ms_mean": statistics.mean(r["queue_duration"] for r in rows if "queue_duration" in r),
            "cached_input_fraction": sum(r.get("cached_input_len", 0) for r in rows) / max(1, sum(r.get("input_len", 0) for r in rows))}
    return {"gpu_sampling": gpu_stats, "server_req_time_stats": server_stats}


def comparison_010(old, arms):
    result = []
    for arm in arms:
        bm = read(old / arm / "benchmark.json")
        for r in bm["game_runs"]:
            if not r["game_id"].startswith(("m0r0", "ft09")):
                continue
            path = old / arm / "artifacts" / f"{r['game_id']}_p0_events.jsonl"
            first_hhmmss = None
            if path.exists():
                for line in path.open():
                    e = json.loads(line)
                    match = re.search(r"analysis_step=1 \| action=1 \| (\d\d:\d\d:\d\d) \|", e.get("transcript", ""))
                    if match:
                        first_hhmmss = match[1]
                        break
            note = re.fullmatch(r"tokens=(\d+)", r.get("solver_note") or "")
            result.append({"experiment": "010", "arm": arm, "game_id": r["game_id"],
                "first_analysis_clock_hhmmss_proxy": first_hhmmss,
                "game_started_at": r["started_at"], "first_http_delay_s": None, "gate_wait_s": None,
                "first_actual_action_game_elapsed_s": r["history"][0]["wallclock_seconds"],
                "analyzer_reported_tokens": int(note[1]) if note else None,
                "score": r["final_score"], "levels_completed": r["levels_completed"]})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("runs/011-animation-confirmation"))
    parser.add_argument("--old-root", type=Path, default=Path("runs/010-retrievable-animation"))
    parser.add_argument("--output", type=Path, default=Path("experiments/011-timing-analysis.json"))
    args = parser.parse_args()
    arms = {arm: arm_report(args.root, arm) for arm in ("retrievable_animation", "baseline")}
    paths = [args.root / arm / name for arm in arms for name in
             ("inference-timing.json", "arm-metadata.json", "benchmark.json")]
    paths += [args.root / name for name in ("gpu-utilization.jsonl", "serve.log")]
    for arm in arms:
        paths.append(args.old_root / arm / "benchmark.json")
        paths.extend(p for game in ("m0r0", "ft09")
                     for p in (args.old_root / arm / "artifacts").glob(game + "*_events.jsonl"))
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only 011 observer, benchmark and resource-log analysis; no model/logged code execution.",
        "sources": [source(p) for p in paths], "arms": arms,
        "resources": resources(args.root, arms), "010_comparison": comparison_010(args.old_root, arms),
        "hook_hashes_equal": arms["baseline"]["hook_source_sha256"] == arms["retrievable_animation"]["hook_source_sha256"],
        "boundaries": [
            "Gate admission-return is worker-observed ownership, not pump-grant or GPU-start time.",
            "Slot holding includes local Python and waits; summed game-seconds are not GPU wall-clock or quota.",
            "HTTP entry means requests.post called; client durations include service/transport and possibly retries at logical level.",
            "Tokens are successful-return usage only; failed/partial generation is unknown. Server output_len is a separate logged accounting view.",
            "First action uses benchmark game elapsed time. First-action-minus-first-HTTP also uses UTC/monotonic clock anchoring and is approximate.",
            "010 has no observer. Transcript HH:MM:SS is a coarse analysis-start proxy, not measured HTTP/gate admission.",
            "GPU utilization means are arithmetic sample means, not GPU busy-time integrals. Shared concurrent allocation is not an independent causal treatment estimate."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({arm: {k: arms[arm][k] for k in ("new_calls_after_global_soft_end", "events_dropped", "observer_errors", "integrity_failures")} for arm in arms}, indent=2))
    print(json.dumps(report["resources"]["server_req_time_stats"], indent=2))


if __name__ == "__main__":
    main()
