#!/usr/bin/env python3
"""Replay the recorded ih01 and tt03 actions through the new stall counter.

This is not a solve and not a score. It checks that the logged failures open
the window once, and that the old no-pixel-change batch counter does not open
on tt03.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/tmp/arc3-community-02152bc48068")
sys.path[:0] = [str(ROOT / "src"), "/private/tmp/arc3-018-sdk", "/private/tmp/arc3-018-check-deps"]

from arcengine import GameAction
from arc_agi import Arcade, OperationMode

from arc3_research.stall_probe import STALL_ACTIONS, StallTracker


BORDER = 4
BENCH = ROOT / "runs/022-community-dev-v4/baseline/benchmark.json"


def interior_changed(previous, new):
    if previous is None or new is None:
        return True
    rows = len(previous)
    cols = len(previous[0]) if rows else 0
    if rows != len(new) or rows <= 2 * BORDER or cols <= 2 * BORDER:
        return previous != new
    for row in range(BORDER, rows - BORDER):
        if previous[row][BORDER:cols - BORDER] != new[row][BORDER:cols - BORDER]:
            return True
    return False


def as_grid(frame):
    data = frame.tolist() if hasattr(frame, "tolist") else frame
    return [list(map(int, row)) for row in data]


def groups_of(history):
    groups = []
    current = []
    for index, item in enumerate(history):
        if item.get("generated_tokens") and current:
            groups.append(current)
            current = []
        current.append(index)
    if current:
        groups.append(current)
    return groups


def old_batch_fires(changed_flags, group_index):
    """Four consecutive model turns whose actions all leave the interior unchanged."""
    streak = 0
    for indexes in group_index:
        if any(changed_flags[index] for index in indexes):
            streak = 0
            continue
        streak += 1
        if streak >= 4:
            return indexes[-1]
    return None


def feed(tracker, game_id, results):
    fired_at = []
    for index, result in enumerate(results):
        note = tracker.observe(game_id, [result])
        if note:
            fired_at.append({"result_index": index, "actions_on_level": note["actions_on_level"],
                             "level_id": note["level_id"]})
    return fired_at


def replay(game_id, history):
    arcade = Arcade(environments_dir=str(SOURCE / "environment_files"),
                    operation_mode=OperationMode.OFFLINE,
                    recordings_dir=f"/tmp/arc3-replay-024-{game_id}")
    env = arcade.make(game_id, seed=200019, render_mode=None, save_recording=False)
    if env is None or env.reset() is None:
        raise RuntimeError(f"{game_id} did not reset")
    game = env._game
    previous = as_grid(game.camera.render(game.current_level.get_sprites()))
    changed_flags = []
    results = []
    heat_max = 0
    heaters_max = 0
    pad_hits = pad_misses = pad_offscreen = 0
    game_over_at = []
    target_counts = []
    for index, item in enumerate(history):
        name = item["action"]["id"]
        data = item["action"].get("data") or None
        action = GameAction.from_name(name)
        if name == "ACTION6" and hasattr(game, "_pads"):
            cell = game.camera.display_to_grid(int(data["x"]), int(data["y"]))
            if cell is None:
                pad_offscreen += 1
            elif tuple(cell) in game._pads:
                pad_hits += 1
            else:
                pad_misses += 1
        before_score = int(game._score)
        if env.step(action, data=data) is None:
            raise RuntimeError(f"{game_id} step {index} returned no frame")
        grid = as_grid(game.camera.render(game.current_level.get_sprites()))
        changed = interior_changed(previous, grid)
        previous = grid
        changed_flags.append(changed)
        if hasattr(game, "_h"):
            heat_max = max(heat_max, max(max(row) for row in game._h))
            heaters_max = max(heaters_max, len(game._on))
        if hasattr(game, "_targets"):
            target_counts.append(len(game._targets))
        over = "GAME_OVER" in str(game._state)
        if over:
            game_over_at.append(index)
        completed = int(game._score) > before_score
        results.append({
            "executed": True,
            "level": int(game.level_index) + 1,
            "executed_actions": [name],
            "level_completed": completed,
            "game_over": over,
            "done": False,
            "run_complete": False,
            "gameplay_changed": changed,
        })
    return {
        "results": results,
        "changed_flags": changed_flags,
        "levels_completed": int(game._score),
        "heat_max": heat_max,
        "heaters_max": heaters_max,
        "pad_hits": pad_hits,
        "pad_misses": pad_misses,
        "pad_offscreen": pad_offscreen,
        "game_over_at": game_over_at,
        "target_counts_head": target_counts[:40],
        "target_min": min(target_counts) if target_counts else None,
        "target_max": max(target_counts) if target_counts else None,
    }


def benchmark_split(history, actions_per_level):
    """Trust the benchmark's level split when the engine replay does not.

    The completing action is reported on the new level, matching the solver.
    """
    done = actions_per_level[0]
    results = []
    for index, item in enumerate(history):
        name = item["action"]["id"]
        if index < done - 1:
            results.append({"executed": True, "level": 1, "executed_actions": [name],
                            "level_completed": False, "game_over": False,
                            "done": False, "run_complete": False, "gameplay_changed": True})
        elif index == done - 1:
            results.append({"executed": True, "level": 2, "executed_actions": [name],
                            "level_completed": True, "game_over": False,
                            "done": False, "run_complete": False, "gameplay_changed": True})
        else:
            results.append({"executed": True, "level": 2, "executed_actions": [name],
                            "level_completed": False, "game_over": False,
                            "done": False, "run_complete": False, "gameplay_changed": True})
    return results


def once(fired, label):
    if len(fired) != 1:
        raise RuntimeError(f"{label} fired {len(fired)} times: {fired}")
    return fired[0]


def main() -> None:
    if not SOURCE.is_dir():
        raise RuntimeError("community source checkout is not at the pinned path")
    bench = json.loads(BENCH.read_text())
    runs = {game["game_id"]: game for game in bench["game_runs"]}
    report_games = {}
    for game_id in ("tt03-63be02fb", "ih01-v1"):
        history = runs[game_id]["history"]
        played = replay(game_id, history)
        engine_fire = once(feed(StallTracker(), game_id, played["results"]), game_id + " engine")
        groups = groups_of(history)
        old_at = old_batch_fires(played["changed_flags"], groups)
        batched_results = []
        cursor = 0
        for indexes in groups:
            chunk = played["results"][indexes[0]:indexes[-1] + 1]
            batched_results.append({
                "executed": True,
                "level": chunk[-1]["level"],
                "executed_actions": [item["executed_actions"][0] for item in chunk],
                "level_completed": any(item["level_completed"] for item in chunk),
                "game_over": any(item["game_over"] for item in chunk),
                "done": False,
                "run_complete": False,
                "gameplay_changed": any(item["gameplay_changed"] for item in chunk),
            })
            cursor += len(indexes)
        batch_fire = once(feed(StallTracker(), game_id, batched_results), game_id + " batches")
        entry = {
            "actions": len(history),
            "model_turns": len(groups),
            "interior_changed": sum(played["changed_flags"]),
            "interior_unchanged": len(played["changed_flags"]) - sum(played["changed_flags"]),
            "replay_levels_completed": played["levels_completed"],
            "benchmark_levels_completed": runs[game_id]["levels_completed"],
            "benchmark_actions_per_level": runs[game_id]["actions_per_level"],
            "old_no_change_batch_fired_at": old_at,
            "new_trigger": engine_fire,
            "new_trigger_when_counted_by_model_turn": batch_fire,
            "game_over_at": played["game_over_at"],
        }
        if game_id.startswith("tt03"):
            split = benchmark_split(history, runs[game_id]["actions_per_level"])
            split_fire = once(feed(StallTracker(), game_id, split), "tt03 benchmark split")
            entry.update({
                "target_min": played["target_min"],
                "target_max": played["target_max"],
                "targets_first_40": played["target_counts_head"],
                "benchmark_split_trigger": split_fire,
                "cause": "Every logged move changes the interior. New targets spawn every 10 moves, so the target count never reaches 0 in this replay (it rises while the original two are collected). The benchmark still records a level clear at action 29; counting that split separately still opens the window once, on the following unfinished level, and not on the 29-action level.",
            })
            if split_fire["result_index"] != runs[game_id]["actions_per_level"][0] + STALL_ACTIONS - 1:
                raise RuntimeError(f"benchmark split fired at the wrong action: {split_fire}")
            if old_at is not None:
                raise RuntimeError("the old pixel counter fired on tt03")
        else:
            entry.update({
                "pad_hits": played["pad_hits"],
                "pad_misses": played["pad_misses"],
                "pad_offscreen": played["pad_offscreen"],
                "heat_max_during_replay": played["heat_max"],
                "heaters_on_max": played["heaters_max"],
                "cause": "481 of 593 actions are clicks. 126 land on the two heater pads and both pads are on at some point; the hidden heat array reaches 6, above the win threshold of 4, but never across the whole grid. The pad sprite stays color 4 and the heat array is never drawn, so all 593 interiors match. Eight GAME_OVER results match eight RESET actions. The first life is 101 actions, so 64 is reached before the first death; several later lives are about 61. Death is not level progress, so it does not clear the count.",
            })
            if old_at is None:
                raise RuntimeError("expected the old pixel counter to fire on ih01's invisible state")
            if played["levels_completed"] != 0 or runs[game_id]["levels_completed"] != 0:
                raise RuntimeError("ih01 replay and benchmark disagree on levels")
        if engine_fire["actions_on_level"] < STALL_ACTIONS:
            raise RuntimeError(f"{game_id} trigger is below the action threshold")
        if len(feed(StallTracker(), game_id, played["results"])) != 1:
            raise RuntimeError(f"{game_id} did not fire exactly once")
        report_games[game_id] = entry

    report = {
        "status": "passed",
        "stall_actions": STALL_ACTIONS,
        "source": str(SOURCE),
        "trace": str(BENCH.relative_to(ROOT)),
        "games": report_games,
        "limits": [
            "Replay uses the logged action ids on this checkout. It does not call the model.",
            "tt03's benchmark level split was not reproduced by the engine replay and is counted as a second case.",
            "A triggered window is not evidence that the three probe actions will raise the score.",
        ],
    }
    out = ROOT / "experiments/024-level-stall-cpu"
    out.mkdir(parents=True, exist_ok=True)
    (out / "replay-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "passed", "triggers": {
        game_id: {"engine": row["new_trigger"], "old": row["old_no_change_batch_fired_at"]}
        for game_id, row in report_games.items()
    }}, indent=2))


if __name__ == "__main__":
    main()
