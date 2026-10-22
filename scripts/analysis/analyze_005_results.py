#!/usr/bin/env python3
"""Manually compare the completed 005 public baseline with 003; no execution.

Uses the shared benchmark summarizer and writes only derived JSON/Markdown.
Example: python3 scripts/analysis/analyze_005_results.py --output-dir experiments/005-analysis
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from summarize_experiment import aggregate, summarize_benchmark


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(path):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def group(runs, overall_tokens):
    result = aggregate(runs)
    tokens = result["analyzer_reported_generated_tokens"]
    result["analyzer_token_share"] = tokens / overall_tokens if tokens is not None and overall_tokens else None
    result["mean_analyzer_tokens_per_game"] = tokens / len(runs) if tokens is not None and runs else None
    result["won_game_ids"] = sorted(r["game_id"] for r in runs if r["state"] == "won")
    result["game_ids"] = sorted(r["game_id"] for r in runs)
    return result


def audit_timing(benchmark, metadata):
    start = datetime.fromisoformat(benchmark["start_time"])
    deadline = (datetime.fromisoformat(metadata["soft_end_local"]) - start).total_seconds()
    rows = {}
    for run in benchmark["game_runs"]:
        history = run["history"]
        offset = (datetime.fromisoformat(run["started_at"]) - start).total_seconds()
        timestamps = [offset + item["wallclock_seconds"] for item in history]
        cursor = 0
        completions = []
        for i in range(run["levels_completed"]):
            cursor += run["actions_per_level"][i]
            completions.append({"level": i + 1, "at_benchmark_second": timestamps[cursor - 1]})
        final = offset + run["final_wallclock_seconds"]
        last = timestamps[-1] if timestamps else offset
        rows[run["game_id"]] = {
            "start_benchmark_second": offset,
            "last_action_benchmark_second": last,
            "finish_benchmark_second": final,
            "last_action_to_finish_seconds": final - last,
            "post_deadline_action_count": sum(t > deadline for t in timestamps),
            "post_deadline_completed_levels": [item["level"] for item in completions if item["at_benchmark_second"] > deadline],
            "level_completion_times": completions,
            "actions_on_completed_levels": sum(run["actions_per_level"][:run["levels_completed"]]),
            "actions_on_uncompleted_levels": sum(run["actions_per_level"][run["levels_completed"]:]),
        }
    return {"deadline_benchmark_second": deadline, "runs": rows}


def display(value, decimals=3):
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{decimals}f}"


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def token_intervals(raw, summarized):
    """Observed token accumulation before each action; no trajectory code runs."""
    summaries = {r["game_id"]: r for r in summarized}
    rows, intervals = [], []
    for run in raw["game_runs"]:
        summary = summaries[run["game_id"]]
        per_run = []
        index = 0
        for level, count in enumerate(run["actions_per_level"], 1):
            for level_action in range(1, count + 1):
                item = run["history"][index]
                start = run["history"][index - 1]["wallclock_seconds"] if index else 0
                per_run.append({"game_id": run["game_id"], "game_state": run["state"],
                                "level": level, "level_eventually_completed": level <= run["levels_completed"],
                                "kind": "before_action", "history_index": index,
                                "action_number": index + 1, "action_number_in_level": level_action,
                                "tokens": item["generated_tokens"],
                                "elapsed_seconds": item["wallclock_seconds"] - start})
                index += 1
        tail_tokens = (summary["final_generated_tokens"] + summary["unattached_generated_tokens"]
                       if summary["unattached_generated_tokens"] is not None else None)
        tail = {"game_id": run["game_id"], "game_state": run["state"],
                "level": min(run["levels_completed"] + 1, run["number_of_levels"]),
                "level_eventually_completed": run["state"] == "won",
                "kind": "terminal_tail", "tokens": tail_tokens,
                "elapsed_seconds": summary["run_elapsed_seconds"] - summary["last_action_seconds"]}
        rows.append({"game_id": run["game_id"], "state": run["state"],
                     "max_before_action_tokens": max((i["tokens"] for i in per_run), default=0),
                     "tail_tokens": tail_tokens,
                     "largest_before_action_intervals": sorted(per_run, key=lambda i: i["tokens"], reverse=True)[:3],
                     "tail": tail})
        intervals.extend(per_run)
        intervals.append(tail)
    positive = [i["tokens"] for i in intervals if i["tokens"] is not None and i["tokens"] > 0]
    thresholds = {}
    for threshold in (24000, 32000, 24576, 32768):
        hit = [i for i in intervals if i["tokens"] is not None and i["tokens"] >= threshold]
        thresholds[str(threshold)] = {
            "observed_interval_count": len(hit),
            "game_count": len({i["game_id"] for i in hit}),
            "before_action_count": sum(i["kind"] == "before_action" for i in hit),
            "tail_count": sum(i["kind"] == "terminal_tail" for i in hit),
            "won_game_ids": sorted({i["game_id"] for i in hit if i["game_state"] == "won"}),
            "before_action_on_eventually_completed_level_count": sum(i["kind"] == "before_action" and i["level_eventually_completed"] for i in hit),
            "intervals": hit,
        }
    return {"source": "benchmark history.generated_tokens per action plus final/unattached analyzer tail",
            "notes": [
                "24k/32k mean 24000/32000 here; 24576/32768 are additionally reported to remove unit ambiguity.",
                "An action-attached count approximates generation accumulated since the prior environment action, including the initial interval. Batch actions often have zero counts.",
                "The tail is analyzer-reported generation not yet attached to an action (recorded final + residual); it is not an extra sum to add to analyzer totals.",
                "These are offline threshold crossings on the observed baseline, not actual feedback firings or measured false positives. Completion after a large interval does not establish whether interrupting it helps or hurts.",
                "Intervals include queue and Python computation in elapsed time; tokens alone cannot identify why no environment action occurred. Alias/retained-code inspection requires request traces.",
            ],
            "positive_interval_distribution": {"count": len(positive), "p50": percentile(positive, .5),
                "p75": percentile(positive, .75), "p90": percentile(positive, .9),
                "p95": percentile(positive, .95), "p99": percentile(positive, .99), "max": max(positive)},
            "per_game": rows, "thresholds": thresholds}


def markdown(result):
    lines = ["# 005 与 003 的公开基线描述性比较", "",
             "005 为 25 游戏池，003 为 16 游戏池；调度池、顺序和有效总时长不同。不是同池 A/B，也不能把差值归因于 RESET 修复或策略提升。", "",
             "## 分组", "",
             "| 运行 / 组 | 游戏 | 分数均值 | 覆盖上限 | 完成关卡 | 全通 | 记账 tokens | Analyzer tokens |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, value in result["groups"].items():
        lines.append(f"| {name} | {value['run_count']} | {display(value['mean_score'])} | {display(value['mean_completion_ceiling'])} | {value['levels_completed']}/{value['levels_available']} | {value['wins']} | {display(value['generated_tokens'])} | {display(value['analyzer_reported_generated_tokens'])} |")
    lines += ["", "## 全部游戏", "",
              "记账 tokens 是 action history + final；Analyzer 是 solver_note 自报累计。尾部无动作秒数包括推理、工具和调度等待，不能等同 GPU 空转。", "",
              "| 游戏 | 分组 | 005 分数 | 003 分数 | Δ 分数 | 完成关卡 003→005 | 005 上限 | Analyzer 003→005 | 未归属 tokens | 最后动作到收尾秒 |",
              "|---|---|---:|---:|---:|---|---:|---:|---:|---:|"]
    for row in result["games"]:
        old_levels = str(row["previous_levels_completed"]) if row["previous_levels_completed"] is not None else "—"
        lines.append(f"| {row['game_id']} | {row['group']} | {display(row['score'])} | {display(row['previous_score'])} | {display(row['score_delta'])} | {old_levels}→{row['levels_completed']}/{row['number_of_levels']} | {display(row['completion_ceiling'])} | {display(row['previous_analyzer_tokens'])}→{display(row['analyzer_reported_generated_tokens'])} | {display(row['unattached_generated_tokens'])} | {display(row['last_action_to_finish_seconds'], 1)} |")
    lines += ["", "## 动作与 token 分配", "",
              "| 005 分组 | 游戏 | 完成关卡 | Analyzer tokens | 占全池 tokens | 已完成关卡动作 | 未完成关卡动作 |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for name, value in result["allocation_groups"].items():
        lines.append(f"| {name} | {value['game_count']} | {value['levels_completed']} | {display(value['analyzer_tokens'])} | {value['analyzer_token_share']:.2%} | {value['actions_on_completed_levels']} | {value['actions_on_uncompleted_levels']} |")
    lines += ["", "## 数据边界", ""] + [f"- {note}" for note in result["notes"]]
    lines += ["", "## 无动作 token 间隔（阈值定位，非效果测试）", "",
              "| 游戏 | 状态 | 最大动作前间隔 tokens | 最后动作后 tokens |",
              "|---|---|---:|---:|"]
    for value in result["token_intervals"]["per_game"]:
        lines.append(f"| {value['game_id']} | {value['state']} | {display(value['max_before_action_tokens'])} | {display(value['tail_tokens'])} |")
    lines += ["", "24k/32k 在本报告明确指 24,000/32,000；还保存 24,576/32,768 供核对。", ""]
    for cutoff in ("24000", "32000"):
        value = result["token_intervals"]["thresholds"][cutoff]
        lines.append(f"- {cutoff}: 命中 {value['observed_interval_count']} 个历史间隔、{value['game_count']} 个游戏；其中最终全通游戏 {len(value['won_game_ids'])} 个。发生在后来已完成关卡上的动作前间隔 {value['before_action_on_eventually_completed_level_count']} 个。不能将这些历史交叉点当作真实反馈触发或收益。")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, default=Path("runs/005-full-baseline"))
    parser.add_argument("--previous", type=Path, default=Path("runs/003-goal-evidence-ab"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    current_path = args.current / "baseline/benchmark.json"
    previous_path = args.previous / "baseline/benchmark.json"
    current = summarize_benchmark("005", current_path, "local-experiment")
    previous = summarize_benchmark("003", previous_path, "local-experiment")
    raw_current = read(current_path)
    cm = read(args.current / "baseline/arm-metadata.json")
    pm = read(args.previous / "baseline/arm-metadata.json")
    manifest = read(args.current / "experiment-manifest.json")
    prior = {r["game_id"]: r for r in previous["runs"]}
    shared = [r for r in current["runs"] if r["game_id"] in prior]
    added = [r for r in current["runs"] if r["game_id"] not in prior]
    total_tokens = current["summary"]["analyzer_reported_generated_tokens"]
    timing = audit_timing(raw_current, cm)
    rows = []
    for now in current["runs"]:
        before = prior.get(now["game_id"])
        rows.append({**now, **timing["runs"][now["game_id"]],
                     "group": "原16" if before else "新增9",
                     "previous_score": before["score"] if before else None,
                     "score_delta": now["score"] - before["score"] if before else None,
                     "previous_levels_completed": before["levels_completed"] if before else None,
                     "levels_delta": now["levels_completed"] - before["levels_completed"] if before else None,
                     "previous_analyzer_tokens": before["analyzer_reported_generated_tokens"] if before else None,
                     "analyzer_tokens_delta": now["analyzer_reported_generated_tokens"] - before["analyzer_reported_generated_tokens"] if before else None,
                     "analyzer_token_share": now["analyzer_reported_generated_tokens"] / total_tokens,
                     "unattached_token_fraction": now["unattached_generated_tokens"] / now["analyzer_reported_generated_tokens"] if now["analyzer_reported_generated_tokens"] else None})
    common_ids = {r["game_id"] for r in shared}
    groups = {
        "005 全25": group(current["runs"], total_tokens),
        "005 原16": group(shared, total_tokens),
        "005 新增9": group(added, total_tokens),
        "003 原16": group([r for r in previous["runs"] if r["game_id"] in common_ids], previous["summary"]["analyzer_reported_generated_tokens"]),
    }
    allocation = {}
    for name, selected in {
        "完整通关": [r for r in rows if r["state"] == "won"],
        "预算取消": [r for r in rows if r["state"] == "cancelled"],
        "完成0–1关": [r for r in rows if r["levels_completed"] <= 1],
        "原16": [r for r in rows if r["group"] == "原16"],
        "新增9": [r for r in rows if r["group"] == "新增9"],
    }.items():
        tokens = sum(r["analyzer_reported_generated_tokens"] for r in selected)
        allocation[name] = {"game_count": len(selected), "game_ids": [r["game_id"] for r in selected],
                            "levels_completed": sum(r["levels_completed"] for r in selected),
                            "analyzer_tokens": tokens, "analyzer_token_share": tokens / total_tokens,
                            "actions_on_completed_levels": sum(r["actions_on_completed_levels"] for r in selected),
                            "actions_on_uncompleted_levels": sum(r["actions_on_uncompleted_levels"] for r in selected)}
    common_rows = [r for r in rows if r["previous_score"] is not None]
    delta = sum(r["score_delta"] for r in common_rows)
    for row in common_rows:
        row["mean_common_score_contribution"] = row["score_delta"] / len(common_rows)
        row["leave_game_out_mean_delta"] = (delta - row["score_delta"]) / (len(common_rows) - 1)
    env_differences = {key: {"003": pm["environment"].get(key), "005": cm["environment"].get(key)}
                       for key in pm["environment"].keys() | cm["environment"].keys()
                       if pm["environment"].get(key) != cm["environment"].get(key)}
    log = (args.current / "baseline/run.log").read_text()
    result = {
        "schema_version": 1,
        "sources": [source(p) for p in (current_path, previous_path,
                    args.current / "baseline/arm-metadata.json", args.previous / "baseline/arm-metadata.json",
                    args.current / "experiment-manifest.json", args.current / "baseline/run.log")],
        "groups": groups, "games": rows, "allocation_groups": allocation,
        "common16_comparison": {
            "mean_score_delta": delta / len(common_rows),
            "mean_ceiling_delta": groups["005 原16"]["mean_completion_ceiling"] - groups["003 原16"]["mean_completion_ceiling"],
            "levels_delta": groups["005 原16"]["levels_completed"] - groups["003 原16"]["levels_completed"],
            "analyzer_token_delta": groups["005 原16"]["analyzer_reported_generated_tokens"] - groups["003 原16"]["analyzer_reported_generated_tokens"],
            "score_improved": sum(r["score_delta"] > 1e-8 for r in common_rows),
            "score_equal": sum(abs(r["score_delta"]) <= 1e-8 for r in common_rows),
            "score_declined": sum(r["score_delta"] < -1e-8 for r in common_rows),
            "level_improved": sum(r["levels_delta"] > 0 for r in common_rows),
            "level_equal": sum(r["levels_delta"] == 0 for r in common_rows),
            "level_declined": sum(r["levels_delta"] < 0 for r in common_rows),
        },
        "comparability": {"pool_sizes": {"003": len(previous['runs']), "005": len(current['runs'])},
                          "budget_seconds": {"003": pm["budget_seconds"], "005": cm["budget_seconds"]},
                          "normalized_budget_seconds_per_game": {"003": pm["budget_seconds"] / len(previous["runs"]), "005": cm["budget_seconds"] / len(current["runs"])},
                          "environment_differences": env_differences,
                          "tool_agent_source_equal": cm["source_sha256"]["tool_agent.py"] == pm["source_sha256"]["tool_agent.py"],
                          "benchmark_initial_source_equal": cm["source_sha256"]["benchmark_initial.pkl"] == pm["source_sha256"]["benchmark_initial.pkl"],
                          "previous_only_ids": sorted(prior.keys() - common_ids)},
        "timing": {"requested_budget_seconds": cm["budget_seconds"],
                   "benchmark_json_elapsed_seconds": current["summary"]["benchmark_elapsed_seconds"],
                   "benchmark_wall_seconds": cm["benchmark_wall_seconds"],
                   "runner_wall_seconds": manifest["elapsed_seconds"],
                   "model_ready_seconds": manifest["model_ready_seconds"],
                   "soft_deadline_fired": cm["soft_deadline_fired"],
                   "post_deadline_action_count": sum(r["post_deadline_action_count"] for r in rows),
                   "post_deadline_completed_levels": sum(len(r["post_deadline_completed_levels"]) for r in rows),
                   "timeout_log_count": log.count("analyzer request timed out"),
                   "timeout_read_seconds": [float(v) for v in re.findall(r"read timeout=([0-9.]+)", log)],
                   "forced_cpu_process_exit": cm["forced_cpu_process_exit"],
                   "gpu_server_stopped": manifest["gpu_server_stopped"]},
        "notes": [
            "分组由003 baseline的完整game_id集合决定，保留全部游戏，未按结果筛选。",
            "005全25与003原16总体均值混合了游戏组成差异；原16子组也因池大小、顺序、调度与生成随机性不同而不是严格重复。",
            "warmup RESET由1改0；底座tool_agent和benchmark_initial哈希相同。不能将本轮差异归因于RESET或策略提升。",
            "recorded/generated_tokens保留history+final；analyzer_reported来自solver_note；unattached是两者差。uncached_input为0代表未跟踪。",
            "token份额只描述生成输出的分配，不等于GPU秒数；最后动作至结束的时间包括模型推理、Python计算、队列等待和取消收尾，不等于空转。",
            "状态cancelled结合soft_deadline_fired表示预算截止上下文；游戏层game_over/reset需轨迹另读。所有反事实策略收益仍未验证。",
        ],
        "token_intervals": token_intervals(raw_current, current["runs"]),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "comparison.md").write_text(markdown(result))
    (args.output_dir / "no-action-token-intervals.json").write_text(json.dumps(result["token_intervals"], ensure_ascii=False, indent=2) + "\n")
    for name, value in groups.items():
        print(f"{name}: score={value['mean_score']:.6f}, ceiling={value['mean_completion_ceiling']:.6f}, levels={value['levels_completed']}/{value['levels_available']}, wins={value['wins']}, analyzer_tokens={value['analyzer_reported_generated_tokens']}")
    print(json.dumps(result["common16_comparison"], ensure_ascii=False))
    print(f"Wrote {args.output_dir / 'comparison.json'} and comparison.md")


if __name__ == "__main__":
    main()
