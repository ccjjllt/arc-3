#!/usr/bin/env python3
"""Audit completed 014 timing/resource files; never executes logged model code."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics

import analyze_011_timing as shared

ARMS = ("baseline", "tail_80k")


def digest(path):
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def summary(values):
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    return {"count": len(values), "min": ordered[0], "median": statistics.median(ordered),
            "mean": statistics.mean(ordered), "max": ordered[-1],
            "p95_nearest_rank": ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]}


def deadline_report(root, arm, timing_summary):
    timing = shared.read(root / arm / "inference-timing.json")
    deadline = shared.read(root / arm / "request-deadline.json")
    benchmark = shared.read(root / arm / "benchmark.json")
    cutoff = timing_summary["global_soft_end_t"]
    offset = (shared.utc(deadline["clock_origin_utc"]) - shared.utc(timing["clock_origin_utc"])).total_seconds()
    blocks = [{**event, "timing_t": offset + event["t"],
               "seconds_after_soft_end": offset + event["t"] - cutoff}
              for event in deadline["events"] if event["kind"] == "request_blocked"]
    blocked_at = {event["game_id"]: event["timing_t"] for event in blocks}
    http_after_stop, after_deadline, last_http = [], [], []
    for session in timing["sessions"]:
        for event in session["events"]:
            if event["kind"] not in ("chat_begin", "http_attempt_begin"):
                continue
            row = {"game_id": session["game_id"], "kind": event["kind"],
                   "request_id": event["request_id"], "timing_t": event["t"],
                   "seconds_after_soft_end": event["t"] - cutoff}
            if event["t"] > cutoff:
                after_deadline.append(row)
            if event["kind"] == "http_attempt_begin":
                last_http.append(event["t"])
                if event["t"] > blocked_at.get(session["game_id"], float("inf")):
                    http_after_stop.append(row)
    actions_after, last_actions = [], []
    origin = shared.utc(timing["clock_origin_utc"])
    for run in benchmark["game_runs"]:
        start = (shared.utc(run["started_at"]) - origin).total_seconds()
        times = [start + entry["wallclock_seconds"] for entry in run["history"]]
        if times:
            last_actions.append(max(times))
        actions_after.extend({"game_id": run["game_id"], "history_index": index,
                              "seconds_after_soft_end": t-cutoff}
                             for index, t in enumerate(times) if t > cutoff)
    counts = deadline["counts"]
    return {
        "active_sessions": deadline["active_sessions"], "provisional": deadline["provisional"],
        "snapshot_after_worker_join": deadline["snapshot_after_worker_join"],
        "lingering_worker_threads": deadline["lingering_worker_threads"],
        "counts": counts, "boundary_counts": deadline["boundary_counts"],
        "retained_events": len(deadline["events"]), "events_dropped_by_bound": deadline["events_dropped"],
        "retained_block_events": blocks,
        "all_block_events_retained": len(blocks) == counts.get("request_blocked", 0),
        "new_client_chat_or_http_after_soft_end": after_deadline,
        "client_http_after_observed_session_stop": http_after_stop,
        "last_client_http_start_before_soft_end_s": cutoff - max(last_http),
        "action_records_after_soft_end": actions_after,
        "last_recorded_action_before_soft_end_s": cutoff - max(last_actions),
        "action_time_method": "GameRun.started_at plus cumulative ActionRecord.wallclock_seconds; UTC alignment, not an instrumented action-start boundary.",
        "evidence_boundary": "The 256-event deadline deque intentionally evicts old passed checks. Aggregate counts survive; full no-new-client-request evidence comes from lossless inference-timing. Client admission does not guarantee server arrival before deadline or abort in-flight work.",
    }


def scheduler_report(root, arm, timing_summary):
    data = shared.read(root / arm / "scheduler-observer.json")
    timing = shared.read(root / arm / "inference-timing.json")
    events = data["events"]
    issues = []
    if [e["seq"] for e in events] != list(range(1, data["events_observed"] + 1)):
        issues.append("event_sequence_incomplete")
    if any(a["monotonic"] > b["monotonic"] for a, b in zip(events, events[1:])):
        issues.append("event_time_nonmonotonic")
    if dict(Counter(e["kind"] for e in events)) != data["counts"]:
        issues.append("event_counts_disagree")
    enqueues, selections, by_session = {}, {}, defaultdict(list)
    missing_owners = omitted = snapshots = 0
    max_queue = 0
    for event in events:
        max_queue = max(max_queue, event["candidate_count"])
        omitted += event["candidates_omitted"]
        missing_owners += sum(row["session"] is None for row in event["candidates"])
        if event["kind"] == "enqueue":
            key = (event["gate_id"], event["gate_seq"])
            if key in enqueues:
                issues.append("duplicate_enqueue")
            enqueues[key] = event
        if event["kind"] != "selection":
            continue
        chosen = event["selected"]
        key = (event["gate_id"], chosen["token"])
        if key in selections:
            issues.append("duplicate_selection")
        selections[key] = event
        if chosen not in event["candidates"]:
            issues.append("chosen_missing_from_candidates")
        if event["candidates_omitted"] == 0:
            expected = min(event["candidates"], key=lambda row: (-row["priority"], row["token"]))
            if chosen != expected:
                issues.append("selection_disagrees_with_priority_fifo")
        if chosen["snapshot"] is not None:
            snapshots += 1
        if chosen["session"] is not None:
            by_session[chosen["session"]["session_id"]].append(event)
    if set(enqueues) != set(selections):
        issues.append("unmatched_enqueue_selection_tokens")
    wake_delays, identities, mismatched_counts = [], [], []
    for session in timing["sessions"]:
        choices = by_session[session["session_id"]]
        admitted = [e for e in session["events"] if e["kind"] == "gate_admitted_return"]
        if len(choices) != len(admitted):
            mismatched_counts.append(session["game_id"])
        for chosen, returned in zip(choices, admitted):
            delay = timing["clock_origin_monotonic"] + returned["t"] - chosen["monotonic"]
            wake_delays.append(delay)
            if delay < 0:
                issues.append("admitted_return_before_selection")
            if chosen["selected"]["session"]["game_id"] != session["game_id"]:
                identities.append(session["game_id"])
    cutoff = timing["clock_origin_monotonic"] + timing_summary["global_soft_end_t"]
    choices = list(selections.values())
    first_choices = {}
    for event in choices:
        owner = event["selected"]["session"]
        if owner is not None:
            first_choices.setdefault(owner["game_id"], event)
    origin = timing["clock_origin_monotonic"]
    return {
        "events_observed": data["events_observed"], "events_dropped": data["events_dropped"],
        "observer_record_errors": data["observer_record_errors"], "counts": data["counts"],
        "gates": data["gates"], "max_candidate_count": max_queue,
        "candidate_rows_omitted": omitted, "candidate_owner_rows_missing": missing_owners,
        "selected_rows_with_snapshot": snapshots, "integrity_failures": sorted(set(issues)),
        "session_selection_count_mismatches": mismatched_counts,
        "session_identity_mismatches": identities,
        "selection_to_admitted_return_seconds": summary(wake_delays),
        "selections_after_soft_end": sum(e["monotonic"] > cutoff for e in choices),
        "initial_selection_order": [{"game_id": game, "timing_t": event["monotonic"]-origin}
                                    for game,event in first_choices.items()],
        "source_sha256": data["source_sha256"],
        "instrumented_source_sha256": data["instrumented_source_sha256"],
        "snapshot_after_worker_join": data["snapshot_after_worker_join"],
        "lingering_worker_threads": data["lingering_worker_threads"],
        "scope": "Validates observed decisions and attribution; does not treat a changed ordering on a different trajectory as a causal score replay.",
    }


def lifecycle(root, manifest):
    lines = (root / "serve.log").read_text().splitlines()
    markers = ("The server is fired up", "Cache flushed successfully!", "SIGTERM received.",
               "Subprocess detokenizer", "No live scheduler processes found", "kill_process_tree called")
    events = [{"source_line": i, "text": line} for i,line in enumerate(lines,1)
              if any(marker in line for marker in markers)]
    kernel = shared.read(root / "kernel.log")
    samples = [json.loads(line) for line in (root / "gpu-utilization.jsonl").read_text().splitlines()]
    return {"server_events": events,
        "ready_count": sum("The server is fired up" in line for line in lines),
        "cache_flush_success_count": sum("Cache flushed successfully!" in line for line in lines),
        "explicit_cuda_oom_lines": [{"source_line":i,"text":line} for i,line in enumerate(lines,1)
                                    if re.search(r"CUDA out of memory|torch.OutOfMemoryError",line)],
        "gpu_samples": len(samples), "gpu_error_records": sum(x.get("returncode") != 0 for x in samples),
        "gpu_sampler_sampling_seconds": summary([x["sampling_seconds"] for x in samples]),
        "gpu_final_samples": samples[-2:],
        "kernel_last_elapsed_seconds": max(x["time"] for x in kernel),
        "manifest_cleanup": {key:manifest[key] for key in ("status","gpu_server_process_group_stopped",
            "gpu_server_leader_exited","gpu_server_stopped","gpu_sampling")},
        "startup_to_model_ready_seconds": manifest["model_ready_seconds"],
        "internal_session_seconds": manifest["elapsed_seconds"],
        "internal_session_hours": manifest["elapsed_seconds"]/3600,
        "assigned_arm_budget_seconds": sum(a["budget_seconds"] for a in manifest["arms"]),
        "budget_fraction_of_internal_session": sum(a["budget_seconds"] for a in manifest["arms"])/manifest["elapsed_seconds"],
        "nonbudget_session_seconds": manifest["elapsed_seconds"]-sum(a["budget_seconds"] for a in manifest["arms"]),
        "shutdown_note": "Detokenizer SIGQUIT/crash wording follows the requested SIGTERM during teardown; do not classify that sequence as an in-arm model failure.",
    }


def execution_validity(root, manifest, arms):
    metadata = {arm:shared.read(root/arm/"arm-metadata.json") for arm in ARMS}
    before, after = (metadata[a] for a in ARMS)
    differences = {key:{"baseline":before["environment"].get(key), "tail_80k":after["environment"].get(key)}
                   for key in before["environment"].keys() | after["environment"].keys()
                   if before["environment"].get(key) != after["environment"].get(key)}
    expected_order = manifest["experiment"]["games"]
    fields = ("budget_seconds","normalized_budget_seconds","active_streams","concurrency",
              "n_passes","warmup_action_games","game_order_sha256","game_ids","requested_game_ids",
              "analyzer_timeout_seconds","source_sha256")
    return {"same_fields": {key:before.get(key)==after.get(key) for key in fields},
            "source_hashes_equal": before["source_sha256"] == after["source_sha256"],
            "only_environment_difference_is_tail_lookup": set(differences)=={"ARC3_PRIORITY_TAIL_LOOKUP"},
            "environment_differences": differences,
            "game_ids_match_manifest_order": {a:metadata[a]["game_ids"]==expected_order for a in ARMS},
            "arm_order": [a["arm"] for a in manifest["arms"]],
            "arm_processes_distinct": before["pid"] != after["pid"],
            "manifest_arms": manifest["arms"],
            "worker_drained": {a:metadata[a]["lingering_worker_threads"]==[] and
                arms[a]["observer_validity"]["snapshot_after_worker_join"] and
                not arms[a]["observer_validity"]["provisional"] for a in ARMS},
            "budget_context": {a:{k:metadata[a].get(k) for k in ("status","budget_seconds",
                "normalized_budget_seconds","benchmark_wall_seconds","soft_deadline_fired",
                "cancel_drain_timeout_seconds","finished_utc")} for a in ARMS},
            "design_limit": "One fixed-order baseline-then-tail pair on known public games; equal engineering conditions do not remove model randomness or order effects."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path("runs/014-tail-allocation"))
    parser.add_argument("--output",type=Path,default=Path("experiments/014-timing-analysis.json"))
    args = parser.parse_args()
    mandatory = [args.root/name for name in ("experiment-manifest.json","serve.log","gpu-utilization.jsonl","kernel.log")]
    mandatory += [args.root/arm/name for arm in ARMS for name in
                  ("arm-metadata.json","benchmark.json","inference-timing.json","scheduler-observer.json","request-deadline.json","run.log")]
    missing = [str(p) for p in mandatory if not p.is_file()]
    if missing:
        raise FileNotFoundError("Incomplete downloaded evidence: " + ", ".join(missing))
    manifest = shared.read(args.root / "experiment-manifest.json")
    arms = {arm:shared.arm_report(args.root,arm) for arm in ARMS}
    for arm,data in arms.items():
        late_kinds = Counter(event["kind"] for game in data["games"] for event in game["starts_after_global_soft_end"])
        data["late_gate_wakeups"] = late_kinds["gate_admitted_return"]
        data["late_chat_begins"] = late_kinds["chat_begin"]
        data["late_http_attempts"] = late_kinds["http_attempt_begin"]
        data["new_calls_after_global_soft_end_semantics"] = (
            "Legacy shared-analysis field counts gate_admitted_return + chat_begin + http_attempt_begin; "
            "it is not a count of new model/HTTP requests. Use the three explicit late_* counters.")
        data["deadline"] = deadline_report(args.root,arm,data)
        data["scheduler"] = scheduler_report(args.root,arm,data)
        data["first_http_coverage_seconds"] = summary([g["first_http_delay_s"] for g in data["games"]])
        data["last_first_action_game_elapsed_seconds"] = max(g["first_actual_action_game_elapsed_s"] for g in data["games"])
        meta = shared.read(args.root/arm/"arm-metadata.json")
        start_t = (shared.utc(meta["benchmark_started_utc"])-shared.utc(data["clock_origin_utc"])).total_seconds()
        clipped_slot_seconds = sum(max(0,min(end,data["global_soft_end_t"])-max(begin,start_t))
                                   for game in data["games"] for begin,end in game["slot_intervals"])
        data["slot_capacity_occupied_inside_budget_fraction"] = clipped_slot_seconds/(meta["active_streams"]*meta["budget_seconds"])
        data["successful_usage_tokens_per_budget_second"] = data["counts"]["observed_generated_tokens"]/meta["budget_seconds"]
    report = {"kind":"014-completed-timing-resource-audit", "analyzed_at_utc":datetime.now(timezone.utc).isoformat(),
        "sources":[digest(p) for p in mandatory], "analysis_script":digest(Path(__file__)),
        "shared_analysis_script":digest(Path(shared.__file__)),
        "execution_validity":execution_validity(args.root,manifest,arms), "arms":arms,
        "resources":shared.resources(args.root,arms), "lifecycle":lifecycle(args.root,manifest),
        "limits":["GPU utilization is sampled device activity, not useful-token FLOP efficiency.",
                  "Logged server output_len includes failed/unfinished client responses; without shared request IDs residuals cannot be allocated exactly.",
                  "Account quota change and session-internal elapsed time have different scope; no billing attribution is inferred."]}
    completion = Path("experiments/014-completion.json")
    if completion.is_file():
        report["account_completion_source"] = digest(completion)
        report["account_completion_receipt"] = shared.read(completion)
        before_path = Path("experiments/014-jiyujia-quota-before.json")
        if before_path.is_file():
            before = shared.read(before_path)
            after = report["account_completion_receipt"]
            delta = after["gpu"]["time_used"]-before["gpu"]["time_used"]
            report["account_quota_comparison"] = {
                "before_source":digest(before_path), "same_refresh_period":before["quota_refresh_time"]==after["quota_refresh_time"],
                "before_checked_at_utc":before["checked_at_utc"], "after_checked_at_utc":after["checked_at_utc"],
                "account_gpu_used_delta_seconds":delta, "account_gpu_used_delta_hours":delta/3600,
                "account_gpu_reserved_after_seconds":after["gpu"]["time_reserved"],
                "session_internal_seconds":manifest["elapsed_seconds"],
                "account_delta_minus_session_seconds":delta-manifest["elapsed_seconds"],
                "attribution":"This is an account-level usage change over the receipt interval, not an experiment billing record. The difference cannot be assigned wholly to this task, provisioning, or platform overhead from these files."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({a:{"timing_failures":d["integrity_failures"],"scheduler_failures":d["scheduler"]["integrity_failures"],
                        "new_requests_after_cutoff":len(d["deadline"]["new_client_chat_or_http_after_soft_end"]),
                        "late_action_records":len(d["deadline"]["action_records_after_soft_end"])} for a,d in arms.items()},indent=2))


if __name__ == "__main__":
    main()
