#!/usr/bin/env python3
"""Analyze downloaded 034 forced checkpoint A/B evidence, without replay or calls.

Missing artifacts remain unknown. Counts of checks come only from checked_action
and prediction_unavailable events; counterexamples are retained as evidence, not
counted a second time. Completion usage comes only from program_recomputed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMES = ("ft09-0d8bbf25", "su15-1944f8ab")


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def usage_sum(values):
    totals = {}
    for usage in values:
        if isinstance(usage, dict):
            for key, value in usage.items():
                if numeric(value):
                    totals[key] = totals.get(key, 0) + value
    return totals or None


def origin(path):
    result = {"path": str(path), "exists": path.is_file()}
    if result["exists"]:
        result.update(bytes=path.stat().st_size,
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def read_json(path, problems):
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("expected object")
        return value
    except (ValueError, UnicodeError) as exc:
        problems.append({"path": str(path), "error": str(exc)})
        return None


def read_jsonl(path, problems):
    if not path.is_file():
        return None
    records = []
    for line, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("expected object")
            records.append({**record, "source_line": line})
        except ValueError as exc:
            problems.append({"path": str(path), "line": line, "error": str(exc)})
    return records


def main_requests(records):
    if records is None:
        return {"requests": None, "responses": None, "returned_usage": None,
                "errors": None, "new_python_calls": None}
    requests = [r for r in records if r.get("event") == "request"]
    responses = [r for r in records if r.get("event") == "response"]
    first = records[0].get("messages", []) if records else []
    seed_ids = {c.get("id") for m in first for c in m.get("tool_calls", [])}
    calls, results = {}, {}
    for record in records:
        for message in record.get("messages", []):
            for call in message.get("tool_calls", []):
                ident, function = call.get("id"), call.get("function", {})
                if not ident or ident in seed_ids or ident in calls or function.get("name") != "python":
                    continue
                arguments = function.get("arguments", {})
                try:
                    arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                except ValueError:
                    arguments = {"unparsed_arguments": arguments}
                calls[ident] = {"id": ident, "first_snapshot_line": record["source_line"],
                                "arguments": arguments}
            ident = message.get("tool_call_id")
            if message.get("role") == "tool" and ident not in seed_ids:
                results.setdefault(ident, message.get("content"))
    for ident, call in calls.items():
        call.update(tool_result_present=ident in results, tool_result=results.get(ident))
    return {"requests": len(requests), "responses": len(responses),
            "request_minus_response_count": len(requests) - len(responses),
            "responses_with_usage": sum(isinstance(r.get("usage"), dict) for r in responses),
            "returned_usage": usage_sum(r.get("usage") for r in responses),
            "errors": [r for r in records if r.get("error") or "error" in str(r.get("event", ""))],
            "new_python_calls": list(calls.values()),
            "note": "Calls deduplicated by ID; IDs in first snapshot excluded as prefix. Final unsnapshotted calls may be absent. Request minus response is not a proven timeout count."}


def plan_events(records):
    if records is None:
        return {"event_counts": None, "program_branch_attempts": None, "returned_usage": None,
                "prediction_checks": None, "host_plan_actions": None, "host_executions": None,
                "rejections": None, "errors": None, "extra_seconds_used": None}
    programs = [r for r in records if r.get("kind") == "program_recomputed"]
    hosts = [r for r in records if r.get("kind") == "host_plan_execution"]
    checks = Counter(r.get("status") for r in records if r.get("kind") == "checked_action")
    # prediction_unavailable is a separate pre-action failure, not a checked action.
    checks["unknown"] += sum(r.get("kind") == "prediction_unavailable" for r in records)
    checks = {status: checks[status] for status in ("match", "mismatch", "unknown", "boundary", "not_executed")}
    seconds = [r.get("extra_seconds_used") for r in hosts if numeric(r.get("extra_seconds_used"))]
    return {"event_counts": dict(Counter(r.get("kind") for r in records)),
            "program_branch_attempts": len(programs),
            "program_returned_responses": sum("response" in r for r in programs),
            "request_send_uncertain_attempts": sum("response" not in r and "before request" not in str(r.get("error", "")) for r in programs),
            "program_responses_with_usage": sum(isinstance(r.get("usage"), dict) for r in programs),
            "returned_usage": usage_sum(r.get("usage") for r in programs),
            "prediction_checks": checks,
            "checked_actual_actions": sum(r.get("actual_actions", 0) for r in records if r.get("kind") == "checked_action"),
            "unchecked_actual_actions": sum(r.get("actual_actions", 0) for r in records if r.get("kind") == "unchecked_action"),
            "host_plan_actions": sum(r.get("actual_actions", 0) for r in hosts),
            "host_executions": hosts,
            "rejections": [r for r in programs if r.get("status") == "rejected"],
            "errors": [r for r in records if r.get("error")],
            "extra_seconds_used": max(seconds) if seconds else None,
            "programs": programs,
            "counterexamples": [r for r in records if r.get("kind") == "counterexample"],
            "note": "program_branch_attempts counts program_recomputed events; errors before completion can leave actual request sending uncertain. Host actions sum top-level host_plan_execution events only. Never add recursive forced_branch actions. Usage sums program_recomputed only. extra_seconds_used is cumulative max and may omit rejected final branch time; patch snapshot is authoritative when available."}


def analyze(root):
    problems, sources = [], []
    manifest_path = root / "experiment-manifest.json"
    manifest = read_json(manifest_path, problems)
    sources.append(origin(manifest_path))
    arms = {}
    for arm in ("A", "B"):
        folder = root / f"executable_plan_{arm}"
        arm_entry = next((entry for entry in (manifest or {}).get("arms", [])
                          if entry.get("arm") == f"executable_plan_{arm}"), {})
        execution_status = ("completed" if arm_entry.get("exit_code") == 0 else
                            "not_started" if arm_entry.get("cache_flush_error") and (manifest or {}).get("status") == "failed" else
                            "unknown")
        summary_path = folder / "executable-plan-forks.json"
        summary = read_json(summary_path, problems)
        sources.append(origin(summary_path))
        games = {}
        for game in GAMES:
            result_path = folder / f"{game}-{arm}.json"
            result = read_json(result_path, problems)
            if result is None and summary:
                result = next((r for r in summary.get("forks", []) if r.get("game_id") == game), None)
            request_path = folder / f"{game}_{arm}_requests.jsonl"
            event_paths = sorted((folder / "artifacts").glob(f"{game}_{arm}_*_executable-plan.jsonl"))
            if len(event_paths) > 1:
                problems.append({"game": game, "arm": arm, "error": "multiple event logs; refusing ambiguous merge"})
            event_path = event_paths[0] if len(event_paths) == 1 else folder / "artifacts" / f"{game}_{arm}_runtime-state_executable-plan.jsonl"
            requests = main_requests(read_jsonl(request_path, problems))
            events = plan_events(read_jsonl(event_path, problems))
            sources.extend(origin(p) for p in (result_path, request_path, event_path))
            if result and isinstance(result.get("continuation_actions"), list):
                if len(result["continuation_actions"]) != result.get("continuation_action_count"):
                    problems.append({"game": game, "arm": arm, "error": "continuation action list/count mismatch"})
            complete = result is not None and request_path.is_file() and (arm == "A" or len(event_paths) == 1)
            games[game] = {"status": "complete" if complete else "partial" if result or request_path.is_file() or event_paths else "not_started" if execution_status == "not_started" else "awaiting",
                "result": result, "added_levels": (result or {}).get("added_levels"),
                "continuation_action_count": (result or {}).get("continuation_action_count"),
                "elapsed_seconds": (result or {}).get("elapsed_seconds"),
                "actions_during_forced_branch": (result or {}).get("actions_during_forced_branch"),
                "main_requests": requests, "plan_events": events,
                "known_disjoint_response_usage": usage_sum([requests["returned_usage"], events["returned_usage"]]),
                "known_usage_complete_sources": request_path.is_file() and (arm == "A" or len(event_paths) == 1)}
        arms[arm] = {"execution_status": execution_status, "session_arm_entry": arm_entry,
            "fork_summary": summary, "games": games,
            "known_main_returned_usage": usage_sum(g["main_requests"]["returned_usage"] for g in games.values()),
            "known_extra_returned_usage": usage_sum(g["plan_events"]["returned_usage"] for g in games.values()),
            "total_added_levels": sum(g["added_levels"] for g in games.values()) if all(numeric(g["added_levels"]) for g in games.values()) else None,
            "total_continuation_actions": sum(g["continuation_action_count"] for g in games.values()) if all(numeric(g["continuation_action_count"]) for g in games.values()) else None,
            "extra_seconds_patch_snapshot": ((summary or {}).get("patch") or {}).get("extra_seconds")}
    comparisons = {}
    for game in GAMES:
        a, b = (arms[arm]["games"][game] for arm in ("A", "B"))
        comparisons[game] = {"B_minus_A_" + key: b[key] - a[key] if numeric(a[key]) and numeric(b[key]) else None
                             for key in ("added_levels", "continuation_action_count", "elapsed_seconds")}
        ra, rb = a.get("result") or {}, b.get("result") or {}
        comparisons[game]["restored_equal"] = {key: ra[key] == rb[key] if key in ra and key in rb else None
            for key in ("grid_sha256", "messages_sha256", "functions_sha256", "branch_source_code_sha256", "prefix_recorded_actions")}
    states = [g["status"] for a in arms.values() for g in a["games"].values()]
    summaries_present = all(a["fork_summary"] is not None for a in arms.values())
    status = "complete" if all(s == "complete" for s in states) and manifest and summaries_present else "awaiting" if all(s == "awaiting" for s in states) and not manifest else "partial"
    if problems and status == "complete":
        status = "partial"
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "status": status,
        "scope": "034 forced same-prefix diagnostic only; no natural coverage, full-pool improvement or hidden-score claim",
        "session_manifest": manifest, "sources": sources, "parse_or_consistency_problems": problems,
        "arms": arms, "paired_comparisons": comparisons,
        "session_cost": {"elapsed_seconds": (manifest or {}).get("elapsed_seconds"),
            "session_gpu_hours_wall_clock": manifest["elapsed_seconds"] / 3600 if manifest and numeric(manifest.get("elapsed_seconds")) else None,
            "model_ready_seconds": (manifest or {}).get("model_ready_seconds"),
            "gpu_sampling": (manifest or {}).get("gpu_sampling"),
            "note": "Session hours are elapsed allocation time, not GPU utilization or billed cost. Games run concurrently; do not sum per-game elapsed times into session cost. Branch time is inside continuation."},
        "limitations": ["Missing or malformed sources imply unknown/partial values, never zero-result evidence.",
            "Returned usage is known cost only; failed or timed-out requests can have unreturned usage.",
            "Pixel matches and accepted plans do not certify task semantics or causal improvement.",
            "final_score includes the restored prefix; paired added_levels is the continuation measure.",
            "checked_action and counterexample describe the same failed prediction; counted once.",
            "forced_branch.actual_actions includes recursive repair; host event totals are a separate cross-check, never added to that aggregate."]}


def write(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    session = report.get("session_manifest") or {}
    lines = ["# 034 强制切点诊断", "", f"产物状态：{report['status']}；会话状态：{session.get('status', 'unknown')}。仅比较相同前缀续跑；不能称为自然覆盖或full-pool提升。", "",
             f"会话错误：`{session.get('error')}`。", "",
             "| arm | game | status | 新增关 | 续跑动作 | host计划动作 | match/mismatch/unknown |", "|---|---|---|---|---|---|---|"]
    details = []
    review = ["# 034 已保存程序与实际行为审阅", "", "仅静态展示已保存产物，不执行模型代码。缺项为null；验收通过不等于任务语义正确。"]
    for arm, data in report["arms"].items():
        for game, value in data["games"].items():
            event = value["plan_events"]
            checks = event["prediction_checks"]
            check_text = "/".join(str(checks[k]) for k in ("match", "mismatch", "unknown")) if checks else "null"
            lines.append(f"| {arm} | {game} | {value['status']} | {value['added_levels']} | {value['continuation_action_count']} | {event['host_plan_actions']} | {check_text} |")
            details.extend(["", f"{arm}/{game} 主usage：`{json.dumps(value['main_requests']['returned_usage'])}`；额外usage：`{json.dumps(event['returned_usage'])}`；拒收：`{len(event['rejections']) if event['rejections'] is not None else None}`。"])
            review.extend(["", f"## {arm}/{game}", "", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```"])
    lines.extend(details)
    lines.extend(["", "配对差值：", "```json", json.dumps(report["paired_comparisons"], ensure_ascii=False, indent=2), "```", "",
                  "成本：", "```json", json.dumps(report["session_cost"], ensure_ascii=False, indent=2), "```", "",
                  "详见summary.json与review.md。额外请求usage只取program_recomputed；主response usage独立。失配不重复计数，递归forced_branch与host_plan_execution动作不相加。"])
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    (output_dir / "review.md").write_text("\n".join(review) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/034-plan-diagnostic")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/034-analysis")
    args = parser.parse_args()
    report = analyze(args.root)
    write(report, args.output_dir)
    print(json.dumps({"status": report["status"], "output_dir": str(args.output_dir),
                      "paired_comparisons": report["paired_comparisons"],
                      "problems": report["parse_or_consistency_problems"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
