#!/usr/bin/env python3
"""025: offline recomputation of initial-admission order (CPU-only, read-only).

Scope (per 2026-10-20 review): ONLY the two baseline arms
(014 baseline, 016 baseline). Both run the identical scheduler policy
(TAIL_LOOKUP=remaining, PACE=0, SCORE_NORMALIZATION=1, TAIL_FADE=1/0.2,
REFRESH_QUEUE=1, 10 streams, 0 warmup), verified from arm-metadata.json.
The tail_80k and pace_1x arms are EXCLUDED: mixing their recorded
priorities with 009-formula values would be a mixed-policy comparison.

Method per selection event:
  1. Fidelity gate: argmax(priority, -token) over the recorded candidates
     must equal the recorded `selected` row. Any mismatch aborts: our
     reading of the heap rule ((-priority, token), smaller token wins
     ties; observer doc: "Candidate array is heap membership") is wrong.
  2. Only null-snapshot (initial admission, 2_000_000 band) candidates are
     rescored with the 009 formula: PrioritySnapshot(level=1, actions=0,
     tokens=0, cost_multiplier=1.0, total_levels=N) with tail_lookup=
     "remaining", normalize_score=True and the contemporaneous
     tail_fraction (fade fraction 0.2, event clocks). Started candidates
     keep recorded priorities.
  3. Winner = max rescore, tie-break smaller token (same heap rule).

Limits (written into the output): single-decision counterfactual only.
After the first reselected admission, real clocks, levels and queues
diverge, so full-run scores under the new policy CANNOT be projected
from old logs. No GPU, no model calls, no game code; JSON only read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/runtime-bundle/src/ARC3-Inference"))

from inference.agent.priority_scheduler import PrioritySnapshot, priority_value

ARMS = [
    ("014-baseline", "runs/014-tail-allocation/baseline"),
    ("016-baseline", "runs/016-pace-allocation-jiyujia/baseline"),
]

FADE_FRACTION = 0.2
EXPECTED_POLICY = {
    "ARC3_PRIORITY_TAIL_LOOKUP": "remaining",
    "ARC3_PRIORITY_PACE": "0",
    "ARC3_PRIORITY_SCORE_NORMALIZATION": "1",
    "ARC3_PRIORITY_TAIL_FADE": "1",
    "ARC3_PRIORITY_TAIL_FADE_FRACTION": "0.2",
}


def tail_fraction_of(event) -> float | None:
    start = event.get("clock_start_monotonic")
    deadline = event.get("clock_deadline_monotonic")
    now = event.get("monotonic")
    if start is None or deadline is None or now is None:
        return None
    window = FADE_FRACTION * max(0.0, deadline - start)
    if window <= 0:
        return 0.0
    return max(0.0, deadline - now) / window


def initial_value(total_levels: int, tail_fraction) -> int:
    snap = PrioritySnapshot(level=1, actions=0, tokens=0.0,
                            cost_multiplier=1.0, total_levels=total_levels)
    return priority_value(snap, endgame=False, tail_fraction=tail_fraction,
                          tail_lookup="remaining", normalize_score=True)


def main() -> None:
    summary = {}
    for name, rundir in ARMS:
        obs = json.loads((ROOT / rundir / "scheduler-observer.json").read_text())
        meta = json.loads((ROOT / rundir / "arm-metadata.json").read_text())
        policy = {k: meta.get("environment", {}).get(k) for k in EXPECTED_POLICY}
        if policy != EXPECTED_POLICY:
            raise SystemExit(f"{name}: scheduler policy changed: {policy}")
        levels = {g["game_id"]: g["number_of_levels"]
                  for g in meta.get("game_results", [])}
        n_sel = n_fidelity_bad = n_mixed = n_flip = 0
        flips = []
        first_mixed = None
        for e in obs["events"]:
            if e.get("kind") != "selection":
                continue
            n_sel += 1
            cands = e.get("candidates", [])
            if e.get("candidates_omitted", 0):
                raise SystemExit(f"{name} seq {e['seq']}: truncated candidate set")
            orig_best = max(cands, key=lambda c: (c["priority"], -c["token"]))
            sel = e.get("selected") or {}
            if (orig_best["token"], orig_best["priority"]) != (
                    sel.get("token"), sel.get("priority")):
                n_fidelity_bad += 1
                continue
            has_null = any(c.get("snapshot") is None for c in cands)
            has_started = any(c.get("snapshot") is not None for c in cands)
            if not (has_null and has_started):
                continue
            n_mixed += 1
            if first_mixed is None:
                first_mixed = e["seq"]
            tf = tail_fraction_of(e)
            rescored = []
            for c in cands:
                if c.get("snapshot") is None:
                    gid = (c.get("session") or {}).get("game_id")
                    tl = levels.get(gid)
                    if tl is None:
                        rescored.append((c["priority"], c))
                        continue
                    rescored.append((initial_value(tl, tf), c))
                else:
                    rescored.append((c["priority"], c))
            new_best = max(rescored, key=lambda item: (item[0], -item[1]["token"]))
            if new_best[1]["token"] != orig_best["token"]:
                n_flip += 1
                flips.append({
                    "seq": e["seq"],
                    "orig_token": orig_best["token"],
                    "orig_game": (orig_best.get("session") or {}).get("game_id"),
                    "new_token": new_best[1]["token"],
                    "new_game": (new_best[1].get("session") or {}).get("game_id"),
                    "new_snapshot": new_best[1].get("snapshot"),
                    "new_priority": new_best[0],
                    "orig_priority": orig_best["priority"],
                    "tail_fraction": tf,
                })
        if n_fidelity_bad:
            raise SystemExit(f"{name}: fidelity gate failed on "
                             f"{n_fidelity_bad}/{n_sel} selections; aborting")
        summary[name] = {
            "selections": n_sel,
            "fidelity_mismatches": 0,
            "mixed": n_mixed,
            "flipped": n_flip,
            "flip_rate_mixed": (n_flip / n_mixed) if n_mixed else None,
            "first_mixed_seq": first_mixed,
            "flips": flips,
        }
        print(f"{name}: selections={n_sel} fidelity=OK mixed={n_mixed} "
              f"flipped={n_flip} rate={summary[name]['flip_rate_mixed']}")
    out = ROOT / "experiments/025-admission-cpu"
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "014-baseline and 016-baseline only; identical scheduler "
                 "policy verified from arm-metadata environment",
        "excluded": "tail_80k (empirical 80k tail) and pace_1x (dynamic pace): "
                    "their recorded priorities belong to other policies",
        "limits": "Single-decision counterfactual. First reselection "
                  "diverges clocks/levels/queues; full-run scores under the "
                  "new policy cannot be projected from old logs.",
        "arms": summary,
    }
    (out / "admission-recompute.json").write_text(json.dumps(report, indent=2) + "\n")

    from collections import Counter
    for name in summary:
        cnt = Counter()
        for f in summary[name]["flips"]:
            s = f["new_snapshot"] or {}
            cnt[(s.get("level"), s.get("total_levels"))] += 1
        print(f"{name} promoted continued states (level,total): {cnt.most_common(8)}")


if __name__ == "__main__":
    main()
