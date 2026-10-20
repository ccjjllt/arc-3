#!/usr/bin/env python3
"""028: CPU pin-down of new repair cuts (no model, no GPU).

Cuts under test (from docs/handoff/027-028-next-round.md + research/028 design):
  ft09-0d8bbf25: cum 26 / rec22 (L3 step27) AND cum 27 / rec30 (L3 step28)
  tr87-cd924810: cum 220 / rec104 (L5 step221, final record)

For each cut, verify:
  1. Deterministic replay: same version + same seed + fixed recording dir,
     replayed TWICE; full per-action state triples + final grid hash identical.
  2. Checkpoint alignment: step == replay_steps + 1 + deaths (deaths==0 here).
  3. Legal tool boundary: cut record is a `request` event whose latest user
     message carries the cum/step; the previous tool call in that record has
     returned; the next request has not been issued at cut time (next record
     is the model's response, or there is no next record for the final cut).
  4. Failure evidence present WITHOUT writing the correct answer:
     ft09 rec30 has WOW transcription in code + 15-action sweep executed +
     explicit mismatch list; rec22 has WOW + sweep but no explicit mismatch
     yet. tr87 rec104 tool output has HITS [] immediately before final user.
  5. ID+data comparison demo: show that ID-only comparison misses coordinate
     differences (ft09 all ACTION6 with distinct coords).

No repair model calls are made here. GPU budget used: 0.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
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

BENCH = {
    "ft09-0d8bbf25": "runs/015-native-adoption/baseline/benchmark.json",
    "tr87-cd924810": "runs/016-pace-allocation-jiyujia/pace_1x/benchmark.json",
}
REQ = {
    "ft09-0d8bbf25": "runs/015-native-adoption/baseline/ft09-0d8bbf25_p0_requests.jsonl",
    "tr87-cd924810": "runs/016-pace-allocation-jiyujia/pace_1x/tr87-cd924810_p0_requests.jsonl",
}
# (game, cum, rec, step, level)
CUTS = [
    ("ft09-0d8bbf25", 26, 22, 27, 3),
    ("ft09-0d8bbf25", 27, 30, 28, 3),
    ("tr87-cd924810", 220, 104, 221, 5),
]


def checkpoints(requests_path: Path):
    out, cum, seen = [], 0, set()
    with open(requests_path) as f:
        for idx, line in enumerate(f):
            d = json.loads(line)
            for m in reversed(d.get("messages", [])):
                if m.get("role") != "user":
                    continue
                content = m.get("content", "")
                text = ("".join(p.get("text", "") for p in content
                                if isinstance(p, dict) and p.get("type") == "text")
                        if isinstance(content, list) else str(content))
                em, sm = EXEC_RE.search(text), STEP_RE.search(text)
                if em and sm:
                    h = hashlib.md5(text.encode()).hexdigest()
                    if h not in seen:
                        seen.add(h)
                        cum += int(em.group(1))
                        out.append((cum, int(sm.group(1)), int(sm.group(2)), idx))
                break
    return out


def replay_states(game_id: str, history, cut: int, rec_dir: str):
    arcade = Arcade(environments_dir=str(ENV_DIR),
                    operation_mode=OperationMode.OFFLINE,
                    recordings_dir=rec_dir)
    env = arcade.make(game_id, seed=0, render_mode=None, save_recording=False)
    if env is None or env.reset() is None:
        raise RuntimeError(f"{game_id} did not reset")
    game = env._game
    states, deaths = [], 0
    for item in history[:cut]:
        name = item["action"]["id"]
        data = item["action"].get("data") or None
        if env.step(GameAction.from_name(name), data=data) is None:
            raise RuntimeError(f"{game_id} step returned no frame")
        if "GAME_OVER" in str(game._state):
            deaths += 1
        states.append((int(game.level_index) + 1, len(states) + 1, deaths))
    raw = game.camera.render(game.current_level.get_sprites())
    grid = tuple(tuple(int(c) for c in row) for row in
                 (raw.tolist() if hasattr(raw, "tolist") else raw))
    gh = hashlib.sha256(json.dumps(grid).encode()).hexdigest()
    return states, gh


def latest_user_text(record: dict) -> str:
    for m in reversed(record.get("messages", [])):
        if m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, list):
                return "".join(p.get("text", "") for p in c
                               if isinstance(p, dict) and p.get("type") == "text")
            return str(c)
    return ""


def main() -> None:
    out_dir = ROOT / "experiments/028-minimal-repair"
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"cuts": {}, "id_data_demo": {}, "gpu_calls": 0,
                    "gpu_seconds": 0}
    failures: list[str] = []

    for game_id, cum, rec, step, level in CUTS:
        key = f"{game_id}@cum{cum}_rec{rec}"
        bench = json.loads((ROOT / BENCH[game_id]).read_text())
        history = next(g["history"] for g in bench["game_runs"]
                       if g["game_id"] == game_id)
        req_lines = (ROOT / REQ[game_id]).read_text().splitlines()
        record = json.loads(req_lines[rec])
        entry: dict = {"cum": cum, "rec": rec, "step": step, "level": level,
                       "benchmark_actions": len(history),
                       "total_records": len(req_lines)}

        # 1. double replay determinism (same version + same seed + fixed dir)
        s1, g1 = replay_states(game_id, history, cum,
                               f"/tmp/arc3-replay-028-{game_id}-{cum}a")
        s2, g2 = replay_states(game_id, history, cum,
                               f"/tmp/arc3-replay-028-{game_id}-{cum}b")
        entry["replay_twice_identical"] = (s1 == s2 and g1 == g2)
        entry["final_grid_sha256"] = g1
        entry["replay_states_match"] = (s1 == s2)
        if not entry["replay_twice_identical"]:
            failures.append(f"{key}: double replay differs")

        # 2. checkpoint alignment for this cut
        cps = checkpoints(ROOT / REQ[game_id])
        hit = [c for c in cps if c[0] == cum and c[3] == rec]
        entry["checkpoint_found"] = len(hit) == 1
        if hit:
            _, cstep, clevel, _ = hit[0]
            rl, rs, rd = s1[cum - 1] if cum else (1, 0, 0)
            entry["logged"] = [cstep, clevel]
            entry["replay"] = [rl, rs, rd]
            entry["step_rule_match"] = (rl == clevel == level
                                        and rs + 1 + rd == cstep == step)
            if not entry["step_rule_match"]:
                failures.append(f"{key}: step rule mismatch")
        else:
            entry["step_rule_match"] = False
            failures.append(f"{key}: checkpoint not found")

        # 3. legal tool boundary: request event, prev tool returned,
        #    next request not yet issued
        entry["event"] = record.get("event")
        msgs = record.get("messages", [])
        # previous tool = last tool-role message in this record
        prev_tools = [m for m in msgs if m.get("role") == "tool"]
        entry["prev_tool_count"] = len(prev_tools)
        entry["prev_tool_returned"] = bool(prev_tools) and (
            "returncode" in prev_tools[-1].get("content", "")
            or "error" in prev_tools[-1].get("content", ""))
        last_user = latest_user_text(record)
        em, sm = EXEC_RE.search(last_user), STEP_RE.search(last_user)
        entry["latest_user_has_cum_step"] = bool(em and sm)
        if em and sm:
            # recompute cum up to and including this record
            cum_check, seen = 0, set()
            for idx in range(rec + 1):
                d = json.loads(req_lines[idx])
                for m in reversed(d.get("messages", [])):
                    if m.get("role") != "user":
                        continue
                    c = m.get("content", "")
                    t = ("".join(p.get("text", "") for p in c
                                 if isinstance(p, dict) and p.get("type") == "text")
                         if isinstance(c, list) else str(c))
                    e2, s2m = EXEC_RE.search(t), STEP_RE.search(t)
                    if e2 and s2m:
                        h = hashlib.md5(t.encode()).hexdigest()
                        if h not in seen:
                            seen.add(h)
                            cum_check += int(e2.group(1))
                    break
            entry["cum_recomputed"] = cum_check
            entry["cum_matches"] = (cum_check == cum)
            if not entry["cum_matches"]:
                failures.append(f"{key}: cum recompute mismatch")
        if rec + 1 < len(req_lines):
            nxt = json.loads(req_lines[rec + 1])
            entry["next_event"] = nxt.get("event")
            entry["next_is_response"] = (nxt.get("event") == "response")
        else:
            entry["next_event"] = None
            entry["next_is_response"] = None  # final record: nothing after
            entry["is_final_record"] = True
        entry["legal_boundary"] = (
            entry["event"] == "request"
            and entry["prev_tool_returned"]
            and entry["latest_user_has_cum_step"]
            and (entry.get("next_is_response") is True
                 or entry.get("is_final_record") is True))
        if not entry["legal_boundary"]:
            failures.append(f"{key}: not a legal tool boundary")

        # 4. failure evidence present, no correct answer written
        parts = []
        for m in msgs:
            if m.get("role") not in ("tool", "user"):
                continue
            c = m.get("content", "")
            if isinstance(c, str):
                parts.append(c)
            else:
                parts.append("".join(
                    p.get("text", "") for p in c
                    if isinstance(p, dict) and p.get("type") == "text"))
        full_text = "\n".join(parts)
        if game_id.startswith("ft09"):
            entry["evidence_wow_present"] = ("WOW" in full_text)
            entry["evidence_sweep_15"] = ("batch of 15 actions, 15 executed"
                                          in full_text)
            entry["evidence_mismatch_list"] = ("mismatches vs my target" in full_text)
            if cum == 26:
                # rec22: WOW + sweep present, explicit mismatch not yet
                entry["evidence_ok"] = (entry["evidence_wow_present"]
                                        and entry["evidence_sweep_15"])
            else:
                entry["evidence_ok"] = (entry["evidence_wow_present"]
                                        and entry["evidence_sweep_15"]
                                        and entry["evidence_mismatch_list"])
            entry["writes_correct_answer"] = False  # by construction: only
            # raw evidence locations recorded, no pattern/pixel conclusions
        else:
            entry["evidence_hits_empty"] = ("HITS []" in full_text)
            entry["evidence_ok"] = entry["evidence_hits_empty"]
            entry["writes_correct_answer"] = False
        if not entry["evidence_ok"]:
            failures.append(f"{key}: failure evidence missing")

        # history actions carry ID+data (needed for repair comparison)
        sample = history[:cum][-3:]
        entry["sample_actions_have_data"] = all(
            isinstance(a.get("action", {}).get("data"), dict) or
            a.get("action", {}).get("data") is None for a in sample)
        report["cuts"][key] = entry
        print(f"{key}: replay2x={entry['replay_twice_identical']} "
              f"step_rule={entry['step_rule_match']} "
              f"boundary={entry['legal_boundary']} "
              f"evidence={entry['evidence_ok']} grid={g1[:12]}")

    # 5. ID+data demo: ft09 first 11 actions share ID ACTION6 but differ in data;
    #    ID-only comparison (026 v6 bug) reports no divergence.
    bench = json.loads((ROOT / BENCH["ft09-0d8bbf25"]).read_text())
    hist = next(g["history"] for g in bench["game_runs"]
                if g["game_id"] == "ft09-0d8bbf25")
    first11 = [(a["action"]["id"], json.dumps(a["action"].get("data"),
                                              sort_keys=True))
               for a in hist[:11]]
    ids_same = len({i for i, _ in first11}) == 1
    data_same = len(set(first11)) == 1
    report["id_data_demo"] = {
        "ft09_first11_ids_same": ids_same,
        "ft09_first11_id_data_same": data_same,
        "id_only_misses_divergence": bool(ids_same and not data_same),
        "note": "026 v6 first_post_T_actions compared ID only; same ID with "
                "different coords was scored as no-divergence. Repair "
                "comparison must use ID+data.",
    }
    print(f"ID+data demo: ids_same={ids_same} id_data_same={data_same} "
          f"miss={report['id_data_demo']['id_only_misses_divergence']}")
    if not report["id_data_demo"]["id_only_misses_divergence"]:
        failures.append("id-data demo: expected ID-only miss not shown")

    report["failures"] = failures
    report["pass"] = not failures
    (out_dir / "replay-fidelity.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(f"Wrote {out_dir / 'replay-fidelity.json'} pass={report['pass']}")
    if failures:
        print("FAILURES:", failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
