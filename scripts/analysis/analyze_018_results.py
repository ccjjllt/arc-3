#!/usr/bin/env python3
"""Read-only 018 scoring, provenance, resource and manual-adoption evidence audit.

No SDK imports, pickle loading, logged-code execution, network or GPU access.
The pool/budgets/arms come from the downloaded manifest, not this script.
Keyword tags are navigation aids ONLY. Adoption requires a separate attributed semantic review.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics

from analyze_005_results import audit_timing
from analyze_011_results import aggregate, score_run
from analyze_011_timing import arm_report, utc
from analyze_014_timing import deadline_report, scheduler_report

ROOT = Path(__file__).resolve().parents[2]
PREFIX_KEY = "ARC3_SYSTEM_PROMPT_PREFIX"
NOTE = ("Descriptive fixed-order public-development comparison. Neither score changes "
        "nor keyword/AST occurrences establish adoption or causal benefit.")


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def origin(path):
    return {"path": str(path.resolve()), "sha256": sha(path), "bytes": path.stat().st_size}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def stats(values):
    if not values:
        return {"count": 0}
    values = sorted(values)
    return {"count": len(values), "min": values[0], "mean": statistics.fmean(values),
            "median": statistics.median(values), "max": values[-1],
            "p95_nearest_rank": values[max(0, (95 * len(values) + 99) // 100 - 1)]}


def level_costs(raw):
    cursor, previous_end, rows = 0, 0.0, []
    for index, count in enumerate(raw["actions_per_level"]):
        history = raw["history"][cursor:cursor + count]
        cursor += count
        end = history[-1]["wallclock_seconds"] if history else previous_end
        rows.append({"level": index + 1, "completed": index < raw["levels_completed"],
                     "actions": count, "first_history_index": cursor - count,
                     "last_history_index": cursor - 1 if count else None,
                     "action_attached_tokens": sum(h.get("generated_tokens", 0) for h in history),
                     "action_attached_uncached_input_tokens": sum(h.get("uncached_input_tokens", 0) for h in history),
                     "last_action_game_seconds": end if history else None,
                     "elapsed_since_previous_level_last_action_seconds": end - previous_end})
        previous_end = end
    return {"levels": rows, "final_unattached_to_action_tokens": raw.get("final_generated_tokens", 0),
            "note": "Action-attached token accounting only. A request may span a level boundary; final generation is not assigned to a level without evidence."}


def compare(manifest, raw, metadata):
    arms, ids = manifest["experiment"]["arm_order"], manifest["experiment"]["games"]
    a, b = arms
    maps, summaries, timing = {}, {}, {}
    for arm in arms:
        rows = [score_run(r) for r in raw[arm]["game_runs"]]
        assert len(rows) == len({r["game_id"] for r in rows}), "Duplicate game runs"
        assert set(ids) == {r["game_id"] for r in rows}, "Incomplete benchmark pool"
        assert raw[arm]["n_passes"] == 1 and raw[arm]["game_weights"] is None
        maps[arm] = {r["game_id"]: r for r in rows}
        summaries[arm] = aggregate(rows)
        timing[arm] = audit_timing(raw[arm], metadata[arm])
    games = []
    for game in ids:
        aa, bb = maps[a][game], maps[b][game]
        assert aa["number_of_levels"] == bb["number_of_levels"]
        parts = dict(shared_completed_levels=0.0, new_completed_levels=0.0,
                     lost_completed_levels=0.0, cap_adjustment_delta=bb["cap_adjustment"] - aa["cap_adjustment"])
        for la, lb in zip(aa["levels"], bb["levels"]):
            assert la["baseline_actions"] == lb["baseline_actions"]
            delta = lb["uncapped_game_contribution"] - la["uncapped_game_contribution"]
            key = ("shared_completed_levels" if la["completed"] and lb["completed"] else
                   "new_completed_levels" if lb["completed"] else "lost_completed_levels")
            parts[key] += delta
        delta = bb["AE"] - aa["AE"]
        assert abs(sum(parts.values()) - delta) < 1e-8
        games.append({"game_id": game, a: aa, b: bb, "score_delta": delta,
                      "levels_delta": bb["levels_completed"] - aa["levels_completed"],
                      "mean_score_contribution": delta / len(ids), "score_decomposition": parts})
    total = sum(r["score_delta"] for r in games)
    for row in games:
        row["leave_one_out_mean_delta"] = (total - row["score_delta"]) / (len(games) - 1) if len(games) > 1 else None
    keys = ("mean_AE", "mean_completion_ceiling", "mean_efficiency_gap", "levels_completed", "wins",
            "actions", "analyzer_tokens", "recorded_tokens", "unattached_tokens", "uncached_input_tokens")
    return {"arms": summaries, "delta": {k: summaries[b][k] - summaries[a][k] for k in keys},
            "games": games, "timing": timing,
            "largest_positive_contributor": max(games, key=lambda r: r["score_delta"])["game_id"],
            "levels_costs": {arm: {r["game_id"]: level_costs(r) for r in raw[arm]["game_runs"]} for arm in arms},
            "scope": NOTE, "score_is_adoption_gate": False,
            "formula": "Level min(115,100*(base_actions/actions)^2), weighted by 1..N; final cap from completed positive-scoring weights. Uncapped level contributions are not additive final scores without the cap adjustment."}


def notebook_evidence(directory):
    build = read(directory / "build-manifest.json")
    notebook = directory / "experiment.ipynb"
    embedded, prefix = {}, None
    for cell in read(notebook)["cells"]:
        source = "".join(cell.get("source", []))
        if not source.startswith("%%writefile /kaggle/research/"):
            continue
        first, body = source.split("\n", 1)
        path = first.removeprefix("%%writefile /kaggle/research/")
        embedded[path] = digest(body.encode())
        if path == "src/arc3_research/observation_grounding.py":
            for node in ast.parse(body).body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GROUNDING_PREFIX" for t in node.targets):
                    prefix = ast.literal_eval(node.value)
    return build, prefix, {"notebook": origin(notebook), "build_manifest": origin(directory / "build-manifest.json"),
                           "notebook_hash_matches": sha(notebook) == build["notebook_sha256"],
                           "embedded_source_hashes": embedded,
                           "embedded_hash_checks": {p: h == build["source_hashes"].get(p) for p, h in embedded.items()},
                           "prefix_source": "Static literal parsed from frozen notebook payload; never imported or executed."}


def static_tags(code):
    # Search hints, deliberately no adoption or correctness classification.
    patterns = {"ascii_text": r"\bascii\b", "segmentation_text": r"segment|pixel_count|bounding|bbox",
                "encoding_text": r"mask|grid|board|cells|pattern|shape|coordinates?",
                "check_text": r"assert|verify|check|mismatch|correct|offset|origin",
                "search_text": r"search|solve|deque|heapq|frontier|bfs|dfs",
                "action_text": r"\.act\b|action|click|ACTION[1-7]"}
    return [name for name, pattern in patterns.items() if re.search(pattern, code, re.I)]


REQUEST_IDENTITY_FIELDS = ("messages", "tools", "action", "analysis_step",
                           "request_index_within_turn", "tool_choice", "chat_template_kwargs")


def fallback_response_evidence(arm_root, game_paths):
    """Match only unambiguous fallback responses to a full same-arm request.

    The frozen harness resolves the output name again after a response. When
    other games have removed their state files it uses ``requests.jsonl``.
    Never infer ownership from token counts, time, game order, or last survivor.
    """
    fallback = arm_root / "requests.jsonl"
    assigned = {game: [] for game in game_paths}
    evidence = {"source": origin(fallback) if fallback.is_file() else None,
                "identity_fields": list(REQUEST_IDENTITY_FIELDS), "matches": [], "issues": []}
    if not fallback.is_file():
        return assigned, evidence
    requests_by_identity, answered = defaultdict(list), set()
    for game, path in game_paths.items():
        source = origin(path)
        for line_number, line in enumerate(path.open(), 1):
            try:
                event = json.loads(line)
            except ValueError:
                continue  # extract_log records the parse failure separately.
            if not isinstance(event, dict) or any(k not in event for k in REQUEST_IDENTITY_FIELDS):
                continue
            identity = {k: event[k] for k in REQUEST_IDENTITY_FIELDS}
            key = canonical(identity)
            if event.get("event") == "request":
                requests_by_identity[key].append({"game_id": game, "source": source,
                    "source_line": line_number, "identity": identity})
            elif event.get("event") == "response":
                answered.add((game, key))
    for line_number, line in enumerate(fallback.open(), 1):
        location = {"source": evidence["source"], "source_line": line_number}
        try:
            event = json.loads(line)
        except ValueError as exc:
            evidence["issues"].append({**location, "issue": "invalid_fallback_json", "detail": str(exc)})
            continue
        if not isinstance(event, dict) or event.get("event") != "response":
            evidence["issues"].append({**location, "issue": "unsupported_fallback_event"})
            continue
        missing = [k for k in REQUEST_IDENTITY_FIELDS if k not in event]
        if missing:
            evidence["issues"].append({**location, "issue": "fallback_missing_identity_fields", "fields": missing})
            continue
        identity = {k: event[k] for k in REQUEST_IDENTITY_FIELDS}
        key = canonical(identity)
        matches = requests_by_identity.get(key, [])
        if len(matches) != 1:
            evidence["issues"].append({**location, "issue": "fallback_request_match_not_unique",
                                        "matching_requests": len(matches)})
            continue
        match = matches[0]
        game = match["game_id"]
        # Compare every observed field as well as its indexed serialization.
        if identity != match["identity"] or (game, key) in answered:
            evidence["issues"].append({**location, "issue": "fallback_response_duplicate_or_already_matched",
                                        "game_id": game})
            continue
        answered.add((game, key))
        binding = {**location, "game_id": game, "request_identity_sha256": digest(key.encode()),
                   "matched_request": {k: v for k, v in match.items() if k != "identity"}}
        evidence["matches"].append(binding)
        assigned[game].append({"event": event, "binding": binding})
    return assigned, evidence


def extract_log(path, prefix, fallback_responses=()):
    """Deduplicate call IDs, retaining original code/results and occurrence locations.

    Requests/responses contain snapshots of *prior* messages. Their action/usage
    cannot be assigned to a newly observed snippet as its dispatch/generation.
    """
    calls, results, responses, requests, issues = {}, {}, [], [], []
    primary_source = origin(path)
    system_hashes, stripped_hashes, tools_hashes = Counter(), Counter(), Counter()
    no_tools, no_tool_seen = [], set()
    prefix_checks = []
    for line_number, line in enumerate(path.open(), 1):
        try:
            event = json.loads(line)
        except ValueError as exc:
            issues.append({"line": line_number, "issue": "invalid_json", "detail": str(exc)})
            continue
        messages = event.get("messages", [])
        kind = event.get("event")
        context = {"source_line": line_number, "source_path": primary_source["path"],
                   "source_sha256": primary_source["sha256"],
                   "event": kind, "action_at_snapshot": event.get("action"),
                   "analysis_step_at_snapshot": event.get("analysis_step"),
                   "request_index_within_turn": event.get("request_index_within_turn")}
        if kind == "request":
            requests.append(context)
            tools_hashes[digest(canonical(event.get("tools")).encode())] += 1
            for m in messages:
                if m.get("role") == "system":
                    content = m.get("content")
                    if not isinstance(content, str):
                        issues.append({"line": line_number, "issue": "nontext_system_prompt"})
                        continue
                    system_hashes[digest(content.encode())] += 1
                    if prefix is not None:
                        present = content.startswith(prefix + "\n\n")
                        prefix_checks.append(present)
                        stripped_hashes[digest((content[len(prefix) + 2:] if present else content).encode())] += 1
        elif kind == "response":
            responses.append({**context, "finish_reason": event.get("finish_reason"), "usage": event.get("usage")})
        for index, message in enumerate(messages):
            if message.get("role") == "assistant" and not message.get("tool_calls"):
                signature = digest(canonical(message).encode())
                if signature not in no_tool_seen:
                    no_tool_seen.add(signature)
                    no_tools.append({**context, "message_index": index, "message": message,
                                     "note": "Unique message content, not an exact no-tool event count; identical distinct returns may collapse."})
            for call in message.get("tool_calls") or []:
                tid = call.get("id")
                if not tid:
                    issues.append({"line": line_number, "message_index": index, "issue": "missing_call_id"})
                    continue
                fn = call.get("function", {})
                signature = canonical(fn)
                if tid in calls:
                    calls[tid]["snapshot_appearances"] += 1
                    calls[tid]["last_seen_line"] = line_number
                    if signature != calls[tid]["_signature"]:
                        issues.append({"line": line_number, "call_id": tid, "issue": "conflicting_function_for_id", "function": fn})
                    continue
                code, decode_error = None, None
                try:
                    args = json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                    if isinstance(args, dict):
                        code = args.get("code")
                except (ValueError, TypeError) as exc:
                    decode_error = str(exc)
                calls[tid] = {"call_id": tid, "seq": len(calls) + 1, "first_seen": context,
                              "message_index": index, "last_seen_line": line_number,
                              "snapshot_appearances": 1, "function": fn, "code": code,
                              "reasoning": message.get("reasoning_content", message.get("reasoning", message.get("content"))),
                              "argument_decode_error": decode_error, "navigation_tags": static_tags(code or ""),
                              "_signature": signature}
            tid = message.get("tool_call_id")
            if message.get("role") != "tool" or not tid:
                continue
            content = message.get("content")
            signature = canonical(content)
            if tid in results:
                results[tid]["snapshot_appearances"] += 1
                results[tid]["last_seen_line"] = line_number
                if signature != results[tid]["_signature"]:
                    issues.append({"line": line_number, "call_id": tid, "issue": "conflicting_result_for_id", "content": content})
                continue
            try:
                body = json.loads(content) if isinstance(content, str) else content
            except (ValueError, TypeError):
                body = None
            results[tid] = {"first_seen": context, "message_index": index, "last_seen_line": line_number,
                            "snapshot_appearances": 1, "raw_content": content, "parsed_content": body, "_signature": signature}
    for supplemental in fallback_responses:
        event, binding = supplemental["event"], supplemental["binding"]
        responses.append({"source_line": binding["source_line"],
                          "source_path": binding["source"]["path"],
                          "source_sha256": binding["source"]["sha256"],
                          "event": "response", "action_at_snapshot": event["action"],
                          "analysis_step_at_snapshot": event["analysis_step"],
                          "request_index_within_turn": event["request_index_within_turn"],
                          "finish_reason": event.get("finish_reason"), "usage": event.get("usage"),
                          "fallback_binding": binding})
        # The matched full request already contributed every historical message.
        # Do not manufacture new tool calls from this duplicate context snapshot.
    snippets = []
    for tid, call in calls.items():
        call.pop("_signature")
        result = results.pop(tid, None)
        if result:
            result.pop("_signature")
        call["result"] = result
        body = result.get("parsed_content") if result else None
        call["observed_result_error"] = body.get("error") if isinstance(body, dict) else None
        call["stdout_action_echo_present"] = "[action]" in str(body.get("stdout", "")) if isinstance(body, dict) else None
        snippets.append(call)
    usage = [r["usage"] for r in responses if isinstance(r["usage"], dict)]
    supplemental_sources = {r["binding"]["source"]["path"]: r["binding"]["source"]
                            for r in fallback_responses}
    return {"source": primary_source, "sources": [primary_source, *supplemental_sources.values()],
            "fallback_response_matches": [r["binding"] for r in fallback_responses],
            "requests": requests, "responses": responses,
            "summary": {"request_records": len(requests), "response_records": len(responses),
                        "unique_tool_call_ids": len(snippets), "calls_with_results": sum(r["result"] is not None for r in snippets),
                        "finish_reasons": dict(Counter(r["finish_reason"] for r in responses)),
                        "response_usage_completion_tokens": sum(u.get("completion_tokens", 0) or 0 for u in usage),
                        "response_usage_prompt_tokens": sum(u.get("prompt_tokens", 0) or 0 for u in usage),
                        "responses_without_usage": len(responses) - len(usage)},
            "system_prompt_hashes": dict(system_hashes), "stripped_system_prompt_hashes": dict(stripped_hashes),
            "tool_schema_hashes": dict(tools_hashes),
            "prefix_present_on_all_request_systems": all(prefix_checks) if prefix_checks else None,
            "prefix_present_on_any_request_systems": any(prefix_checks) if prefix_checks else None,
            "issues": issues, "orphan_result_ids": list(results), "no_tool_message_candidates": no_tools,
            "snippets": snippets,
            "limits": ["Call ID deduplication removes repeated historical snapshots, not independent model requests.",
                       "First appearance is an observation in a later snapshot, not proven generation/dispatch time. Do not attribute that snapshot's usage to the snippet.",
                       "A final generated call/result may never enter a subsequent request snapshot. Missing results are unknown, not failed calls.",
                       "Navigation tags have no adoption/correctness meaning. All snippets remain available, including untagged ones."]}


def trajectory_evidence(root, out, arms, ids, prefix):
    rows, reports, fallback_evidence = [], {}, {}
    for arm in arms:
        game_paths = {}
        for game in ids:
            paths = sorted(set((root / arm).glob(f"{game}_p0_requests.jsonl")) |
                           set((root / arm / "artifacts").glob(f"{game}_p0_requests.jsonl")))
            if not paths:
                rows.append({"arm": arm, "game_id": game, "status": "missing_log"})
                continue
            hashes = {sha(path) for path in paths}
            if len(hashes) > 1:
                rows.append({"arm": arm, "game_id": game, "status": "conflicting_log_copies", "sources": [origin(p) for p in paths]})
                continue
            game_paths[game] = paths[0]
        supplemental, fallback_evidence[arm] = fallback_response_evidence(root / arm, game_paths)
        for game, path in game_paths.items():
            report = extract_log(path, prefix, supplemental[game])
            report["issues"].extend(fallback_evidence[arm]["issues"])
            destination = out / "trajectories" / f"{arm}-{game}.json"
            save(destination, report)
            reports[(arm, game)] = report
            rows.append({"arm": arm, "game_id": game, "status": "extracted", "source": report["source"],
                         "sources": report["sources"], "fallback_response_matches": report["fallback_response_matches"],
                         "derived_path": str(destination.resolve()), "summary": report["summary"],
                         "issues": report["issues"]})
    base, candidate = arms
    base_systems = set().union(*(set(r["system_prompt_hashes"]) for (a, _), r in reports.items() if a == base))
    candidate_systems = set().union(*(set(r["stripped_system_prompt_hashes"]) for (a, _), r in reports.items() if a == candidate))
    tools = {a: set().union(*(set(r["tool_schema_hashes"]) for (arm, _), r in reports.items() if arm == a)) for a in arms}
    reconciliation = []
    for arm in arms:
        timing_path = root / arm / "inference-timing.json"
        sessions = {s["game_id"]: s for s in read(timing_path)["sessions"]} if timing_path.is_file() else {}
        runs = {r["game_id"]: r for r in read(root / arm / "benchmark.json")["game_runs"]}
        for game in ids:
            report, session = reports.get((arm, game)), sessions.get(game)
            if report is None or session is None:
                reconciliation.append({"arm": arm, "game_id": game, "status": "missing_evidence", "passes": False})
                continue
            counts, summary = session["counts"], report["summary"]
            note = re.fullmatch(r"tokens=(\d+)", runs[game].get("solver_note", ""))
            analyzer_tokens = int(note[1]) if note else None
            expected = {"request_records": counts.get("chat_begin", 0), "response_records": counts.get("chat_return", 0),
                        "response_usage_completion_tokens": counts.get("observed_generated_tokens", 0)}
            checks = {k: summary[k] == value for k, value in expected.items()}
            checks["known_usage_response_count"] = summary["response_records"] - summary["responses_without_usage"] == counts.get("responses_with_known_tokens", 0)
            checks["usage_equals_analyzer_note"] = analyzer_tokens is not None and summary["response_usage_completion_tokens"] == analyzer_tokens
            reconciliation.append({"arm": arm, "game_id": game, "status": "checked", "passes": all(checks.values()),
                                   "checks": checks, "expected_timing": expected, "observed_log": summary,
                                   "benchmark_analyzer_tokens": analyzer_tokens,
                                   "note": "A final exception can leave request_count greater than response_count. Counts are compared to chat_begin/return separately, not forced equal."})
    return {"logs": rows, "fallback_response_evidence": fallback_evidence,
            "complete_log_pool": len(reports) == len(arms) * len(ids),
            "log_timing_token_reconciliation": reconciliation,
            "all_log_counts_and_usage_reconcile": all(r["passes"] for r in reconciliation),
            "observed_tool_schema_sets_equal": bool(tools[base]) and tools[base] == tools[candidate],
            "candidate_stripped_systems_present_in_baseline": bool(candidate_systems) and candidate_systems <= base_systems,
            "baseline_has_no_candidate_prefix": bool(base_systems) and all(r["prefix_present_on_any_request_systems"] is False for (a, _), r in reports.items() if a == base) if prefix else None,
            "candidate_all_request_systems_have_prefix": bool(candidate_systems) and all(r["prefix_present_on_all_request_systems"] is True for (a, _), r in reports.items() if a == candidate) if prefix else None,
            "note": "System suffix hash comparisons cover downloaded requests only; dynamic prompt variants absent from baseline are flagged for inspection, not silently normalized."}, reports


def gpu_resources(root, manifest, metadata):
    path = root / "gpu-utilization.jsonl"
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    arm_windows = []
    for entry in manifest["arms"]:
        arm = entry["arm"]
        m = metadata[arm]
        arm_windows.append((arm, entry["started_at_epoch"], utc(m["benchmark_started_utc"]).timestamp(),
                            utc(m["soft_end_local"]).timestamp(), utc(m["finished_utc"]).timestamp()))
    def classify(epoch):
        for arm, start, benchmark, deadline, finish in arm_windows:
            if start <= epoch < benchmark:
                return arm + ":setup"
            if benchmark <= epoch < min(deadline, finish):
                return arm + ":strict_budget"
            if deadline <= epoch <= finish:
                return arm + ":drain"
        return "startup" if epoch < min(w[1] for w in arm_windows) else "between_arms_or_shutdown"
    groups, original, samples, errors = defaultdict(list), Counter(), [], []
    for line_no, line in enumerate(path.open(), 1):
        row = json.loads(line)
        original[row.get("phase", "unknown")] += 1
        epoch = row.get("observed_at_epoch", row.get("time"))
        if row.get("returncode") != 0:
            errors.append({"source_line": line_no, "record": row})
            continue
        # nvidia-smi emits one CSV line per GPU; keep each device distinct.
        for device, metrics in enumerate(row.get("metrics", "").splitlines()):
            try:
                util, memory, total, power = (float(v.strip()) for v in metrics.split(","))
                assert epoch is not None
            except (ValueError, AssertionError):
                errors.append({"source_line": line_no, "issue": "unparsed_metrics", "record": row})
                continue
            phase = classify(epoch)
            sample = {"source_line": line_no, "epoch": epoch, "device_index_in_csv": device,
                      "original_phase": row.get("phase"), "derived_phase": phase,
                      "util_percent": util, "memory_mib": memory, "total_memory_mib": total, "power_watts": power}
            samples.append(sample)
            groups[(phase, device)].append(sample)
    result = []
    for (phase, device), rows in sorted(groups.items()):
        result.append({"phase": phase, "device_index_in_csv": device, "samples": len(rows),
                       "util_percent": stats([r["util_percent"] for r in rows]),
                       "at_least_90_percent_fraction": sum(r["util_percent"] >= 90 for r in rows) / len(rows),
                       "at_most_10_percent_fraction": sum(r["util_percent"] <= 10 for r in rows) / len(rows),
                       "memory_peak_mib": max(r["memory_mib"] for r in rows),
                       "power_watts": stats([r["power_watts"] for r in rows]),
                       "sampling_gap_seconds": stats([b["epoch"] - a["epoch"] for a, b in zip(rows, rows[1:])]),
                       "first_source_line": rows[0]["source_line"], "last_source_line": rows[-1]["source_line"]})
    return {"source": origin(path), "groups": result, "samples": samples, "errors": errors,
            "original_phase_counts": dict(original),
            "arm_windows": [{"arm": a, "process_start_epoch": s, "benchmark_start_epoch": b,
                             "soft_end_epoch": d, "finished_epoch": f} for a, s, b, d, f in arm_windows],
            "note": "Sample arithmetic means, not GPU busy-time integrals. Strict windows use actual benchmark start/soft deadline, excluding startup and drain; no inference that high utilization improves score or that slot time is CPU/GPU busy time."}


def server_evidence(root, manifest, metadata):
    path = root / "serve.log"
    if not path.is_file():
        return {"status": "missing"}
    rows, markers = defaultdict(list), []
    for line_no, line in enumerate(path.open(), 1):
        if any(text in line for text in ("The server is fired up", "Cache flushed successfully!", "SIGTERM received.", "CUDA out of memory", "torch.OutOfMemoryError")):
            markers.append({"source_line": line_no, "text": line.rstrip()})
        if "ReqTimeStats(" not in line:
            continue
        values = {k: float(v) for k, v in re.findall(r"(input_len|cached_input_len|output_len|entry_time|queue_duration|initial_prefill_elapsed|post_prefill_elapsed|forward_duration)=([\d.]+)", line)}
        if "entry_time" not in values:
            continue
        for arm, m in metadata.items():
            if utc(m["benchmark_started_utc"]).timestamp() <= values["entry_time"] <= utc(m["finished_utc"]).timestamp():
                rows[arm].append({"source_line": line_no, **values})
    return {"source": origin(path), "lifecycle_markers": markers,
            "backend_cache_flush_success_markers": sum("Cache flushed successfully!" in r["text"] for r in markers),
            "arm_server_records": dict(rows),
            "arm_summary": {a: {"records": len(rs), "logged_output_tokens": sum(r.get("output_len", 0) for r in rs),
                                  "cached_input_fraction": sum(r.get("cached_input_len", 0) for r in rs) / max(1, sum(r.get("input_len", 0) for r in rs)),
                                  "queue_duration_ms": stats([r["queue_duration"] for r in rs if "queue_duration" in r])} for a, rs in rows.items()},
            "manifest_cache_confirmation": {e["arm"]: e.get("cache_flush_backend_confirmed") for e in manifest["arms"]},
            "note": "Server records are attributed by entry timestamp, not assumed identical to successful client usage or a particular tool call."}


def validity(manifest, build, frozen, metadata, prefix, comparison):
    arms, ids = manifest["experiment"]["arm_order"], manifest["experiment"]["games"]
    a, b = arms
    ma, mb = metadata[a], metadata[b]
    env_diff = {k: [ma["environment"].get(k), mb["environment"].get(k)]
                for k in ma["environment"].keys() | mb["environment"].keys()
                if ma["environment"].get(k) != mb["environment"].get(k)}
    sa, sb = ma["source_sha256"], mb["source_sha256"]
    common = sa.keys() & sb.keys()
    checks = {"manifest_config_matches_frozen_build": manifest["experiment"] == build["config"],
              "manifest_sources_match_frozen_build": manifest["source_hashes"] == build["source_hashes"],
              "frozen_notebook_hash_matches": frozen["notebook_hash_matches"],
              "all_embedded_sources_match": bool(frozen["embedded_hash_checks"]) and all(frozen["embedded_hash_checks"].values()),
              "ordered_baseline_then_grounding": arms == ["baseline", "observation_grounding"],
              "both_game_orders_match": all(metadata[x]["game_ids"] == ids for x in arms),
              "equal_requested_budgets": all(metadata[x]["budget_seconds"] == manifest["experiment"]["requested_arm_seconds"] for x in arms),
              "complete_clean_arms": all(e.get("exit_code") == 0 and e.get("complete_pool") for e in manifest["arms"]),
              "cache_confirmed": all(e.get("cache_flush_backend_confirmed") for e in manifest["arms"]),
              "workers_drained": all(metadata[x].get("lingering_worker_threads") == [] for x in arms),
              "server_stopped": manifest.get("gpu_server_stopped") is True,
              "common_runtime_sources_equal": all(sa[k] == sb[k] for k in common),
              "only_candidate_grounding_source_added": set(sb) - set(sa) == {"observation_grounding.py"} and not (set(sa) - set(sb)),
              "baseline_prefix_empty": not ma["environment"].get(PREFIX_KEY, "").strip(),
              "candidate_prefix_equals_frozen": prefix is not None and mb["environment"].get(PREFIX_KEY) == prefix,
              "only_environment_difference_prefix": set(env_diff) == {PREFIX_KEY},
              "no_post_deadline_actions_or_completed_levels": all(not r["post_deadline_action_count"] and not r["post_deadline_completed_levels"] for arm in arms for r in comparison["timing"][arm]["runs"].values())}
    same_fields = ("game_ids", "requested_game_ids", "game_order_sha256", "operation_mode", "budget_seconds",
                   "normalized_budget_seconds", "active_streams", "concurrency", "n_passes", "warmup_action_games", "analyzer_timeout_seconds")
    checks.update({"same_" + k: ma.get(k) == mb.get(k) for k in same_fields})
    runtime_checks = {}
    for arm in arms:
        runtime_checks[arm] = {}
        for name, actual in metadata[arm]["source_sha256"].items():
            matches = [h for p, h in build["source_hashes"].items() if Path(p).name == name]
            matches += [h for p, h in manifest["experiment"].get("runtime_source_sha256", {}).items() if Path(p).name == name]
            if matches:
                runtime_checks[arm][name] = set(matches) == {actual}
    checks["runtime_sources_match_frozen_hashes"] = all(v for rows in runtime_checks.values() for v in rows.values())
    return {"metadata_and_build_checks": checks, "metadata_and_build_checks_pass": all(checks.values()), "environment_differences": env_diff,
            "runtime_hash_checks": runtime_checks,
            "unmapped_runtime_hashes": {arm: [p for p in metadata[arm]["source_sha256"] if p not in runtime_checks[arm]] for arm in arms},
            "note": "Unmapped bundle/pickle hashes are retained and compared across arms, not silently claimed verified against the build. Current working-tree hashes are not a substitute for frozen experiment provenance."}


def review_template(arms, ids, reports, review_inputs):
    return {"schema_version": 1, "review_inputs": review_inputs, "reviewer": "", "reviewed_at_utc": "", "entries": [],
            "game_review_status": [{"arm": a, "game_id": g, "status": "pending", "opportunities": None, "notes": ""} for a in arms for g in ids],
            "entry_example_do_not_count": {"arm": arms[1], "game_id": ids[0], "classification": "correct_confirmation",
                "level": None, "observation_call_ids": [], "encoding_call_ids": [], "consumption_call_ids": [],
                "wrong_encoding_call_ids": [], "correction_call_ids": [], "frame_and_coordinate_evidence": "",
                "pixel_or_cell_recomputation": "", "actual_consumption_evidence": "", "outcome_evidence": "",
                "new_misuse_excluded": None, "reviewer_conclusion": ""},
            "classifications": ["correct_confirmation", "error_corrected", "error_intercepted", "new_misuse", "unused_or_insufficient"],
            "instructions": ["Fill a separate copy and pass --reviews; this generated template is always pending, never adoption evidence.",
                "Read original source lines and untruncated code/results. IDs refer to the corresponding game/arm deduplicated trajectory.",
                "Prove current-frame crop bounds/origin/row-col/characters, encoded state and downstream consumption; printing or uncalled function definitions do not qualify.",
                "Correct first encoding is confirmation, not prevention. Correction requires an observed wrong prior encoding and changed state; action-before/after must be supported separately.",
                "Record baseline chains too. Inspect stale frame/new-level coordinates, holes/components, color-mask versus physical-footprint distinctions and added read overhead.",
                "At least two candidate games need verified extraction→encoding→consumption chains, with at least one concrete correction/interception and no observed new misuse; score is evaluated separately.",
                "Machine checks validate reference existence, not semantic truth. Record whether the reviewer is a human or an AI agent; explicit semantic judgment remains necessary."]}


def adoption_review(path, arms, ids, reports, review_inputs=None, runtime_evidence_valid=False):
    if path is None:
        return {"status": "pending_manual_review", "passes": None, "confirmed_games": None,
                "note": "No keyword/AST-based adoption count is computed."}
    review = read(path)
    checked, issues = [], []
    allowed = {"correct_confirmation", "error_corrected", "error_intercepted", "new_misuse", "unused_or_insufficient"}
    for index, entry in enumerate(review.get("entries", [])):
        arm, game = entry.get("arm"), entry.get("game_id")
        report = reports.get((arm, game))
        known = {r["call_id"] for r in report["snippets"]} if report else set()
        returned = {r["call_id"] for r in report["snippets"] if r["result"] is not None} if report else set()
        refs = [r for k, values in entry.items() if k.endswith("_call_ids") for r in values]
        missing = sorted(set(refs) - known)
        missing_results = sorted(set(refs) - returned)
        chain = all(entry.get(k) for k in ("observation_call_ids", "encoding_call_ids", "consumption_call_ids",
                     "frame_and_coordinate_evidence", "pixel_or_cell_recomputation", "actual_consumption_evidence", "reviewer_conclusion"))
        correction = entry.get("classification") in {"error_corrected", "error_intercepted"}
        correction_refs = bool(entry.get("wrong_encoding_call_ids") and entry.get("correction_call_ids"))
        valid = arm in arms and game in ids and report is not None and not missing and entry.get("classification") in allowed
        if not valid:
            issues.append({"entry_index": index, "missing_call_ids": missing, "invalid_arm_game_class_or_log": not (arm in arms and game in ids and report and entry.get("classification") in allowed)})
        checked.append({"entry_index": index, "arm": arm, "game_id": game, "classification": entry.get("classification"),
                        "references_exist": valid, "referenced_results_missing": missing_results,
                        "reviewer_asserted_complete_chain": bool(valid and not missing_results and chain and (not correction or correction_refs)),
                        "new_misuse_excluded": entry.get("new_misuse_excluded") is True})
    candidate = arms[1]
    eligible = [e for e in checked if e["arm"] == candidate and e["reviewer_asserted_complete_chain"] and e["new_misuse_excluded"] and e["classification"] in {"correct_confirmation", "error_corrected", "error_intercepted"}]
    statuses = {(e.get("arm"), e.get("game_id")): e.get("status") for e in review.get("game_review_status", [])}
    complete = all(statuses.get((a, g)) == "reviewed" for a in arms for g in ids)
    gates = {"named_reviewer": bool(review.get("reviewer")), "all_games_reviewed": complete,
             "review_bound_to_this_manifest_and_logs": review_inputs is not None and review.get("review_inputs") == review_inputs,
             "runtime_evidence_valid": runtime_evidence_valid is True,
             "all_game_logs_available_without_identity_conflicts": len(reports) == len(arms) * len(ids) and all(not r["issues"] for r in reports.values()),
             "reference_integrity": not issues,
             "two_candidate_games_with_reviewed_chain": len({e["game_id"] for e in eligible}) >= 2,
             "at_least_one_concrete_correction_or_interception": any(e["classification"] in {"error_corrected", "error_intercepted"} for e in eligible),
             "no_reported_candidate_new_misuse": not any(e["arm"] == candidate and e["classification"] == "new_misuse" for e in checked)}
    return {"status": "review_supplied", "source": origin(path), "entries": checked, "issues": issues,
            "gates": gates, "passes": all(gates.values()), "confirmed_games": sorted({e["game_id"] for e in eligible}),
            "note": "Passing here means supplied reviewer judgments satisfy the stated gate and call IDs exist. This script does not establish pixel correctness, causal benefit, exhaustive misuse absence or a counterfactual prevented error."}


def runtime_validation(root, arms, ids, timing, timing_issues, trajectories, reports, prefix):
    checks = {"timing_reports_complete": len(timing) == len(arms) and not timing_issues,
              "complete_request_log_pool": trajectories["complete_log_pool"],
              "all_log_counts_and_usage_reconcile": trajectories["all_log_counts_and_usage_reconcile"],
              "request_logs_parse_and_call_id_integrity": bool(reports) and all(not r["issues"] for r in reports.values())}
    checks.update({k: trajectories[k] is True for k in ("observed_tool_schema_sets_equal",
                  "candidate_stripped_systems_present_in_baseline", "baseline_has_no_candidate_prefix",
                  "candidate_all_request_systems_have_prefix")})
    for arm in arms:
        data = timing.get(arm)
        if not data:
            checks[arm + ":timing_valid"] = False
            continue
        observer, deadline, scheduler = data["observer_validity"], data["deadline"], data["scheduler"]
        checks[arm + ":timing_valid"] = (observer["sessions_seen"] == observer["sessions_recorded"] == len(ids)
            and observer["sessions_omitted_by_limit"] == 0 and observer["snapshot_after_worker_join"] is True
            and not observer["provisional"] and not observer["lingering_worker_threads"]
            and not data["events_dropped"] and not data["observer_errors"] and not data["integrity_failures"])
        checks[arm + ":deadline_valid"] = (deadline["snapshot_after_worker_join"] is True and not deadline["provisional"]
            and not deadline["active_sessions"] and not deadline["lingering_worker_threads"]
            and not deadline["new_client_chat_or_http_after_soft_end"]
            and not deadline["client_http_after_observed_session_stop"] and not deadline["action_records_after_soft_end"])
        checks[arm + ":scheduler_valid"] = (scheduler["snapshot_after_worker_join"] is True
            and not scheduler["lingering_worker_threads"] and not scheduler["events_dropped"]
            and not scheduler["observer_record_errors"] and not scheduler["integrity_failures"]
            and not scheduler["session_selection_count_mismatches"] and not scheduler["session_identity_mismatches"])
    snapshot = root / arms[1] / "observation-grounding.json"
    data = read(snapshot) if snapshot.is_file() else {}
    checks["candidate_prefix_snapshot_matches_frozen"] = (prefix is not None and data.get("enabled") is True
        and data.get("prefix_sha256") == digest(prefix.encode()) and data.get("prefix_characters") == len(prefix)
        and data.get("adds_tools") is False and data.get("adds_framework_model_calls") is False
        and data.get("adds_framework_game_actions") is False and data.get("changes_memory_contract") is False)
    checks["baseline_has_no_grounding_snapshot"] = not (root / arms[0] / "observation-grounding.json").exists()
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/018-observation-grounding")
    parser.add_argument("--notebook-dir", type=Path, default=ROOT / "notebooks/018-observation-grounding")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/018-analysis")
    parser.add_argument("--reviews", type=Path, help="Separate attributed adoption review JSON; never overwritten")
    parser.add_argument("--allow-other-experiment", action="store_true", help="Read-only legacy fixture rehearsal, explicitly not 018 results")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    if root == out or root in out.parents or out in root.parents:
        parser.error("Derived output and immutable raw input directories must be disjoint")
    if args.reviews and args.reviews.resolve().is_relative_to(out):
        parser.error("Keep human review files outside the generated output directory so they cannot be overwritten")
    manifest = read(root / "experiment-manifest.json")
    arms, ids = manifest["experiment"]["arm_order"], manifest["experiment"]["games"]
    if len(arms) != 2 or len(set(ids)) != len(ids) or not ids:
        parser.error("Expected two arms and a nonempty unique game pool")
    is018 = arms == ["baseline", "observation_grounding"]
    if not is018 and not args.allow_other_experiment:
        parser.error("Not an 018 arm pair; use --allow-other-experiment only for a labeled legacy rehearsal")
    required = [root / arm / name for arm in arms for name in ("benchmark.json", "arm-metadata.json")]
    required += [args.notebook_dir / name for name in ("experiment.ipynb", "build-manifest.json")]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Incomplete immutable evidence: " + ", ".join(missing))
    metadata = {a: read(root / a / "arm-metadata.json") for a in arms}
    raw = {a: read(root / a / "benchmark.json") for a in arms}
    comparison = compare(manifest, raw, metadata)
    build, prefix, frozen = notebook_evidence(args.notebook_dir)
    validation = validity(manifest, build, frozen, metadata, prefix, comparison)
    timing, timing_issues = {}, []
    for arm in arms:
        try:
            data = arm_report(root, arm)
            kinds = Counter(e["kind"] for g in data["games"] for e in g["starts_after_global_soft_end"])
            data["explicit_late_event_counts"] = dict(kinds)
            data["late_count_note"] = "Legacy new_calls field also counts gate wakeups; use chat_begin/http_attempt_begin for new client requests."
            data["deadline"] = deadline_report(root, arm, data)
            data["scheduler"] = scheduler_report(root, arm, data)
            data["returned_usage_including_drain_per_assigned_budget_second"] = data["counts"].get("observed_generated_tokens", 0) / metadata[arm]["budget_seconds"]
            data["throughput_accounting_note"] = "Includes successful returns during drain divided by assigned budget. It is not exact in-budget token-generation throughput; a deadline-spanning request cannot be split by return time."
            start = (utc(metadata[arm]["benchmark_started_utc"]) - utc(data["clock_origin_utc"])).total_seconds()
            held = sum(max(0, min(end, data["global_soft_end_t"]) - max(begin, start)) for g in data["games"] for begin, end in g["slot_intervals"])
            data["slot_capacity_occupied_inside_budget_fraction"] = held / (metadata[arm]["active_streams"] * metadata[arm]["budget_seconds"])
            timing[arm] = data
        except (OSError, KeyError, ValueError, AssertionError, TypeError) as exc:
            timing_issues.append({"arm": arm, "error": type(exc).__name__, "detail": str(exc)})
    out.mkdir(parents=True, exist_ok=True)
    trajectories, reports = trajectory_evidence(root, out, arms, ids, prefix)
    validation["runtime_evidence_checks"] = runtime_validation(root, arms, ids, timing, timing_issues, trajectories, reports, prefix)
    validation["runtime_evidence_checks_pass"] = all(validation["runtime_evidence_checks"].values())
    validation["all_checks_pass"] = validation["metadata_and_build_checks_pass"] and validation["runtime_evidence_checks_pass"]
    validation["status"] = ("passed" if validation["all_checks_pass"] else
                            "incomplete_evidence" if not trajectories["complete_log_pool"] or timing_issues else "failed_or_requires_inspection")
    review_inputs = {"experiment_id": manifest["experiment"]["id"], "manifest_sha256": sha(root / "experiment-manifest.json"),
                     "request_log_sha256": {f"{arm}/{game}": report["source"]["sha256"] for (arm, game), report in reports.items()}}
    save(out / "review-template.json", review_template(arms, ids, reports, review_inputs))
    adoption = (adoption_review(args.reviews, arms, ids, reports, review_inputs, validation["all_checks_pass"]) if is018 else
                {"status": "not_applicable_legacy_fixture", "passes": None,
                 "note": "Legacy fixture rehearsal cannot pass the 018 adoption gate, even if --reviews was supplied."})
    gpu, server = gpu_resources(root, manifest, metadata), server_evidence(root, manifest, metadata)
    for name, content in (("comparison.json", comparison), ("validation.json", validation), ("frozen-provenance.json", frozen),
                          ("timing.json", {"arms": timing, "issues": timing_issues}), ("trajectory-index.json", trajectories),
                          ("gpu-phases.json", gpu), ("server-cache.json", server), ("adoption-review.json", adoption)):
        save(out / name, content)
    sources = [origin(root / "experiment-manifest.json")] + [origin(p) for p in required]
    sources += [origin(root / arm / name) for arm in arms for name in ("inference-timing.json", "scheduler-observer.json", "request-deadline.json", "observation-grounding.json", "run.log", "requests.jsonl") if (root / arm / name).is_file()]
    report = {"kind": "018-descriptive-and-adoption-audit" if is018 else "legacy-fixture-rehearsal-NOT-018",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "experiment_id": manifest["experiment"]["id"],
              "game_count": len(ids), "arms": arms, "requested_arm_seconds": manifest["experiment"]["requested_arm_seconds"],
              "score_delta": comparison["delta"], "validation_passes": validation["all_checks_pass"],
              "timing_issues": timing_issues, "adoption_status": adoption["status"], "adoption_passes": adoption["passes"],
              "complete_request_log_pool": trajectories["complete_log_pool"], "sources": sources,
              "analysis_scripts": [origin(Path(__file__)), *[origin(Path(__file__).with_name(n)) for n in ("analyze_005_results.py", "analyze_011_results.py", "analyze_011_timing.py", "analyze_014_timing.py")]],
              "limits": [NOTE, "No adoption pass is inferred from scores, tag frequencies, correct-looking code or old baseline errors.",
                         "No direct CPU-busy telemetry is available; slot/client durations are not CPU compute measurements.",
                         "Successful client usage, action-attached tokens and server output are distinct accounting views.",
                         "Missing logs/timing are explicit evidence gaps; no automatic launch, promotion, submission or rerun occurs."]}
    save(out / "report.json", report)
    (out / "README.md").write_text("# 018 派生证据（只读分析）\n\n" +
        f"输入实验：`{report['experiment_id']}`；{len(ids)} 游戏，{arms[0]} → {arms[1]}，每臂 {report['requested_arm_seconds']} 秒。\n\n" +
        f"描述性 ΔAE={comparison['delta']['mean_AE']:+.6f}，Δ覆盖={comparison['delta']['mean_completion_ceiling']:+.6f}，Δ关卡={comparison['delta']['levels_completed']:+d}。采用状态：`{adoption['status']}`。\n\n" +
        "逐关复算、cap 修正及单局贡献在 comparison.json；工程检查在 validation.json；严格窗口 GPU 样本在 gpu-phases.json；deadline/调度在 timing.json；缓存和服务记录在 server-cache.json。\n\n" +
        "trajectory-index.json 指向每局去重调用原文和原始日志哈希/行号。导航标签只帮助定位，不是采用。复制 review-template.json 到独立文件，人工填写观察→编码→消费与具体纠错证据，再用 --reviews 读取；分数变化与采用门始终分开。\n\n" +
        ("**本目录仅为旧实验兼容演练，不是018结果。**\n\n" if not is018 else "") +
        "未执行模型、游戏、SDK、pickle 或日志代码；未调用网络/GPU。无直接CPU忙时数据。单次开发集结果不能证明隐藏分数或因果收益。\n")
    print(json.dumps({k: report[k] for k in ("kind", "game_count", "score_delta", "validation_passes", "timing_issues", "adoption_status", "complete_request_log_pool")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
