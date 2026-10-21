#!/usr/bin/env python3
"""Summarize 031 natural-start A/B outputs and index exact-pixel review evidence.

Reads local files only. Uses the existing official-formula benchmark summarizer
and the conservative 031 Python-call scanner; no automatic adoption verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

from analyze_031_forks import analyze_requests
from summarize_experiment import summarize_benchmark, compare


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("baseline", "segmentation_runs")


def source(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def read_optional(path):
    return json.loads(path.read_text()) if path.is_file() else None


def add_usage(target, values):
    for key, value in values.items():
        if isinstance(value, (int, float)):
            target[key] = target.get(key, 0) + value


def analyze(root, config_path):
    manifest_path = root / "experiment-manifest.json"
    manifest = read_optional(manifest_path)
    config = manifest.get("experiment") if manifest else None
    config_source = source(manifest_path) if config else source(config_path)
    if not config:
        config = json.loads(config_path.read_text())
    expected_games = config["games"]
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "031 natural-start public short comparison; official per-game scoring formula, not hidden leaderboard",
        "review_status": "static_field_candidates_unreviewed",
        "configuration": config, "configuration_source": config_source,
        "configuration_from_run_manifest": bool(manifest and manifest.get("experiment")),
        "session_manifest": manifest, "arms": {}, "comparison": None,
        "review_candidates": [], "limitations": [
            "A single short A/B run is descriptive and does not estimate hidden-score transfer or significance.",
            "A runs/boundary AST reference is a review candidate; tool success does not prove that expression executed or corrected a pixel set.",
            "Recorded request usage, benchmark action/final tokens and analyzer token totals are separate accounting views, not additive.",
            "Timed-out requests may have unreported token cost; missing usage is not zero.",
            "Per-game elapsed times overlap and must not be summed into GPU wall time.",
            "A natural window that never reaches the relevant failure state does not test correction of that failure.",
            "031 v1 checkpoint results are separate evidence and do not validate this revised v2 interface contract."]}
    for arm in ARMS:
        arm_dir = root / arm
        benchmark_path = arm_dir / "benchmark.json"
        metadata_path = arm_dir / "arm-metadata.json"
        metadata = read_optional(metadata_path)
        session_arm = next((entry for entry in (manifest or {}).get("arms", [])
                            if entry.get("arm") == arm), None)
        item = {"benchmark_exists": benchmark_path.is_file(), "metadata": metadata,
                "session_arm": session_arm, "benchmark": None, "request_logs": [],
                "request_usage": {}, "per_game_request_usage": {}, "coverage": None}
        report["arms"][arm] = item
        if not benchmark_path.is_file():
            continue
        benchmark = summarize_benchmark(arm, benchmark_path, "local-experiment")
        item["benchmark"] = benchmark
        item["benchmark_source"] = source(benchmark_path)
        ids = [run["game_id"] for run in benchmark["runs"]]
        occurrences = Counter(ids)
        pool_equal = set(ids) == set(expected_games)
        terminal = bool(benchmark["runs"]) and all(run["state"] in {"won", "gave_up", "cancelled"} for run in benchmark["runs"])
        item["coverage"] = {
            "expected_game_count": len(expected_games), "actual_unique_game_count": len(occurrences),
            "actual_run_count": len(ids), "exact_game_ids_match": pool_equal,
            "missing_games": sorted(set(expected_games) - set(ids)),
            "unexpected_games": sorted(set(ids) - set(expected_games)),
            "runs_per_game": dict(occurrences),
            "expected_passes_per_arm": config.get("n_passes_per_arm", 1),
            "expected_run_counts_match": pool_equal and all(
                n == config.get("n_passes_per_arm", 1) for n in occurrences.values()),
            "all_runs_terminal_without_crash": terminal,
            "all_scores_available": bool(benchmark["runs"]) and all(run["score"] is not None for run in benchmark["runs"]),
            "reported_scores_match_recomputation": bool(benchmark["runs"]) and all(
                run["reported_score"] is not None and run["recomputed_score"] is not None
                and abs(run["reported_score"] - run["recomputed_score"]) < 1e-6
                for run in benchmark["runs"]),
            "benchmark_has_end_time": benchmark["end_time"] is not None,
            "configured_budget_seconds": config.get("requested_arm_seconds"),
            "observed_budget_seconds": (metadata or {}).get("budget_seconds"),
            "budget_matches_configuration": (
                metadata.get("budget_seconds") == config.get("requested_arm_seconds") if metadata else None),
            "observed_warmup_action_games": (metadata or {}).get("warmup_action_games"),
            "observed_request_deadline_enabled": (metadata or {}).get("request_deadline_enabled"),
            "metadata_status": (metadata or {}).get("status"),
            "exit_code": (metadata or {}).get("exit_code"),
            "lingering_worker_threads": (metadata or {}).get("lingering_worker_threads"),
            "forced_cpu_process_exit": (metadata or {}).get("forced_cpu_process_exit"),
            "cache_flush_http_status": (session_arm or {}).get("cache_flush_http_status"),
            "cache_flush_backend_confirmed": (session_arm or {}).get("cache_flush_backend_confirmed"),
        }
        for game_id in sorted(set(expected_games) | set(ids)):
            paths = sorted(arm_dir.glob(f"{game_id}_p*_requests.jsonl"))
            if not paths and (arm_dir / f"{game_id}_requests.jsonl").is_file():
                paths = [arm_dir / f"{game_id}_requests.jsonl"]
            game_usage = {}
            item["per_game_request_usage"][game_id] = {
                "logs_found": len(paths), "recorded_usage": None,
                "new_python_call_count": None, "runs_reference_candidates": None,
                "boundary_reference_candidates": None}
            python_count, runs_count, boundary_count = 0, 0, 0
            for path in paths:
                data = analyze_requests(path, set())
                data.update(game_id=game_id, arm=arm)
                item["request_logs"].append(data)
                add_usage(game_usage, data.get("recorded_usage", {}))
                python_count += data.get("new_python_call_count", 0)
                for call in data["new_python_calls"]:
                    fields = {ref["field"] for ref in call["static_field_candidates"]["references"]}
                    runs_count += "runs" in fields
                    boundary_count += "boundary" in fields
                    if fields:
                        report["review_candidates"].append({
                            "game_id": game_id, "arm": arm, "call_id": call["call_id"],
                            "path": str(path), "snapshot_line": call["first_snapshot_line"],
                            "analysis_step": call["analysis_step"], "snapshot_action": call["snapshot_action"],
                            "fields": sorted(fields), "tool_result_present": call["tool_result_present"],
                            "successful_tool_result": call["successful_tool_result"],
                            "references": call["static_field_candidates"]["references"],
                            "status": "unreviewed_static_candidate"})
            if paths:
                item["per_game_request_usage"][game_id].update(
                    recorded_usage=game_usage or None, new_python_call_count=python_count,
                    runs_reference_candidates=runs_count, boundary_reference_candidates=boundary_count)
            add_usage(item["request_usage"], game_usage)
        item["coverage"]["missing_request_logs"] = [game for game, info in item["per_game_request_usage"].items()
                                                        if not info["logs_found"]]
        item["coverage"]["request_log_malformed_lines"] = {
            log["path"]: log["malformed_lines"] for log in item["request_logs"] if log["malformed_lines"]}
    baseline, candidate = (report["arms"][arm]["benchmark"] for arm in ARMS)
    if baseline is not None and candidate is not None:
        comparison = compare(baseline, candidate)
        for row in comparison["games"]:
            for arm, prefix, benchmark in (("baseline", "reference", baseline),
                                            ("segmentation_runs", "candidate", candidate)):
                game = next(g for g in benchmark["games"] if g["game_id"] == row["game_id"])
                for key in ("actions", "levels_completed", "wins", "state_counts"):
                    row[prefix + "_" + key] = game[key]
                row[prefix + "_recorded_usage"] = report["arms"][arm]["per_game_request_usage"][row["game_id"]]["recorded_usage"]
            row["delta_actions"] = row["candidate_actions"] - row["reference_actions"]
            row["delta_levels_completed"] = row["candidate_levels_completed"] - row["reference_levels_completed"]
        scored = [row for row in comparison["games"] if row["delta_mean_score"] is not None]
        ranked = sorted(scored, key=lambda row: row["delta_mean_score"], reverse=True)
        comparison["score_direction_counts"] = dict(Counter(
            "positive" if row["delta_mean_score"] > 1e-9 else "negative"
            if row["delta_mean_score"] < -1e-9 else "unchanged" for row in scored))
        comparison["score_delta_descending"] = [row["game_id"] for row in ranked]
        has_positive = bool(ranked) and ranked[0]["delta_mean_score"] > 0
        comparison["sensitivity"] = {
            "largest_positive_game": ranked[0]["game_id"] if has_positive else None,
            "largest_positive_delta": ranked[0]["delta_mean_score"] if has_positive else None,
            "remaining_mean_delta": statistics.fmean(row["delta_mean_score"] for row in ranked[1:]) if has_positive and len(ranked) > 1 else None,
            "note": "Descriptive concentration check, not an alternative official score or automatic rejection rule"}
        report["comparison"] = comparison
    deltas = {row["game_id"]: row["delta_mean_score"] for row in (report["comparison"] or {}).get("games", [])}
    report["review_candidates"].sort(key=lambda row: (
        "runs" not in row["fields"], -abs(deltas.get(row["game_id"]) or 0), row["game_id"], row["arm"], row["snapshot_line"]))
    budgets = [(report["arms"][arm]["metadata"] or {}).get("budget_seconds") for arm in ARMS]
    report["paired_budget_equal"] = budgets[0] == budgets[1] if all(v is not None for v in budgets) else None
    return report


def fmt(value):
    return "缺失" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def write_reports(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 031 自然短跑对照", "", "公开短窗口的描述性比较；真实采用和纠错须人工审阅。", "",
        "| 臂 | 官方均分 | 完成关 | 全通 | 动作 | benchmark记录生成token | analyzer生成token | response usage生成token |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        item = report["arms"][arm]
        if item["benchmark"] is None:
            lines.append(f"| {arm} | 尚无benchmark | | | | | | |")
            continue
        summary = item["benchmark"]["summary"]
        values = [summary.get(key) for key in ("mean_game_score", "levels_completed", "wins", "actions",
                    "generated_tokens", "analyzer_reported_generated_tokens")]
        values.append(item["request_usage"].get("completion_tokens"))
        lines.append("| " + arm + " | " + " | ".join(fmt(v) for v in values) + " |")
    lines += ["", "三种token口径不可相加；超时未返回usage的成本未知。并发游戏耗时不能相加当作GPU会话时间。", ""]
    if report["comparison"]:
        comparison = report["comparison"]
        lines += [f"配对均分变化：**{fmt(comparison['mean_game_score_delta'])}**。", "",
            "| 游戏 | baseline分 | runs分 | 分差 | 关差 | 动作差 |", "|---|---:|---:|---:|---:|---:|"]
        for row in sorted(comparison["games"], key=lambda r: r["delta_mean_score"] or 0, reverse=True):
            values = [row.get(key) for key in ("reference_mean_score", "candidate_mean_score", "delta_mean_score",
                      "delta_levels_completed", "delta_actions")]
            lines.append("| " + row["game_id"] + " | " + " | ".join(fmt(v) for v in values) + " |")
    lines += ["", "覆盖、时限、缓存、退出与源码信息见summary.json；缺失证据不推定通过。", "",
        "人工优先看review-index.md中的runs候选，再看最大正负变化游戏。完整代码和工具返回保存在summary.json。"]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    review = ["# 031 自然轨迹人工审阅索引", "",
        "先看runs访问是否实际构造像素集合，再对齐原帧、stdout和后续行为。字段提及、函数定义、无异常返回都不足以单独证明采用。", "",
        "| 游戏 | 臂 | 字段 | request日志行 | call ID | 工具返回 | 返回码0且无error |", "|---|---|---|---:|---|---|---|"]
    for row in report["review_candidates"]:
        review.append(f"| {row['game_id']} | {row['arm']} | {','.join(row['fields'])} | {row['snapshot_line']} | {row['call_id']} | {row['tool_result_present']} | {row['successful_tool_result']} |")
    for row in report["review_candidates"]:
        review += ["", f"## {row['game_id']} · {row['arm']} · {row['call_id']}", "",
            f"原件：{row['path']}:{row['snapshot_line']}；analysis_step={row['analysis_step']}，snapshot_action={row['snapshot_action']}。", "",
            "```json", json.dumps(row["references"], ensure_ascii=False, indent=2), "```"]
    if not report["review_candidates"]:
        review += ["", "尚无静态字段候选；先核对请求日志是否完整，不能自动解释为没有调用。"]
    (output_dir / "review-index.md").write_text("\n".join(review) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/031-natural-aligned")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/031-natural-analysis")
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/031-natural-aligned.json")
    args = parser.parse_args()
    report = analyze(args.root, args.config)
    if not any(report["arms"][arm]["benchmark_exists"] for arm in ARMS):
        raise FileNotFoundError(f"No natural benchmark found below {args.root}")
    write_reports(report, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir),
        "mean_game_score_delta": (report["comparison"] or {}).get("mean_game_score_delta"),
        "review_candidate_count": len(report["review_candidates"]),
        "coverage": {arm: report["arms"][arm]["coverage"] for arm in ARMS}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
