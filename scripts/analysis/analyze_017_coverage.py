"""Describe four full-pool baselines without treating them as IID repeats.

Reads recorded action counts only; never executes stored agent code or games.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics

from analyze_011_results import score_run, aggregate

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "005": "runs/005-full-baseline/baseline/benchmark.json",
    "014": "runs/014-tail-allocation/baseline/benchmark.json",
    "016-old": "runs/016-pace-allocation/baseline/benchmark.json",
    "016-jiyujia": "runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
}


def main():
    runs, summaries, hashes = {}, {}, {}
    for name, relative in SOURCES.items():
        payload = (ROOT / relative).read_bytes()
        raw = json.loads(payload)
        rows = [score_run(row) for row in raw["game_runs"]]
        assert len(rows) == 25 and raw["n_passes"] == 1
        runs[name] = {row["game_id"]: row for row in rows}
        summaries[name] = aggregate(rows)
        hashes[relative] = hashlib.sha256(payload).hexdigest()
    ids = list(runs["005"])
    assert all(list(run) == ids for run in runs.values())
    games = []
    for gid in ids:
        rows = [run[gid] for run in runs.values()]
        games.append({
            "game_id": gid,
            "levels_available": rows[0]["number_of_levels"],
            "levels_by_run": {name: run[gid]["levels_completed"] for name, run in runs.items()},
            "scores_by_run": {name: run[gid]["AE"] for name, run in runs.items()},
            "min_levels": min(row["levels_completed"] for row in rows),
            "max_levels": max(row["levels_completed"] for row in rows),
            "mean_AE": statistics.fmean(row["AE"] for row in rows),
            "min_AE": min(row["AE"] for row in rows),
            "max_AE": max(row["AE"] for row in rows),
            "won_runs": sum(row["state"] == "won" for row in rows),
            "analyzer_tokens_by_run": {name: run[gid]["analyzer_tokens"] for name, run in runs.items()},
        })
    result = {
        "sources": hashes, "summaries": summaries, "games": games,
        "selection_free_low_coverage_definition": "Maximum completed fraction over these four recorded baselines <= 1/3. Descriptive post-hoc grouping, not an experimental inclusion rule.",
        "low_coverage_in_all_four": [g["game_id"] for g in games if g["max_levels"] / g["levels_available"] <= 1 / 3],
        "won_at_least_once_not_always": [g["game_id"] for g in games if 0 < g["won_runs"] < 4],
        "oracle_per_game_best_mean_AE": statistics.fmean(g["max_AE"] for g in games),
        "oracle_per_game_worst_mean_AE": statistics.fmean(g["min_AE"] for g in games),
        "limitations": [
            "These are four existing runs, not newly controlled random-seed replications. 005 predates deadline/diagnostic fixes; 016-old stopped before its candidate arm.",
            "Shared queues, trajectories, request budgets, and runtime versions affect outcomes; spread is not an estimate of pure sampling variance.",
            "Per-game best/worst use hindsight and are not deployable policies, ensemble scores, hidden-LB predictions, or evidence that restarts help.",
            "Every game remains in the analysis; the familiar public pool is not a holdout.",
        ],
    }
    out = ROOT / "experiments/017-research"
    out.mkdir(parents=True, exist_ok=True)
    (out / "cross-run-coverage.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: result[key] for key in ("low_coverage_in_all_four", "won_at_least_once_not_always", "oracle_per_game_best_mean_AE", "oracle_per_game_worst_mean_AE")}, indent=2))
    for g in sorted(games, key=lambda g: g["max_levels"] / g["levels_available"]):
        print(g["game_id"], g["levels_by_run"], "of", g["levels_available"], "meanAE", round(g["mean_AE"], 2))


if __name__ == "__main__":
    main()
