#!/usr/bin/env python3
"""026: deterministic replay of failure prefixes (CPU-only, read-only).

For each prefix (game + saved benchmark history + saved request log):
replay the exact executed benchmark actions in an offline Arcade env from
reset, and check every request-log checkpoint
("... executed N actions ... Current state: step S, level L")
against replay state after the same cumulative number of env steps.

No model calls, no GPU. Mismatches are reported, never hidden.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "research/data/extracted/environment_files"
sys.path[:0] = [str(ROOT / "src"), "/private/tmp/arc3-018-sdk",
                "/private/tmp/arc3-018-check-deps"]

from arcengine import GameAction
from arc_agi import Arcade, OperationMode

STEP_RE = re.compile(r"Current state:\s*step\s+(\d+),\s*level\s+(\d+)", re.I)
EXEC_RE = re.compile(r"executed\s+(\d+)\s+actions?", re.I)

PREFIXES = [
    ("ft09-0d8bbf25", "runs/015-native-adoption/baseline/benchmark.json",
     "runs/015-native-adoption/baseline/ft09-0d8bbf25_p0_requests.jsonl"),
    ("tr87-cd924810", "runs/016-pace-allocation-jiyujia/pace_1x/benchmark.json",
     "runs/016-pace-allocation-jiyujia/pace_1x/tr87-cd924810_p0_requests.jsonl"),
    ("m0r0-492f87ba", "runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
     "runs/016-pace-allocation-jiyujia/baseline/m0r0-492f87ba_p0_requests.jsonl"),
    ("r11l-495a7899", "runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
     "runs/016-pace-allocation-jiyujia/baseline/r11l-495a7899_p0_requests.jsonl"),
]


def checkpoints(requests_path: Path):
    """Return [(cum_executed, step, level, record_idx)] in log order.

    Messages accumulate across records, so dedupe by hash: each new user
    message is counted once (request + response + retries repeat it).
    """
    out = []
    cum = 0
    seen = set()
    with open(requests_path) as f:
        for idx, line in enumerate(f):
            d = json.loads(line)
            # only the LATEST user message can be new in this record.
            for m in reversed(d.get("messages", [])):
                if m.get("role") != "user":
                    continue
                content = m.get("content", "")
                text = "".join(p.get("text", "") for p in content
                               if isinstance(p, dict) and p.get("type") == "text") \
                    if isinstance(content, list) else str(content)
                em = EXEC_RE.search(text)
                sm = STEP_RE.search(text)
                if em and sm:
                    import hashlib
                    h = hashlib.md5(text.encode()).hexdigest()
                    if h not in seen:
                        seen.add(h)
                        cum += int(em.group(1))
                        out.append((cum, int(sm.group(1)), int(sm.group(2)), idx))
                break
    return out
    return out


def replay(game_id: str, history):
    arcade = Arcade(environments_dir=str(ENV_DIR),
                    operation_mode=OperationMode.OFFLINE,
                    recordings_dir=f"/tmp/arc3-replay-026-{game_id}")
    env = arcade.make(game_id, seed=0, render_mode=None, save_recording=False)
    if env is None or env.reset() is None:
        raise RuntimeError(f"{game_id} did not reset")
    game = env._game
    states = []  # (level, steps_done, deaths_so_far) after each action
    deaths = 0
    for item in history:
        name = item["action"]["id"]
        data = item["action"].get("data") or None
        action = GameAction.from_name(name)
        if env.step(action, data=data) is None:
            raise RuntimeError(f"{game_id} step returned no frame")
        if "GAME_OVER" in str(game._state):
            deaths += 1
        states.append((int(game.level_index) + 1, len(states) + 1, deaths))
    return states


def main() -> None:
    full = {}
    for game_id, bench_rel, req_rel in PREFIXES:
        bench = json.loads((ROOT / bench_rel).read_text())
        runs = {g["game_id"]: g for g in bench["game_runs"]}
        history = runs[game_id]["history"]
        cps = checkpoints(ROOT / req_rel)
        states = replay(game_id, history)
        n_actions = len(history)
        match = mismatch = 0
        bad = []
        max_step_seen = 0
        for cum, step, level, idx in cps:
            max_step_seen = max(max_step_seen, step)
            if cum > n_actions:
                # checkpoint beyond benchmark actions (e.g. trailing summary):
                # count separately, do not force-fit
                bad.append({"record": idx, "cum": cum, "beyond_history": n_actions,
                            "logged": [step, level]})
                mismatch += 1
                continue
            rl, rs, rd = states[cum - 1] if cum else (1, 0, 0)
            # Logged step = len(run.history): replay env steps + 1 initial
            # entry + one auto-reset bookkeeping entry per death observed so
            # far. Level must match exactly; step must match under that rule.
            if rl == level and rs + 1 + rd == step:
                match += 1
            else:
                mismatch += 1
                if len(bad) < 8:
                    bad.append({"record": idx, "cum": cum, "logged": [step, level],
                                "replay": [rl, rs, rd]})
        full[game_id] = {
            "benchmark_actions": n_actions,
            "checkpoints": len(cps),
            "exact_match": match,
            "mismatch": mismatch,
            "max_logged_step": max_step_seen,
            "first_mismatches": bad,
        }
        print(f"{game_id}: actions={n_actions} checkpoints={len(cps)} "
              f"exact={match} mismatch={mismatch}")
        for b in bad[:4]:
            print("   ", b)
    out = ROOT / "experiments/026-repair-cpu"
    out.mkdir(parents=True, exist_ok=True)
    (out / "replay-fidelity.json").write_text(json.dumps(full, indent=2) + "\n")


if __name__ == "__main__":
    main()
