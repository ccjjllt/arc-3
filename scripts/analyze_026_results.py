"""Read-only 026 fork A/B summary; no automatic promotion.

Compares full-trajectory (prefix replay + bounded continuation) runs between
repair_A (fresh continuation) and repair_B (host evidence recheck first).
Also cross-checks that the Kaggle replay prefix matches the local fork
inputs exactly (environment determinism gate).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORKS = {"ft09-0d8bbf25": 11, "tr87-cd924810": 132, "r11l-495a7899": 40}


def read(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "runs/026-failure-repair")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/026-analysis")
    parser.add_argument("--inputs", type=Path, default=ROOT / "experiments/026-fork-inputs.json")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    if root == out or root in out.parents or out in root.parents:
        parser.error("Keep raw and derived outputs separate")
    manifest = read(root / "experiment-manifest.json")
    arms = manifest["experiment"]["arm_order"]
    if arms != ["repair_A", "repair_B"]:
        parser.error("This analysis is for the frozen 026 repair pair")
    raw = {a: read(root / a / "benchmark.json") for a in arms}
    fork_in = json.loads(args.inputs.read_text())
    per_game = {}
    for game_id, cut in FORKS.items():
        rows = {}
        for a in arms:
            runs = [g for g in raw[a]["game_runs"] if g["game_id"] == game_id]
            if len(runs) != 1:
                raise ValueError(f"{a}/{game_id}: expected 1 run, got {len(runs)}")
            g = runs[0]
            hist = g.get("history", [])
            # determinism gate: replayed prefix must equal fork inputs exactly
            want = fork_in["actions"][game_id]
            got = [{"a": h["action"]["id"], "d": h["action"].get("data") or {}}
                   for h in hist[:cut]]
            rows[a] = {
                "state": g.get("state"),
                "levels_completed": g.get("levels_completed"),
                "number_of_levels": g.get("number_of_levels"),
                "final_score": g.get("final_score"),
                "actions_total": len(hist),
                "actions_post_T": len(hist) - cut,
                "prefix_exact": got == want,
                "levels_post_T": (g.get("levels_completed") or 0) - _levels_at_cut(game_id),
                "solver_note": g.get("solver_note"),
            }
            post = [h["action"]["id"] for h in hist[cut:cut + 5]]
            rows[a]["first_post_T_actions"] = post
        a_row, b_row = rows["repair_A"], rows["repair_B"]
        per_game[game_id] = {
            "A": a_row, "B": b_row,
            "levels_delta_B_minus_A": (b_row["levels_completed"] or 0) - (a_row["levels_completed"] or 0),
            "diverged": a_row["first_post_T_actions"] != b_row["first_post_T_actions"],
        }
    report = {
        "kind": "026-fork-AB", "experiment": manifest["experiment"]["id"],
        "arms": arms, "per_game": per_game,
        "both_clean": all(e.get("exit_code") == 0 and e.get("complete_pool") is True
                          for e in manifest["arms"]),
        "session_minutes": manifest.get("elapsed_seconds", 0) / 60,
        "limits": ["Full-trajectory scores share a deterministic prefix; only the suffix differs.",
                   "Single fixed-order pair on familiar prefixes, not hidden score or causal proof.",
                   "No logged model code, game implementation, pickle, network or GPU is executed."],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def _levels_at_cut(game_id: str) -> int:
    # Levels completed within the replayed prefix. Verified constants: cut
    # action counts reach L3/L5/L1/L3 respectively (see replay_026_prefix.py
    # checkpoints: ft09 11->L3, tr87 132->L5, r11l 40->L3).
    return {"ft09-0d8bbf25": 2, "tr87-cd924810": 4,
            "r11l-495a7899": 2}[game_id]


if __name__ == "__main__":
    main()
