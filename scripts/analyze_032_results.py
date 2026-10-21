#!/usr/bin/env python3
"""Read 032 local outputs and index memory delivery for human reuse review.

Reuses the existing official-formula benchmark comparison and completed Python
call reader. Delivery counters, text references and successful code are not
semantic adoption or causal score evidence. Never runs a model or environment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from analyze_031_natural import source, read_optional, add_usage, fmt
from analyze_030_results import completed_python_calls, call_excerpt, text, STATE_RE
from summarize_experiment import summarize_benchmark, compare

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("baseline", "solved_level_memory")
HEADER = "=== SOLVED LEVEL EXPERIENCE ("
FOOTER = "=== END SOLVED LEVEL EXPERIENCE ==="


def memory_windows(path):
    """Index only request snapshots; history shrink is a candidate, not a proven trim event."""
    windows, previous, seen_blocks, malformed = [], None, set(), []
    counts = Counter()
    with path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
            except ValueError:
                malformed.append(line_number)
                continue
            if record.get("event") == "response":
                counts["responses_with_usage" if isinstance(record.get("usage"), dict) else "responses_without_usage"] += 1
            if record.get("event") != "request":
                continue
            messages = record.get("messages") or []
            system = text(messages[0].get("content")) if messages else ""
            marker = system.find(HEADER)
            block = system[marker:].split(FOOTER, 1)[0] + FOOTER if marker >= 0 else ""
            first_history = json.dumps(messages[1], sort_keys=True) if len(messages) > 1 else ""
            latest_user = next((text(m.get("content")) for m in reversed(messages) if m.get("role") == "user"), "")
            state = STATE_RE.search(latest_user)
            current = {"request_line": line_number, "message_count": len(messages),
                       "history_head_hash": hashlib.sha256(first_history.encode()).hexdigest(),
                       "analysis_step": record.get("analysis_step"), "snapshot_action": record.get("action"),
                       "step": int(state.group(1)) if state else None,
                       "level": int(state.group(2)) if state else None}
            counts["requests"] += 1
            if "Before your tool call, write `Rule for level" in latest_user:
                counts["latest_user_contains_rule_instruction"] += 1
            if block:
                counts["requests_with_memory_header"] += 1
                counts["system_memory_characters_in_requests"] += len(block)
                digest = hashlib.sha256(block.encode()).hexdigest()
                reasons = []
                if not seen_blocks:
                    reasons.append("first_memory_header")
                elif digest not in seen_blocks:
                    reasons.append("new_memory_block")
                shrank = bool(previous and current["message_count"] < previous["message_count"])
                changed_head = bool(previous and current["history_head_hash"] != previous["history_head_hash"])
                if shrank:
                    reasons.append("history_message_count_decreased_with_memory")
                if changed_head:
                    reasons.append("history_head_changed_with_memory")
                if reasons:
                    windows.append({**current, "path": str(path), "reasons": reasons,
                        "previous_request_line": previous["request_line"] if previous else None,
                        "previous_message_count": previous["message_count"] if previous else None,
                        "memory_block_sha256": digest, "memory_block": block,
                        "review_status": "delivery_window_only_reuse_unreviewed"})
                seen_blocks.add(digest)
            previous = current
    return {"counts": dict(counts), "distinct_memory_blocks": len(seen_blocks),
            "windows": windows, "malformed_lines": malformed}


def read_requests(path):
    calls, origin = completed_python_calls(path)
    delivery = memory_windows(path)
    if not delivery["counts"].get("responses_with_usage"):
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cached_prompt_tokens"):
            origin["costs"][key] = None
    for window in delivery["windows"]:
        # New calls become visible in a subsequent snapshot. Existing calls in
        # the delivery snapshot are not attributed to the just-delivered block.
        following = [call for call in calls
                     if call.get("request_line_1based", 0) > window["request_line"]][:3]
        window["following_python_calls"] = []
        for call in following:
            item = call_excerpt(call)
            item["action_echoes"] = re.findall(r"^\[action\]\s*(.*)$", str(call["payload"].get("stdout") or ""), re.M)
            item["review_note"] = "Nearby new code and actual tool output; neither implies memory use or improvement."
            window["following_python_calls"].append(item)
    return {"source": origin, "python_calls_with_tool_output": len(calls), **delivery}


def analyze(root, config_path):
    manifest = read_optional(root / "experiment-manifest.json")
    config = (manifest or {}).get("experiment") or json.loads(config_path.read_text())
    expected = set(config["games"])
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "032 public short A/B; official formula on development games, not leaderboard score",
        "configuration": config, "configuration_from_manifest": bool((manifest or {}).get("experiment")),
        "session_manifest": manifest, "arms": {}, "comparison": None, "review_windows": [],
        "limitations": [
            "A recorded memory block proves delivery in a request snapshot, not correct model reuse.",
            "History length/head changes are observed candidates for eviction; inspect transcript for the exact cause.",
            "Following call source first appears after generation; missing final tool output requires transcript review.",
            "Memory-helper usage, response usage and benchmark/analyzer tokens overlap and must not be added.",
            "Whole-request latency/usage is not the marginal cost of memory; missing timeout usage is unknown.",
            "Concurrent per-game elapsed times cannot be summed into GPU wall time.",
            "No level completion/eviction/reuse opportunity means coverage is inconclusive, not a negative adoption verdict."]}
    for arm in ARMS:
        directory = root / arm
        metadata = read_optional(directory / "arm-metadata.json")
        session_arm = next((item for item in (manifest or {}).get("arms", []) if item.get("arm") == arm), None)
        item = {"metadata": metadata, "session_arm": session_arm, "benchmark": None,
                "coverage": None, "request_logs": [], "request_usage": {},
                "memory_summary": read_optional(directory / "solved-level-memory-summary.json")}
        report["arms"][arm] = item
        benchmark_path = directory / "benchmark.json"
        if benchmark_path.is_file():
            benchmark = summarize_benchmark(arm, benchmark_path, "local-experiment")
            item["benchmark"] = benchmark
            item["benchmark_source"] = source(benchmark_path)
            ids = Counter(run["game_id"] for run in benchmark["runs"])
            item["coverage"] = {"exact_game_ids_match": set(ids) == expected,
                "missing_games": sorted(expected - set(ids)), "unexpected_games": sorted(set(ids) - expected),
                "runs_per_game": dict(ids), "expected_run_counts_match": set(ids) == expected and all(
                    n == config.get("n_passes_per_arm", 1) for n in ids.values()),
                "all_terminal_without_crash": bool(ids) and all(r["state"] in {"won", "cancelled", "gave_up"} for r in benchmark["runs"]),
                "all_scores_available": bool(ids) and all(r["score"] is not None for r in benchmark["runs"]),
                "reported_scores_match_recomputation": bool(ids) and all(
                    r["reported_score"] is not None and r["recomputed_score"] is not None
                    and abs(r["reported_score"] - r["recomputed_score"]) < 1e-6 for r in benchmark["runs"]),
                "configured_budget_seconds": config.get("requested_arm_seconds"),
                "budget_matches_configuration": (metadata or {}).get("budget_seconds") == config.get("requested_arm_seconds") if metadata else None,
                "benchmark_has_end_time": benchmark["end_time"] is not None}
        for path in sorted(directory.glob("*_requests.jsonl")):
            game = path.name.split("_p", 1)[0]
            data = read_requests(path)
            data["game_id"] = game
            item["request_logs"].append(data)
            add_usage(item["request_usage"], data["source"]["costs"])
            for window in data["windows"]:
                report["review_windows"].append({"arm": arm, "game_id": game, **window})
        if item["coverage"] is not None:
            logged = {entry["game_id"] for entry in item["request_logs"]}
            item["coverage"]["missing_request_logs"] = sorted(expected - logged)
        memory = item["memory_summary"]
        if memory:
            item["memory_summary_source"] = source(directory / "solved-level-memory-summary.json")
            item["memory_review_counts"] = {
                "sessions": len(memory.get("sessions", [])),
                "fact_records": sum(len(s.get("records", [])) for s in memory.get("sessions", [])),
                "records_with_rule": sum(bool(r.get("rule")) for s in memory.get("sessions", []) for r in s.get("records", [])),
                "metrics": memory.get("metrics", {}),
                "note": "Facts/asks/refresh/delivery counters only; no semantic adoption verdict."}
    a, b = (report["arms"][name]["benchmark"] for name in ARMS)
    if a is not None and b is not None:
        result = compare(a, b)
        maps = [{g["game_id"]: g for g in bench["games"]} for bench in (a, b)]
        for row in result["games"]:
            for prefix, mapping in zip(("reference", "candidate"), maps):
                game = mapping.get(row["game_id"], {})
                for key in ("levels_completed", "actions", "wins", "generated_tokens"):
                    row[prefix + "_" + key] = game.get(key)
            for key in ("levels_completed", "actions"):
                av, bv = row["reference_" + key], row["candidate_" + key]
                row["delta_" + key] = bv - av if av is not None and bv is not None else None
        report["comparison"] = result
    budgets = [(report["arms"][a]["metadata"] or {}).get("budget_seconds") for a in ARMS]
    report["paired_budget_equal"] = budgets[0] == budgets[1] if all(x is not None for x in budgets) else None
    return report


def write_reports(report, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2) + "\n")
    lines = ["# 032 成功经验记忆短跑", "", "实际采用需审阅请求和后续行为，计数器不代表采用。", "",
             "| 臂 | 官方均分 | 完成关 | 全通 | 动作 | benchmark生成token | response生成token |", "|---|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        item = report["arms"][arm]
        stats = (item["benchmark"] or {}).get("summary", {})
        values = [stats.get(k) for k in ("mean_game_score", "levels_completed", "wins", "actions", "generated_tokens")]
        values.append(item["request_usage"].get("completion_tokens"))
        lines.append("| " + arm + " | " + " | ".join(fmt(x) for x in values) + " |")
    if report["comparison"]:
        lines += ["", f"配对平均分差：{fmt(report['comparison']['mean_game_score_delta'])}", "",
            "| 游戏 | baseline | memory | 分差 | 关差 | 动作差 |", "|---|---:|---:|---:|---:|---:|"]
        for row in report["comparison"]["games"]:
            lines.append("| " + row["game_id"] + " | " + " | ".join(fmt(row.get(k)) for k in (
                "reference_mean_score", "candidate_mean_score", "delta_mean_score", "delta_levels_completed", "delta_actions")) + " |")
    lines += ["", "交付/摘要计数：", "", "```json", json.dumps(report["arms"][ARMS[1]].get("memory_review_counts"),ensure_ascii=False,indent=2), "```", "",
              "成本口径互相重叠不可相加；超时未返回usage不是零成本。详见summary.json及review-index.md。"]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    review = ["# 032 记忆交付后的人工复用审阅", "", "首次header、新记忆块及历史缩短/头部变化只是定位线索。核对旧关事实、当前局面、随后代码与实际动作，不能把复述旧rule当成有效迁移。", ""]
    for window in report["review_windows"]:
        review += [f"## {window['arm']} / {window['game_id']} / request行{window['request_line']}", "",
            f"原件：{window['path']}:{window['request_line']}；level={window['level']}，action={window['snapshot_action']}；{', '.join(window['reasons'])}", "",
            "```text", window["memory_block"], "```"]
        for call in window["following_python_calls"]:
            review += ["", f"call {call['tool_call_id']}；首次出现行{call.get('request_line_1based')}，tool返回行{call['result_line_1based']}，level={call.get('level')}", "",
                       "```python", call["code"], "```", "```json", json.dumps({k:call.get(k) for k in ('stdout','result','error','action_echoes')},ensure_ascii=False,indent=2), "```"]
    if not report["review_windows"]:
        review += ["未发现header交付窗口；先核对日志完整性及是否发生通关/裁剪，不能直接判定模型拒绝使用。"]
    (out / "review-index.md").write_text("\n".join(review) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/032-memory-short")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/032-memory-analysis")
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/032-memory-short.json")
    args = parser.parse_args()
    report = analyze(args.root, args.config)
    if not any(item["benchmark"] for item in report["arms"].values()):
        raise FileNotFoundError(f"No benchmark found under {args.root}")
    write_reports(report,args.output_dir)
    print(json.dumps({"output_dir":str(args.output_dir),"score_delta":(report["comparison"] or {}).get("mean_game_score_delta"),"review_windows":len(report["review_windows"])},indent=2))


if __name__ == "__main__":
    main()
