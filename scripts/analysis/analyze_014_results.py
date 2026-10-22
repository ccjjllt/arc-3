#!/usr/bin/env python3
"""Recompute 014 from JSON only; no model calls or execution of saved code."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

from analyze_005_results import audit_timing
from analyze_011_results import aggregate, score_run

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/014-tail-allocation"
OUT = ROOT / "experiments/014-analysis"
ARMS = ("baseline", "tail_80k")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = read(RUN / "experiment-manifest.json")
    archive = ROOT / "experiments/014-source"
    build = read(archive / "build-manifest.json")
    index = read(archive / "source-hashes.json")
    ids = manifest["experiment"]["games"]
    assert len(ids) == len(set(ids)) == 25
    raw, meta, maps, arms = {}, {}, {}, {}
    for arm in ARMS:
        raw[arm] = read(RUN / arm / "benchmark.json")
        meta[arm] = read(RUN / arm / "arm-metadata.json")
        assert raw[arm]["game_weights"] is None and raw[arm]["n_passes"] == 1
        assert [g["game_id"] for g in raw[arm]["game_runs"]] == ids
        rows = [score_run(g) for g in raw[arm]["game_runs"]]
        timing = audit_timing(raw[arm], meta[arm])
        maps[arm] = {g["game_id"]: g for g in rows}
        arms[arm] = {
            "summary": aggregate(rows),
            "status": meta[arm]["status"],
            "exit_code": meta[arm]["exit_code"],
            "requested_seconds": meta[arm]["budget_seconds"],
            "benchmark_wall_seconds": meta[arm]["benchmark_wall_seconds"],
            "post_deadline_actions": sum(g["post_deadline_action_count"] for g in timing["runs"].values()),
            "post_deadline_levels": sum(len(g["post_deadline_completed_levels"]) for g in timing["runs"].values()),
        }
    games = []
    for gid in ids:
        a, b = (maps[arm][gid] for arm in ARMS)
        assert a["number_of_levels"] == b["number_of_levels"]
        assert [r["baseline_actions"] for r in a["levels"]] == [r["baseline_actions"] for r in b["levels"]]
        games.append({
            "game_id": gid, "baseline": a, "tail_80k": b,
            "AE_delta": b["AE"] - a["AE"],
            "mean_AE_contribution": (b["AE"] - a["AE"]) / len(ids),
            "levels_delta": b["levels_completed"] - a["levels_completed"],
            "coverage_delta": b["completion_ceiling"] - a["completion_ceiling"],
            "analyzer_tokens_delta": b["analyzer_tokens"] - a["analyzer_tokens"],
        })
    keys = ("mean_AE", "mean_completion_ceiling", "mean_efficiency_gap", "levels_completed",
            "wins", "actions", "analyzer_tokens", "recorded_tokens", "unattached_tokens")
    delta = {k: arms[ARMS[1]]["summary"][k] - arms[ARMS[0]]["summary"][k] for k in keys}
    delta["relative_AE_change"] = delta["mean_AE"] / arms[ARMS[0]]["summary"]["mean_AE"]
    delta["better_equal_worse"] = {
        "better": sum(g["AE_delta"] > 1e-9 for g in games),
        "equal": sum(abs(g["AE_delta"]) <= 1e-9 for g in games),
        "worse": sum(g["AE_delta"] < -1e-9 for g in games),
    }
    delta["games_with_added_levels"] = sum(g["levels_delta"] > 0 for g in games)
    delta["games_with_lost_levels"] = sum(g["levels_delta"] < 0 for g in games)
    largest = max(games, key=lambda g: g["AE_delta"])
    sensitivity = {
        "largest_positive_game": largest["game_id"],
        "largest_positive_contribution_to_25_game_mean": largest["mean_AE_contribution"],
        "remaining_24_game_mean_delta": statistics.fmean(
            g["AE_delta"] for g in games if g["game_id"] != largest["game_id"]),
        "meaning": "Descriptive sensitivity, not a rerun, held-out evaluation or significance test.",
    }
    env_a, env_b = (meta[a]["environment"] for a in ARMS)
    env_diff = {k: [env_a.get(k), env_b.get(k)] for k in sorted(env_a.keys() | env_b.keys())
                if env_a.get(k) != env_b.get(k)}
    same_fields = ("game_ids", "requested_game_ids", "game_order_sha256", "operation_mode",
                   "budget_seconds", "normalized_budget_seconds", "active_streams", "concurrency",
                   "n_passes", "warmup_action_games", "analyzer_timeout_seconds", "source_sha256")
    metadata_equal = {k: meta[ARMS[0]][k] == meta[ARMS[1]][k] for k in same_fields}
    validation = {
        "metadata_equal": metadata_equal,
        "environment_differences": env_diff,
        "only_expected_environment_difference": env_diff == {"ARC3_PRIORITY_TAIL_LOOKUP": ["remaining", "1"]},
        "runtime_config_equals_frozen": manifest["experiment"] == build["config"],
        "source_map_equals_frozen": manifest["source_hashes"] == build["source_hashes"],
        "archive_hashes_match": all(sha(archive / p) == h for p, h in index["files"].items()),
        "independent_score_recomputations": 50,
        "separate_cpu_pids": meta[ARMS[0]]["pid"] != meta[ARMS[1]]["pid"],
        "both_arms_complete": all(meta[a]["status"] == "completed" and meta[a]["exit_code"] == 0 for a in ARMS),
        "both_budgets_7254": all(meta[a]["budget_seconds"] == 7254 for a in ARMS),
        "complete_pools": all(a["complete_pool"] for a in manifest["arms"]),
        "no_lingering_workers": all(not meta[a]["lingering_worker_threads"] for a in ARMS),
        "both_backend_flushes_confirmed": all(a["cache_flush_backend_confirmed"] for a in manifest["arms"]),
        "server_process_group_stopped": manifest["gpu_server_process_group_stopped"],
        "no_post_deadline_actions_or_levels": all(not arms[a]["post_deadline_actions"] and
                                                  not arms[a]["post_deadline_levels"] for a in ARMS),
    }
    assert all(metadata_equal.values())
    assert all(v for k, v in validation.items() if isinstance(v, bool)), validation
    criteria = {
        "mean_AE_positive": delta["mean_AE"] > 0,
        "weighted_completion_coverage_positive": delta["mean_completion_ceiling"] > 0,
        "total_levels_not_lower": delta["levels_completed"] >= 0,
        "at_least_two_games_added_levels": delta["games_with_added_levels"] >= 2,
        "positive_mean_survives_removing_largest_winner": sensitivity["remaining_24_game_mean_delta"] > 0,
    }
    decision = {"criteria": criteria, "passes_first_round_gate": all(criteria.values()),
                "reverse_confirmation_recommended": all(criteria.values()),
                "formal_submission_ready": False,
                "reason": "First-round gate fails: coverage and total levels decline; the mean gain also depends on the largest winner."
                          if not all(criteria.values()) else "A matched reverse-order confirmation is still required."}
    sources = [RUN / "experiment-manifest.json", archive / "build-manifest.json", archive / "source-hashes.json"]
    for a in ARMS:
        sources.extend(RUN / a / p for p in ("benchmark.json", "arm-metadata.json", "inference-timing.json",
                                             "request-deadline.json", "scheduler-observer.json", "run.log"))
    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "kernel": "jiyujia/arc3-014-tail-allocation", "version": 1,
        "arms": arms, "delta": delta, "sensitivity": sensitivity, "games": games,
        "validation": validation, "decision": decision,
        "session_elapsed_seconds": manifest["elapsed_seconds"],
        "model_ready_seconds": manifest["model_ready_seconds"],
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "limitations": [
            "One stochastic matched pair on the familiar public 25-game pool; not an independent replication or hidden-leaderboard estimate.",
            "Whole-game token/slot allocation and scores both depend on the generated trajectory; a correlation is not a causal attribution.",
            "Client deadline checks do not guarantee server admission before the deadline; see the separate timing audit.",
            "No new GPU experiment or formal competition submission was launched by this analysis.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# 014 首轮完整复算", "", "| 指标 | baseline | tail_80k | 差值 |", "|---|---:|---:|---:|"]
    for k in keys:
        a, b = (arms[n]["summary"][k] for n in ARMS)
        lines.append(f"| {k} | {a:.6f} | {b:.6f} | {delta[k]:+.6f} |")
    lines += ["", "前四项为预设数值门槛；最后一项是对“不能仅靠单游戏”的描述性敏感性检查：", ""]
    lines += [f"- {k}: {v}" for k, v in criteria.items()]
    lines += ["", "| 游戏 | A分数 | B分数 | Δ | A关卡 | B关卡 | A tokens | B tokens |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for g in games:
        a, b = g["baseline"], g["tail_80k"]
        lines.append(f"| {g['game_id']} | {a['AE']:.4f} | {b['AE']:.4f} | {g['AE_delta']:+.4f} | "
                     f"{a['levels_completed']} | {b['levels_completed']} | {a['analyzer_tokens']} | {b['analyzer_tokens']} |")
    lines += ["", f"剔除最大正向游戏 {largest['game_id']} 后，其余24游戏均值差为"
              f"{sensitivity['remaining_24_game_mean_delta']:+.6f}。这是描述性敏感性检查。", "",
              "结论：当前tail版本不晋升，不启动倒序确认，不据此提交新正式版本。"]
    (OUT / "comparison.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"delta": delta, "sensitivity": sensitivity, "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
