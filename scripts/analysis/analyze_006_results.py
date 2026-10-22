#!/usr/bin/env python3
"""Read completed 006 A/B outputs and derive comparison diagnostics; no GPU.

Manual use: python3 scripts/analysis/analyze_006_results.py --output-dir experiments/006-analysis
Raw benchmark, metadata and intervention outputs are never rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_005_results import audit_timing, source
from summarize_experiment import summarize_benchmark


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def exposures(snapshot):
    grouped = defaultdict(list)
    for call in snapshot.get("calls", []):
        game_id = call["run_ref"].rsplit("_p", 1)[0]
        grouped[game_id].append(call)
    result = {}
    for game_id, calls in grouped.items():
        attachment_calls = [c for c in calls if c.get("attached")]
        result[game_id] = {
            "observed_calls": len(calls),
            "attachment_calls": len(attachment_calls),
            **{key: sum(c.get(key, 0) for c in calls) for key in (
                "new_executed_actions", "captured_transient_events", "eligible_earlier_events",
                "attached_events", "omitted_events", "added_chars")},
            "attachment_levels": dict(sorted(Counter(c["after_level"] for c in attachment_calls).items())),
            "status_counts": dict(Counter(c.get("status", "unknown") for c in calls)),
            "max_added_chars": max((c.get("added_chars", 0) for c in calls), default=0),
            "first_attachment": {key: attachment_calls[0].get(key) for key in (
                "before_step", "before_level", "after_step", "after_level", "attached_action_nums")}
                if attachment_calls else None,
        }
    return result


def render(result):
    lines = ["# 006 同池 A/B 结果", "",
             "12个已知公开诊断游戏，各1遍；baseline先运行。以下为描述性对比，不是显著性或隐藏榜收益。", "",
             "| 游戏 | A分数 | B分数 | Δ分数 | 关卡A→B | tokens A→B（analyzer） | 动作A→B | B附加次数/事件 |",
             "|---|---:|---:|---:|---|---:|---:|---:|"]
    for row in result["games"]:
        lines.append(f"| {row['game_id']} | {row['baseline']['score']:.4f} | {row['transient_history']['score']:.4f} | {row['score_delta']:+.4f} | {row['baseline']['levels_completed']}→{row['transient_history']['levels_completed']}/{row['baseline']['number_of_levels']} | {row['baseline']['analyzer_reported_generated_tokens']:,}→{row['transient_history']['analyzer_reported_generated_tokens']:,} | {row['baseline']['actions']}→{row['transient_history']['actions']} | {row['exposure']['attachment_calls']}/{row['exposure']['attached_events']} |")
    lines += ["", "分差保留所有12游戏。sc25+ar25对均值贡献为 "
              f"{result['sensitivity']['sc25_ar25_mean_contribution']:.6f}；移除两者后的差值 "
              f"{result['sensitivity']['without_sc25_ar25_mean_delta']:.6f} 仅作集中度说明，不能替代总结果。", "",
              "## 停止和预算", "",
              "| 臂 | 请求预算秒 | benchmark秒 | 截止后动作 | 截止后关卡 | 尾部timeout日志 | 记账tokens | analyzer tokens | 未归属tokens |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, value in result["arms"].items():
        s, t = value["summary"], value["timing"]
        lines.append(f"| {arm} | {t['budget_seconds']} | {s['benchmark_elapsed_seconds']:.3f} | {t['post_deadline_actions']} | {t['post_deadline_levels']} | {t['timeout_log_count']} | {s['generated_tokens']:,} | {s['analyzer_reported_generated_tokens']:,} | {s['unattached_generated_tokens']:,} |")
    lines += ["", "## 解释边界", ""] + [f"- {note}" for note in result["notes"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("runs/006-transient-history"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    names = ("baseline", "transient_history")
    sources = [source(args.root / "experiment-manifest.json")]
    manifest = read(args.root / "experiment-manifest.json")
    arms = {}
    metadata = {}
    run_maps = {}
    for arm in names:
        directory = args.root / arm
        benchmark_path = directory / "benchmark.json"
        summary = summarize_benchmark(arm, benchmark_path, "local-experiment")
        benchmark = read(benchmark_path)
        meta = read(directory / "arm-metadata.json")
        snapshot = read(directory / "transient-history.json")
        timing = audit_timing(benchmark, meta)
        log = (directory / "run.log").read_text()
        sources.extend(source(directory / file) for file in (
            "benchmark.json", "arm-metadata.json", "transient-history.json", "run.log"))
        reset_by_game = {r["game_id"]: sum(h["action"].get("id") == "RESET" for h in r["history"])
                         for r in benchmark["game_runs"]}
        ledger = exposures(snapshot)
        arms[arm] = {
            "summary": summary["summary"],
            "timing": {"budget_seconds": meta["budget_seconds"],
                "post_deadline_actions": sum(t["post_deadline_action_count"] for t in timing["runs"].values()),
                "post_deadline_levels": sum(len(t["post_deadline_completed_levels"]) for t in timing["runs"].values()),
                "timeout_log_count": log.count("analyzer request timed out"),
                "timeout_read_seconds": [float(v) for v in re.findall(r"read timeout=([0-9.]+)", log)],
                "benchmark_wall_seconds": meta["benchmark_wall_seconds"],
                "arm_wall_seconds": meta["wall_seconds"],
                "soft_deadline_fired": meta["soft_deadline_fired"],
                "forced_cpu_process_exit": meta["forced_cpu_process_exit"],
                "lingering_worker_threads": meta["lingering_worker_threads"],
                "exit_code": meta["exit_code"]},
            "reset_actions": sum(reset_by_game.values()),
            "intervention": {key: value for key, value in snapshot.items() if key != "calls"},
            "ledger_status_counts": dict(Counter(c.get("status") for c in snapshot.get("calls", []))),
            "per_game_exposure": ledger,
            "warnings": summary["warnings"],
        }
        metadata[arm] = meta
        run_maps[arm] = {r["game_id"]: {**r, **timing["runs"][r["game_id"]],
                                           "reset_actions": reset_by_game[r["game_id"]]}
                         for r in summary["runs"]}
    left, right = (run_maps[arm] for arm in names)
    if left.keys() != right.keys():
        raise ValueError("A/B game IDs differ; do not silently compare a subset")
    rows = []
    for game_id in metadata["baseline"]["game_ids"]:
        a, b = left[game_id], right[game_id]
        exposure = arms["transient_history"]["per_game_exposure"][game_id]
        rows.append({"game_id": game_id, "baseline": a, "transient_history": b,
            "score_delta": b["score"] - a["score"],
            "ceiling_delta": b["completion_ceiling"] - a["completion_ceiling"],
            "levels_delta": b["levels_completed"] - a["levels_completed"],
            "analyzer_tokens_delta": b["analyzer_reported_generated_tokens"] - a["analyzer_reported_generated_tokens"],
            "actions_delta": b["actions"] - a["actions"],
            "mean_score_contribution": (b["score"] - a["score"]) / len(left),
            "exposure": exposure,
            "ledger_actions_plus_resets_match": exposure["new_executed_actions"] + b["reset_actions"] == b["actions"]})
    total_delta = sum(r["score_delta"] for r in rows)
    for row in rows:
        row["leave_one_game_out_mean_delta"] = (total_delta - row["score_delta"]) / (len(rows) - 1)
    selected = [r for r in rows if r["game_id"].startswith(("sc25-", "ar25-"))]
    fields = ("game_ids", "game_order_sha256", "operation_mode", "budget_seconds", "normalized_budget_seconds",
              "active_streams", "concurrency", "n_passes", "warmup_action_games", "analyzer_timeout_seconds",
              "source_sha256", "environment")
    serve_log = (args.root / "serve.log").read_text()
    result = {
        "schema_version": 1, "sources": sources, "arms": arms, "games": rows,
        "overall_delta": {"score": total_delta / len(rows),
            "ceiling": statistics.fmean(r["ceiling_delta"] for r in rows),
            "completed_levels": sum(r["levels_delta"] for r in rows),
            "wins": arms["transient_history"]["summary"]["wins"] - arms["baseline"]["summary"]["wins"],
            "analyzer_tokens": sum(r["analyzer_tokens_delta"] for r in rows),
            "actions": sum(r["actions_delta"] for r in rows),
            "score_better_equal_worse": {"better": sum(r["score_delta"] > 1e-8 for r in rows),
                "equal": sum(abs(r["score_delta"]) <= 1e-8 for r in rows),
                "worse": sum(r["score_delta"] < -1e-8 for r in rows)},
            "levels_better_equal_worse": {"better": sum(r["levels_delta"] > 0 for r in rows),
                "equal": sum(r["levels_delta"] == 0 for r in rows),
                "worse": sum(r["levels_delta"] < 0 for r in rows)}},
        "sensitivity": {"sc25_ar25_mean_contribution": sum(r["score_delta"] for r in selected) / len(rows),
            "without_sc25_ar25_mean_delta": (total_delta - sum(r["score_delta"] for r in selected)) / (len(rows) - len(selected))},
        "comparability": {"equal_metadata_fields": {field: metadata["baseline"].get(field) == metadata["transient_history"].get(field) for field in fields},
            "distinct_cpu_pids": metadata["baseline"]["pid"] != metadata["transient_history"]["pid"],
            "successful_cache_flush_log_count": serve_log.count("Cache flushed successfully!"),
            "arm_order": manifest["experiment"]["arm_order"],
            "source_hashes": manifest["source_hashes"]},
        "session": {key: manifest.get(key) for key in (
            "elapsed_seconds", "model_ready_seconds", "status", "gpu_server_stopped")},
        "notes": [
            "同12游戏、相同顺序和3482秒预算是本轮内部可比条件；每组仅1遍且共享10流调度，固定A先B后，不是独立随机配对重复。",
            "不与005全25或003的16游戏均值直接比较，不以删去回退游戏后的均值替代总结果。",
            "tokens保留history+final与analyzer自报两种口径；总输出tokens近等不代表逐游戏计算机会、input/prefill或真实GPU秒完全相同。",
            "附加次数不等于模型注意、采用或提分；零附加游戏仍可能受共享调度、随机轨迹和额外观测读取开销影响。",
            "曝光分组由实际轨迹产生，是事后观测，不能把有/无附加游戏比较当作随机对照或剂量因果估计。",
            "cancelled结合deadline元数据表示预算终止上下文；动作层死亡/RESET与程序crash分开。",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "comparison.md").write_text(render(result))
    print(json.dumps(result["overall_delta"], ensure_ascii=False))
    print(json.dumps(result["sensitivity"], ensure_ascii=False))
    for arm, value in arms.items():
        print(arm, json.dumps(value["timing"], ensure_ascii=False))


if __name__ == "__main__":
    main()
