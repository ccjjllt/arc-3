#!/usr/bin/env python3
"""Independent numerical recomputation of completed 010 public A/B outputs.

Reads JSON/logs only; does not import the SDK, unpickle games, execute logged
code, call a model, or modify raw artifacts. Intended for manual research use.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics

from analyze_005_results import audit_timing

ROOT = Path(__file__).resolve().parents[2]
ARMS = ("baseline", "retrievable_animation")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_run(raw):
    """Reimplement the published TAAF formula directly from raw action counts."""
    n, k = raw["number_of_levels"], raw["levels_completed"]
    counts, baselines = raw["actions_per_level"], raw["base_actions_per_level"]
    assert 0 <= k <= n and len(counts) == len(baselines) == n
    denominator = n * (n + 1) / 2
    level_rows = []
    for i, (actions, baseline) in enumerate(zip(counts, baselines), 1):
        completed = i <= k
        value = min(115.0, 100.0 * (baseline / actions) ** 2) if completed and actions > 0 else 0.0
        level_rows.append({"level": i, "completed": completed, "actions": actions,
                           "baseline_actions": baseline, "level_AE": value,
                           "weight": i, "weight_fraction": i / denominator,
                           "uncapped_game_contribution": value * i / denominator})
    uncapped = sum(row["uncapped_game_contribution"] for row in level_rows)
    cap = sum(row["weight"] for row in level_rows if row["level_AE"] > 0) / denominator * 100
    score = min(uncapped, cap)
    assert abs(score - raw["final_score"]) < 1e-9
    assert sum(counts) == len(raw["history"])
    match = re.fullmatch(r"tokens=(\d+)", raw.get("solver_note", ""))
    assert match, "Keep missing analyzer tokens explicit; do not silently substitute"
    tokens = int(match.group(1))
    attached = sum(action["generated_tokens"] for action in raw["history"])
    final = raw.get("final_generated_tokens", 0)
    ceiling = k * (k + 1) / (n * (n + 1)) * 100
    return {"game_id": raw["game_id"], "AE": score, "reported_AE": raw["final_score"],
            "uncapped_AE": uncapped, "cap_adjustment": score - uncapped,
            "completion_ceiling": ceiling, "efficiency_gap": ceiling - score,
            "levels_completed": k, "number_of_levels": n, "state": raw["state"],
            "actions": sum(counts), "actions_per_level": counts,
            "reset_actions": sum(action["action"]["id"] == "RESET" for action in raw["history"]),
            "analyzer_tokens": tokens, "history_tokens": attached, "final_tokens": final,
            "recorded_tokens": attached + final, "unattached_tokens": tokens - attached - final,
            "uncached_input_tokens": sum(action["uncached_input_tokens"] for action in raw["history"])
                + raw.get("final_uncached_input_tokens", 0),
            "levels": level_rows}


def aggregate(runs):
    return {"games": len(runs), "mean_AE": statistics.fmean(r["AE"] for r in runs),
            "mean_completion_ceiling": statistics.fmean(r["completion_ceiling"] for r in runs),
            "mean_efficiency_gap": statistics.fmean(r["efficiency_gap"] for r in runs),
            "wins": sum(r["state"] == "won" for r in runs),
            "state_counts": dict(Counter(r["state"] for r in runs)),
            **{key: sum(r[key] for r in runs) for key in ("levels_completed", "number_of_levels",
                "actions", "reset_actions", "analyzer_tokens", "history_tokens", "final_tokens",
                "recorded_tokens", "unattached_tokens", "uncached_input_tokens")}}


def action_token_section(raw, scored, cap):
    """Descriptive prefix only: completed boundaries must precede the cap.

    An action's attached generation is charged as a whole; zero-token members
    of the same batch remain eligible. No fractional generation, unexecuted
    action, future completion, or later level's actions are scored.
    """
    cumulative = []
    for entry in raw["history"]:
        assert entry["generated_tokens"] >= 0
        cumulative.append((cumulative[-1] if cumulative else 0) + entry["generated_tokens"])
    prefix_actions = sum(tokens <= cap for tokens in cumulative)
    cursor, boundaries, completed = 0, [], []
    for level in scored["levels"]:
        cursor += level["actions"]
        if not level["completed"]:
            continue
        assert cursor > 0
        boundary = {"level": level["level"], "action_num": cursor,
                    "attached_tokens": cumulative[cursor - 1],
                    "included_at_cap": cumulative[cursor - 1] <= cap,
                    "wallclock_seconds": raw["history"][cursor - 1]["wallclock_seconds"]}
        boundaries.append(boundary)
        if boundary["included_at_cap"]:
            completed.append(level)
    raw_score = sum(level["uncapped_game_contribution"] for level in completed)
    score_cap = sum(level["weight_fraction"] * 100 for level in completed if level["level_AE"] > 0)
    return {"cap_action_attached_tokens": cap, "levels_completed_at_cap": len(completed),
            "AE_at_cap": min(raw_score, score_cap), "completed_level_boundaries": boundaries,
            "prefix_executed_actions": prefix_actions,
            "prefix_attached_tokens": cumulative[prefix_actions - 1] if prefix_actions else 0,
            "unused_cap_before_next_whole_action": cap - (cumulative[prefix_actions - 1] if prefix_actions else 0),
            "raw_total_action_attached_tokens": cumulative[-1] if cumulative else 0}


def render(result):
    a, b = (result["arms"][arm]["summary"] for arm in ARMS)
    lines = ["# 010 公开同池结果复算", "",
        f"12 个已知公开游戏，baseline 先运行，各 1 遍。AE {a['mean_AE']:.6f} → {b['mean_AE']:.6f}（{b['mean_AE']-a['mean_AE']:+.6f}），完成关卡 {a['levels_completed']} → {b['levels_completed']}/{a['number_of_levels']}；全通 {a['wins']} → {b['wins']}。单次筛选，不能把差值直接解释成旧动画检索的因果收益。", "",
        "| 指标 | baseline | retrievable_animation | 差值 |", "|---|---:|---:|---:|"]
    for label, key in [("AE均值", "mean_AE"), ("覆盖上限均值", "mean_completion_ceiling"),
                       ("效率缺口均值", "mean_efficiency_gap"), ("关卡", "levels_completed"),
                       ("全通", "wins"), ("动作", "actions"), ("RESET", "reset_actions"),
                       ("analyzer tokens", "analyzer_tokens"), ("history+final tokens", "recorded_tokens"),
                       ("未归属 tokens", "unattached_tokens")]:
        lines.append(f"| {label} | {a[key]:,.6f} | {b[key]:,.6f} | {b[key]-a[key]:+,.6f} |")
    lines += ["", "游戏等权（1/12）；最后一列是单游戏 AE 差值除以 12，而非剔除游戏后的均值。", "",
        "| 游戏 | AE A→B | ΔAE | 关卡A→B | 动作A→B | analyzer tokens A→B | B旧动画命中 | 对总均值贡献 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["games"]:
        aa, bb = row["baseline"], row["retrievable_animation"]
        lines.append(f"| {row['game_id']} | {aa['AE']:.4f}→{bb['AE']:.4f} | {row['AE_delta']:+.4f} | {aa['levels_completed']}→{bb['levels_completed']}/{aa['number_of_levels']} | {aa['actions']}→{bb['actions']} | {aa['analyzer_tokens']:,}→{bb['analyzer_tokens']:,} | {row['archive_counts'].get('nonlatest_hits',0)} | {row['mean_AE_contribution']:+.6f} |")
    lines += ["", "分数先按第 i 关权重 i 计算 `min(115, 100*(human_baseline/actions)^2)`，再用已完成且非零得分的权重上限裁剪。原始逐关贡献与裁剪修正都保存于 comparison.json，不能把未裁剪的逐关贡献直接当最终分数。", "",
        "| 臂 | 请求预算秒 | benchmark wall秒 | 截止后动作/关卡 | 完成状态 | token记录缺口 |",
        "|---|---:|---:|---:|---|---:|"]
    for name, arm in result["arms"].items():
        t = arm["timing"]
        lines.append(f"| {name} | {t['budget_seconds']} | {t['benchmark_wall_seconds']:.3f} | {t['post_deadline_actions']}/{t['post_deadline_levels']} | {arm['status']}, exit {arm['exit_code']} | {arm['summary']['unattached_tokens']:,} |")
    lines += ["", "## 共同动作附着 tokens 截面（描述性）", "",
        "每局取两臂 history.generated_tokens 总和的较小者，只计累计附着 tokens 不超过此上限的已完成关卡边界；没有把后续才完成的关卡或其未来动作算入。batch 中零 token 动作沿实际执行顺序保留。该截面不是等GPU算力、独立随机对照或新正式分数，不能替代上方完整12游戏结果。", "",
        "| 游戏 | 共同上限 | 关卡A→B | AE A→B | 已执行动作A→B |", "|---|---:|---:|---:|---:|"]
    for row in result["games"]:
        section = row["common_action_token_section"]
        aa, bb = (section[arm] for arm in ARMS)
        lines.append(f"| {row['game_id']} | {section['cap']:,} | {aa['levels_completed_at_cap']}→{bb['levels_completed_at_cap']} | {aa['AE_at_cap']:.4f}→{bb['AE_at_cap']:.4f} | {aa['prefix_executed_actions']}→{bb['prefix_executed_actions']} |")
    lines += ["", "## 解释边界", ""] + [f"- {note}" for note in result["notes"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/010-retrievable-animation")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/010-analysis")
    args = parser.parse_args()
    manifest = read(args.root / "experiment-manifest.json")
    ledger = read(args.root / "retrievable_animation/retrievable-animation.json")
    ledger_games = {entry["game_id"]: entry for entry in ledger["sessions"]}
    metadata, raw, arm_results, maps = {}, {}, {}, {}
    sources = []
    for arm in ARMS:
        directory = args.root / arm
        raw[arm] = read(directory / "benchmark.json")
        metadata[arm] = read(directory / "arm-metadata.json")
        assert raw[arm]["game_weights"] is None and raw[arm]["n_passes"] == 1
        rows = [score_run(run) for run in raw[arm]["game_runs"]]
        assert len({row["game_id"] for row in rows}) == len(rows)
        timing = audit_timing(raw[arm], metadata[arm])
        maps[arm] = {row["game_id"]: {**row, "timing": timing["runs"][row["game_id"]]} for row in rows}
        log = (directory / "run.log").read_text()
        arm_results[arm] = {"summary": aggregate(rows), "status": metadata[arm]["status"],
            "exit_code": metadata[arm]["exit_code"],
            "timing": {"budget_seconds": metadata[arm]["budget_seconds"],
                "deadline_benchmark_second": timing["deadline_benchmark_second"],
                "post_deadline_actions": sum(t["post_deadline_action_count"] for t in timing["runs"].values()),
                "post_deadline_levels": sum(len(t["post_deadline_completed_levels"]) for t in timing["runs"].values()),
                "benchmark_wall_seconds": metadata[arm]["benchmark_wall_seconds"],
                "benchmark_datetime_seconds": (datetime.fromisoformat(raw[arm]["end_time"]) - datetime.fromisoformat(raw[arm]["start_time"])).total_seconds(),
                "soft_deadline_fired": metadata[arm]["soft_deadline_fired"],
                "forced_cpu_process_exit": metadata[arm]["forced_cpu_process_exit"],
                "lingering_worker_threads": metadata[arm]["lingering_worker_threads"],
                "timeout_log_count": log.count("analyzer request timed out")}}
        sources.extend({"path": str((directory / name).resolve()), "sha256": sha(directory / name)}
                       for name in ("benchmark.json", "arm-metadata.json", "run.log"))
    ids = metadata["baseline"]["game_ids"]
    assert set(maps[ARMS[0]]) == set(maps[ARMS[1]]) == set(ids)
    n = len(ids)
    rows = []
    for game in ids:
        a, b = (maps[arm][game] for arm in ARMS)
        assert a["number_of_levels"] == b["number_of_levels"]
        decomposition = {"shared_completed_levels": 0.0, "new_completed_levels": 0.0,
                         "lost_completed_levels": 0.0,
                         "cap_adjustment_delta": b["cap_adjustment"] - a["cap_adjustment"]}
        for la, lb in zip(a["levels"], b["levels"]):
            assert la["baseline_actions"] == lb["baseline_actions"]
            delta = lb["uncapped_game_contribution"] - la["uncapped_game_contribution"]
            if la["completed"] and lb["completed"]:
                decomposition["shared_completed_levels"] += delta
            elif lb["completed"]:
                decomposition["new_completed_levels"] += delta
            elif la["completed"]:
                decomposition["lost_completed_levels"] += delta
        assert abs(sum(decomposition.values()) - (b["AE"] - a["AE"])) < 1e-9
        cap = min(a["history_tokens"], b["history_tokens"])
        sections = {arm: action_token_section(next(r for r in raw[arm]["game_runs"] if r["game_id"] == game),
                                              maps[arm][game], cap) for arm in ARMS}
        rows.append({"game_id": game, "baseline": a, "retrievable_animation": b,
            "AE_delta": b["AE"] - a["AE"], "levels_delta": b["levels_completed"] - a["levels_completed"],
            "actions_delta": b["actions"] - a["actions"],
            "analyzer_tokens_delta": b["analyzer_tokens"] - a["analyzer_tokens"],
            "mean_AE_contribution": (b["AE"] - a["AE"]) / n,
            "score_decomposition": decomposition,
            "common_action_token_section": {"cap": cap, **sections},
            "archive_counts": ledger_games[game]["counts"],
            "capture_actions_match_benchmark": ledger_games[game]["captured_actions"] == b["actions"]})
    total_delta = sum(row["AE_delta"] for row in rows)
    for row in rows:
        row["leave_one_out_mean_delta"] = (total_delta - row["AE_delta"]) / (n - 1)
    same = ("game_ids", "requested_game_ids", "game_order_sha256", "operation_mode", "budget_seconds",
            "normalized_budget_seconds", "active_streams", "concurrency", "n_passes",
            "warmup_action_games", "analyzer_timeout_seconds", "environment")
    source_a, source_b = (metadata[arm]["source_sha256"] for arm in ARMS)
    common_source_equal = {key: source_a[key] == source_b[key] for key in source_a.keys() & source_b.keys()}
    frozen_root = ROOT / "experiments/010-source"
    frozen = read(frozen_root / "source-hashes.json")
    frozen_matches = {name: sha(frozen_root / name) == expected for name, expected in frozen["files"].items()}
    launch = read(ROOT / "experiments/010-launch.json")
    sources.extend({"path": str(path.resolve()), "sha256": sha(path)} for path in
                   (args.root / "experiment-manifest.json", args.root / "retrievable_animation/retrievable-animation.json",
                    frozen_root / "source-hashes.json", ROOT / "experiments/010-launch.json", Path(__file__)))
    grouped = {}
    for label, selected in [("queried_games", [r for r in rows if r["archive_counts"].get("query_calls", 0)]),
                            ("zero_query_games", [r for r in rows if not r["archive_counts"].get("query_calls", 0)])]:
        grouped[label] = {"games": [r["game_id"] for r in selected],
            "mean_AE_contribution": sum(r["mean_AE_contribution"] for r in selected),
            "levels_delta": sum(r["levels_delta"] for r in selected)}
    summaries = {arm: arm_results[arm]["summary"] for arm in ARMS}
    delta = {key: summaries[ARMS[1]][key] - summaries[ARMS[0]][key] for key in
             ("mean_AE", "mean_completion_ceiling", "mean_efficiency_gap", "levels_completed",
              "wins", "actions", "analyzer_tokens", "recorded_tokens", "unattached_tokens")}
    delta["AE_relative_change"] = delta["mean_AE"] / summaries[ARMS[0]]["mean_AE"]
    delta["analyzer_tokens_relative_change"] = delta["analyzer_tokens"] / summaries[ARMS[0]]["analyzer_tokens"]
    delta["AE_better_equal_worse"] = {"better": sum(r["AE_delta"] > 1e-9 for r in rows),
                                     "equal": sum(abs(r["AE_delta"]) <= 1e-9 for r in rows),
                                     "worse": sum(r["AE_delta"] < -1e-9 for r in rows)}
    result = {"schema_version": 1, "sources": sources, "arms": arm_results, "overall_delta": delta,
        "games": rows, "post_hoc_query_groups": grouped,
        "score_decomposition": {key: sum(r["score_decomposition"][key] for r in rows) / n
                                for key in rows[0]["score_decomposition"]},
        "comparability": {"equal_metadata_fields": {key: metadata[ARMS[0]][key] == metadata[ARMS[1]][key] for key in same},
            "game_order_hash_recomputed": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            "game_order_hash_matches_metadata": all(hashlib.sha256(json.dumps(ids).encode()).hexdigest() == metadata[a]["game_order_sha256"] for a in ARMS),
            "both_raw_game_orders_equal_fixed_plan": all([r["game_id"] for r in raw[a]["game_runs"]] == manifest["experiment"]["games"] for a in ARMS),
            "same_exact_ids_and_order_as_006": ids == read(ROOT / "experiments/006-transient-history.json")["games"],
            "all_game_weights_null": True, "common_source_hashes_equal": common_source_equal,
            "candidate_extra_source_keys": sorted(source_b.keys() - source_a.keys()),
            "candidate_module_matches_frozen_and_launch": source_b["retrievable_animation.py"] == launch["module_sha256"] == frozen["files"]["src/arc3_research/retrievable_animation.py"],
            "manifest_matches_frozen_sources": {name: expected == frozen["files"][name] for name, expected in manifest["source_hashes"].items()},
            "frozen_archive_file_hashes_match": frozen_matches,
            "benchmark_initial_pickle_hash_equal_only": source_a["benchmark_initial.pkl"] == source_b["benchmark_initial.pkl"],
            "distinct_cpu_pids": metadata[ARMS[0]]["pid"] != metadata[ARMS[1]]["pid"],
            "arm_order": manifest["experiment"]["arm_order"],
            "cache_flush_http_status": [a["cache_flush_http_status"] for a in manifest["arms"]],
            "cache_flush_success_log_count": (args.root / "serve.log").read_text().count("Cache flushed successfully!")},
        "sensitivity": {"leave_one_out_min": min(r["leave_one_out_mean_delta"] for r in rows),
                        "leave_one_out_max": max(r["leave_one_out_mean_delta"] for r in rows),
                        "without_m0r0_mean_delta": next(r["leave_one_out_mean_delta"] for r in rows if r["game_id"].startswith("m0r0-")),
                        "without_ft09_mean_delta": next(r["leave_one_out_mean_delta"] for r in rows if r["game_id"].startswith("ft09-"))},
        "session": {key: manifest.get(key) for key in ("status", "elapsed_seconds", "model_ready_seconds", "gpu_server_stopped")},
        "notes": [
            "每臂只有一次运行；固定baseline先、候选后、共享10活跃流调度。相同墙钟不保证逐游戏tokens、prefill或GPU计算机会相同，无显著性或因果结论。",
            "所有24个game-run分数由逐关原始动作数独立重算，与final_score逐项误差<1e-9。游戏等权，每个游戏贡献为ΔAE/12。",
            "两臂requested budget均3482秒，截止后动作和关卡均为0。候选较长收尾不增加游戏动作预算，但尾部生成tokens仍应保留。",
            "analyzer tokens来自solver_note的完整tokens=格式；history+final为动作/收尾记账，未归属差额不是再加一次的tokens。input tokens记录不足，不能据此比较完整推理成本。",
            "零query游戏也接收新API说明且参与共享调度。query分组由实际轨迹形成，只是事后记账，不是有/无检索的随机对照。",
            "最大加分m0r0无archive查询，最大回退ft09也无查询；不能把总增益都归因检索，也不能从零查询直接认定没有间接影响。",
            "删去单游戏后的均值只展示集中度，不替代完整12游戏结果；已知诊断池不是未见holdout，也不是正式排行榜分数。",
            "原始benchmark_initial.pkl仅核对两臂运行时记录的同一hash；没有反序列化或声称核验未下载的blob。",
        ]}
    assert abs(sum(result["score_decomposition"].values()) - delta["mean_AE"]) < 1e-9
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "comparison.md").write_text(render(result))
    print(json.dumps({"overall_delta": delta, "score_decomposition": result["score_decomposition"],
                      "query_groups": grouped, "sensitivity": result["sensitivity"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
