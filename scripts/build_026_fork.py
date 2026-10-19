#!/usr/bin/env python3
"""026: build host-side fork inputs for failure prefixes (CPU-only).

For each prefix and its cut point (cumulative executed actions):
1. replay benchmark actions offline to the cut,
2. write _tool_runtime_state.json (Frame/HistoryEntry round-tripped),
3. snapshot the conversation (cut record messages) and kept-function names,
4. emit fork-manifest.json.

This is the deterministic half of the 026 fork. Model continuation (A/B)
needs the GPU server and is NOT run here.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"),
                str(ROOT / "research/runtime-bundle/src/ARC3-Inference"),
                "/private/tmp/arc3-018-sdk",
                "/private/tmp/arc3-018-check-deps"]

from arcengine import GameAction
from arc_agi import Arcade, OperationMode
from inference.agent.runtime_state import (Frame, HistoryEntry,
                                           load_runtime_state,
                                           write_runtime_state)

ENV_DIR = ROOT / "research/data/extracted/environment_files"

# game_id -> (benchmark, requests, cut_cum_executed, note)
FORKS = {
    "ft09-0d8bbf25": ("runs/015-native-adoption/baseline/benchmark.json",
                      "runs/015-native-adoption/baseline/ft09-0d8bbf25_p0_requests.jsonl",
                      11, "L3 entry; legend mis-encode from analysis_step 5"),
    "tr87-cd924810": ("runs/016-pace-allocation-jiyujia/pace_1x/benchmark.json",
                      "runs/016-pace-allocation-jiyujia/pace_1x/tr87-cd924810_p0_requests.jsonl",
                      132, "L5; crop error range rec 65-105; HITS [] at rec 104"),
    "m0r0-492f87ba": ("runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
                      "runs/016-pace-allocation-jiyujia/baseline/m0r0-492f87ba_p0_requests.jsonl",
                      22, "L1 step23; 18-loop with step-2 mismatch follows"),
    "r11l-495a7899": ("runs/016-pace-allocation-jiyujia/baseline/benchmark.json",
                      "runs/016-pace-allocation-jiyujia/baseline/r11l-495a7899_p0_requests.jsonl",
                      40, "L3 step41; cross-level control"),
}

KEPT_RE = re.compile(r"Your retained functions from earlier Python calls in this game: ([^.]*)\.",
                     re.S)


def main() -> None:
    out_root = ROOT / "experiments/026-repair-cpu"
    manifest = {}
    for game_id, (bench_rel, req_rel, cut, note) in FORKS.items():
        bench = json.loads((ROOT / bench_rel).read_text())
        history = next(g["history"] for g in bench["game_runs"] if g["game_id"] == game_id)
        assert len(history) >= cut, (game_id, len(history), cut)
        arcade = Arcade(environments_dir=str(ENV_DIR),
                        operation_mode=OperationMode.OFFLINE,
                        recordings_dir=f"/tmp/arc3-fork-026-{game_id}")
        env = arcade.make(game_id, seed=0, render_mode=None, save_recording=False)
        assert env is not None and env.reset() is not None
        game = env._game
        from arcengine import GameAction as GA
        entries: list[HistoryEntry] = []
        current: Frame | None = None
        for item in history[:cut]:
            a = GA.from_name(item["action"]["id"])
            env.step(a, data=item["action"].get("data") or None)
            from inference.agent.runtime_state import normalize_grid
            raw = game.camera.render(game.current_level.get_sprites())
            grid = normalize_grid(raw.tolist() if hasattr(raw, "tolist") else raw)
            current = Frame(grid=grid, step=len(entries) + 1,
                            level=int(game.level_index) + 1)
            entries.append(HistoryEntry(action=item["action"]["id"],
                                        frame=current, result={}))
        out = out_root / f"fork-{game_id}"
        out.mkdir(parents=True, exist_ok=True)
        sp = out / "tool_runtime_state.json"
        write_runtime_state(sp, current_frame=current, history=entries)
        back_frame, back_hist = load_runtime_state(sp)
        assert back_frame is not None and back_frame.step == cut
        assert len(back_hist) == cut
        assert back_frame.grid == current.grid
        # conversation + kept names from the cut record
        with open(ROOT / req_rel) as f:
            records = [json.loads(line) for line in f]
        cum, target_rec = 0, None
        seen = set()
        import re as _re
        exec_re = _re.compile(r"executed\s+(\d+)\s+actions?")
        for idx, d in enumerate(records):
            for m in reversed(d.get("messages", [])):
                if m.get("role") != "user":
                    continue
                content = m.get("content", "")
                text = "".join(p.get("text", "") for p in content
                               if isinstance(p, dict) and p.get("type") == "text") \
                    if isinstance(content, list) else str(content)
                em = exec_re.search(text)
                if not em:
                    break
                h = hashlib.md5(text.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    cum += int(em.group(1))
                break
            if cum >= cut:
                target_rec = idx
                break
        conv = records[target_rec]["messages"]
        kept = []
        for m in conv:
            if m.get("role") != "user":
                continue
            content = m.get("content", "")
            text = "".join(p.get("text", "") for p in content
                           if isinstance(p, dict) and p.get("type") == "text") \
                if isinstance(content, list) else str(content)
            mm = KEPT_RE.search(text)
            if mm:
                kept = [x.strip().strip("`") for x in mm.group(1).split(",")]
                break
        (out / "conversation.json").write_text(json.dumps(conv, indent=1)[:200000] + "\n")
        (out / "kept-functions.json").write_text(json.dumps({"names": kept,
            "note": "names only: exact kept sources were not persisted in request logs; B-branch repairs must redefine helpers with data args"}, indent=2) + "\n")
        manifest[game_id] = {"cut_cum": cut, "cut_record": target_rec,
                             "note": note, "state_file": str(sp.relative_to(ROOT)),
                             "frames": len(entries), "roundtrip_ok": True,
                             "kept_names": kept,
                             "limit": "exact _kept_functions sources not in logs; B must be self-contained"}
        print(f"{game_id}: cut={cut} rec={target_rec} frames={len(entries)} kept={kept}")
    (out_root / "fork-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
