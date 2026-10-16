"""Fixed-observation priority sensitivity, not a scheduler or score replay."""
from __future__ import annotations

import bisect
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("tail-priority-cpu.json")
PRIORITY = ROOT / "research/runtime-bundle/src/ARC3-Inference/inference/agent/priority_scheduler.py"
spec = importlib.util.spec_from_file_location("arc3_tail_sensitivity", PRIORITY)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def study(folder):
    benchmark_path = ROOT / "runs" / folder / "baseline/benchmark.json"
    meta_path = benchmark_path.with_name("arm-metadata.json")
    benchmark = json.loads(benchmark_path.read_text())
    metadata = json.loads(meta_path.read_text())
    budget = metadata["budget_seconds"]
    start = datetime.fromisoformat(benchmark["start_time"])
    games = []
    for game in benchmark["game_runs"]:
        history = game["history"]
        assert sum(game["actions_per_level"]) == len(history)
        offset = (datetime.fromisoformat(game["started_at"]) - start).total_seconds()
        times = [offset + h["wallclock_seconds"] for h in history]
        assert times == sorted(times)
        token_prefix = [0]
        for h in history:
            token_prefix.append(token_prefix[-1] + h["generated_tokens"])
        completed_boundaries, total = [], 0
        for count in game["actions_per_level"][:game["levels_completed"]]:
            total += count
            completed_boundaries.append(total)
        games.append((game, times, token_prefix, completed_boundaries))
    first_actions = sorted(
        [{"game_id": g["game_id"], "seconds": times[0]} for g, times, _, _ in games if times],
        key=lambda row: row["seconds"],
    )
    snapshots = []
    for fraction in (0.10, 0.25, 0.50, 0.75, 0.90):
        at = budget * fraction
        tail_fraction = min(1.0, (budget-at) / (0.2*budget))
        rows = []
        for game, times, token_prefix, boundaries in games:
            consumed = bisect.bisect_right(times, at)
            if not consumed:
                continue
            completed = bisect.bisect_right(boundaries, consumed)
            if completed >= game["number_of_levels"]:
                continue
            level_start = boundaries[completed-1] if completed else 0
            state = module.PrioritySnapshot(
                completed+1, consumed-level_start,
                token_prefix[consumed]-token_prefix[level_start],
                1.0, game["number_of_levels"],
            )
            kwargs = {"normalize_score": True, "tail_fraction": tail_fraction}
            rows.append({
                "game_id": game["game_id"], "level": state.level,
                "total_levels": state.total_levels, "actions_at_observed_level": state.actions,
                "action_attached_tokens_at_observed_level": state.tokens,
                "last_observed_action_seconds": times[consumed-1],
                "remaining_priority": module.priority_value(state, tail_lookup="remaining", **kwargs),
                "empirical_80k_priority": module.priority_value(state, tail_lookup=True, **kwargs),
            })
        old = sorted(rows, key=lambda r: (-r["remaining_priority"], r["game_id"]))
        new = sorted(rows, key=lambda r: (-r["empirical_80k_priority"], r["game_id"]))
        comparable = inversions = 0
        for i, a in enumerate(rows):
            for b in rows[i+1:]:
                x = a["remaining_priority"]-b["remaining_priority"]
                y = a["empirical_80k_priority"]-b["empirical_80k_priority"]
                if x and y:
                    comparable += 1
                    inversions += (x*y < 0)
        snapshots.append({
            "budget_fraction": fraction, "seconds": at, "tail_fraction": tail_fraction,
            "state_count": len(rows), "strictly_comparable_pairs": comparable,
            "pairwise_order_reversals": inversions,
            "remaining_top3": [r["game_id"] for r in old[:3]],
            "empirical_80k_top3": [r["game_id"] for r in new[:3]], "states": rows,
        })
    return {
        "folder": folder, "budget_seconds": budget, "game_count": len(games),
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in [benchmark_path, meta_path]},
        "observed_first_actions": first_actions,
        "observed_first_action_coverage_seconds": {
            "50_percent": first_actions[(len(games)-1)//2]["seconds"],
            "90_percent": first_actions[(9*len(games)+9)//10-1]["seconds"],
            "100_percent": first_actions[-1]["seconds"] if len(first_actions)==len(games) else None,
        },
        "candidate_coverage_time_difference_seconds": None,
        "snapshots": snapshots,
    }


reports = [study(folder) for folder in ["005-full-baseline", "006-transient-history", "007-program-state"]]
table = [{"total_levels": n,
          "remaining_B": list(module.TAIL_LOOKUP_REMAINING[n]),
          "empirical_80k_B_after_default_efficiency": [round(x*0.8, 6) for x in module.TAIL_LOOKUP_80K[n]]}
         for n in range(6, 11)]
result = {
    "kind": "fixed_observation_priority_sensitivity_not_score_replay",
    "run_date_local": "2026-10-13 Asia/Shanghai",
    "source_hashes": {str(PRIORITY.relative_to(ROOT)): sha(PRIORITY),
                      str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
    "method": [
        "Use small baseline benchmark JSON files only; do not read request logs or game engines.",
        "ActionRecord.wallclock_seconds is elapsed since game start, not an inter-action duration.",
        "Use each fixed clock's last observed action; infer completed level boundaries from final monotone per-level action counters.",
        "Sum action-attached generated tokens within the inferred current level, with pace=1 as in baseline.",
        "Evaluate the unchanged priority_value function twice: tail_lookup='remaining' versus True, preserving score normalization and final-20-percent tail fade.",
        "Rank all observed unfinished game states as a sensitivity check, not the unknown real waiting queue.",
    ],
    "limitations": [
        "No context-trim or gate-entry timestamps exist in these compact benchmarks; actual waiting/admitted sets are not reconstructed.",
        "In-flight/no-action model tokens and within-tool level-transition accounting are not fully represented by action-attached records.",
        "All clocks, action histories, completions, and first-action coverage are the original baseline's observed values and are held fixed.",
        "Changed priorities do not imply changed slot admissions, compute use, coverage time, levels, or score.",
        "The candidate's coverage-time difference is unknown (null), not zero; an actual paired run is required.",
        "Fresh-game priority bands remain unchanged by this switch. It primarily affects post-trim handovers and queue repricing.",
    ],
    "B_tables": table, "runs": reports,
}
OUT.write_text(json.dumps(result, indent=2)+"\n")
for report in reports:
    print(report["folder"], report["observed_first_action_coverage_seconds"],
          [(s["budget_fraction"], s["pairwise_order_reversals"], s["strictly_comparable_pairs"])
           for s in report["snapshots"]])
print(OUT)
