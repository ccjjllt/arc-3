#!/usr/bin/env python3
"""025: offline recomputation of initial-admission order (CPU-only, read-only).

For each selection event in the 4 saved scheduler-observer.json logs
(014 baseline/tail_80k, 016 baseline/pace_1x), replace every null-snapshot
(initial admission, original priority 2000000-100*idx) with the 009 original
priority_value of PrioritySnapshot(level=1, actions=0, tokens=0.0,
cost_multiplier=1.0, total_levels=number_of_levels), keeping
tail_lookup="remaining", normalize_score=True and the contemporaneous
tail_fraction (TAIL_FADE=1, fraction 0.2 in all four arms). Started
candidates keep their recorded priorities. Winner = max priority,
tie-break by smaller token (heap order). No GPU, no model calls, no
replay of game code; JSON is only read.
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
    ("014-tail_80k", "runs/014-tail-allocation/tail_80k"),
    ("016-baseline", "runs/016-pace-allocation-jiyujia/baseline"),
    ("016-pace_1x", "runs/016-pace-allocation-jiyujia/pace_1x"),
]

FADE_FRACTION = 0.2


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
        levels = {g["game_id"]: g["number_of_levels"]
                  for g in meta.get("game_results", [])}
        n_sel = n_mixed = n_flip = 0
        flips = []
        first_mixed = None
        for e in obs["events"]:
            if e.get("kind") != "selection":
                continue
            n_sel += 1
            cands = e.get("candidates", [])
            has_null = any(c.get("snapshot") is None for c in cands)
            has_started = any(c.get("snapshot") is not None for c in cands)
            if not (has_null and has_started):
                continue
            n_mixed += 1
            if first_mixed is None:
                first_mixed = e["seq"]
            tf = tail_fraction_of(e)
            orig_best = max(cands, key=lambda c: (c["priority"], -c["token"]))
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
                    "tail_fraction": tf,
                })
        summary[name] = {
            "selections": n_sel,
            "mixed": n_mixed,
            "flipped": n_flip,
            "flip_rate_mixed": (n_flip / n_mixed) if n_mixed else None,
            "first_mixed_seq": first_mixed,
            "flips": flips,
        }
        print(f"{name}: selections={n_sel} mixed={n_mixed} flipped={n_flip} "
              f"rate={summary[name]['flip_rate_mixed']}")
    out = ROOT / "experiments/025-admission-cpu"
    out.mkdir(parents=True, exist_ok=True)
    (out / "admission-recompute.json").write_text(json.dumps(summary, indent=2) + "\n")

    # distribution of promoted continued-game states
    from collections import Counter
    for name in summary:
        cnt = Counter()
        for f in summary[name]["flips"]:
            s = f["new_snapshot"] or {}
            cnt[(s.get("level"), s.get("total_levels"))] += 1
        print(f"{name} promoted continued states (level,total): {cnt.most_common(8)}")


if __name__ == "__main__":
    main()
