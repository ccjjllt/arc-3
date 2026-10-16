"""Fresh-process evaluation of one arm on every public competition game."""
import argparse
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pickle
import re
import time


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory", type=int, choices=(0, 1), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--seed", type=int, default=20261012)
    args = parser.parse_args()
    os.environ.update(ARC3_SCOPED_MEMORY=str(args.memory), LOCAL_ANALYZER_SEED=str(args.seed),
                      TAAF_RUN_AS_SUBMISSION="0", TAAF_MINIMAL_DIAGNOSTICS="0")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    os.environ["RECORDINGS_DIR"] = str(output / "recordings")
    from input_checks import wait_for_inputs
    input_paths = wait_for_inputs()
    import arc_agi
    import taaf.game_api

    bundle = Path("/kaggle/taaf-kaggle-source-share")
    with (bundle / "deploy_target.pkl").open("rb") as f:
        target = pickle.load(f)
    target.actual_run_as_submission = False
    target.is_competition_rerun = False
    with (bundle / "benchmark_initial.pkl").open("rb") as f:
        bm = pickle.load(f)
    env_dir = input_paths["environment_files"]
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
    ids = sorted(env.game_id for env in arcade.available_environments)
    if len(ids) != 25:
        raise RuntimeError(f"Expected all 25 public games; got {len(ids)}")
    bm.games = [taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec) for game_id in ids]
    bm.job_dir = output
    bm.label = "scoped-memory" if args.memory else "baseline"
    bm.n_passes = 1
    bm.game_weights = None
    bm.solver.max_runtime_s_per_game = args.seconds
    bm.solver.analyzer_timeout = 900.0
    bm.solver.concurrency = 25
    bm.solver.max_actions_per_game = None
    bm.solver.save_request_logs = False
    bm.periodic_save_interval_s = 300
    (output / "git_status.txt").write_text((bundle / "git_status.txt").read_text())
    started = time.monotonic()
    await bm.run(soft_end_time=datetime.now() + timedelta(seconds=args.seconds + 60),
                 runtime_environment=target, minimal_diagnostics=False)
    elapsed = time.monotonic() - started
    games = []
    for game in bm.game_runs:
        note = str(game.solver_note or "")
        token_match = re.search(r"tokens=(\d+)", note)
        tokens = int(getattr(game, "final_generated_tokens", 0) or 0)
        if not tokens and token_match:
            tokens = int(token_match[1])
        games.append({"game_id": game.game_id, "score": game.final_score,
                      "levels_completed": game.levels_completed, "total_levels": game.number_of_levels,
                      "actions": sum(game.actions_per_level), "state": game.state,
                      "generated_tokens": tokens, "note": note})
    invalid = [g["game_id"] for g in games if g["score"] is None or g["state"] == "crashed" or "analyzer failed" in g["note"]]
    if len(games) != len(ids) or sum(g["generated_tokens"] for g in games) == 0:
        invalid.append("incomplete game coverage or no generated tokens")
    memory_reports = 0
    memory_games = []
    error_reports = 0
    for path in output.rglob("*_events.jsonl"):
        # Only artifact logs carry full per-turn transcripts; pointer files do not.
        count = 0
        for line in path.open(encoding="utf-8"):
            event = json.loads(line)
            transcript = event.get("transcript", "")
            count += transcript.count('"scratch_saved_keys"')
            error_reports += transcript.count("NameError:")
        if count:
            memory_games.append(path.name)
            memory_reports += count
    result = {"arm": bm.label, "memory_enabled": bool(args.memory), "seed": args.seed,
              "valid": not invalid, "invalid_reasons": invalid, "game_ids": ids,
              "game_budget_seconds": args.seconds, "elapsed_seconds": elapsed,
              "mean_score": sum(g["score"] or 0 for g in games) / len(ids),
              "generated_tokens": sum(g["generated_tokens"] for g in games),
              "memory_saved_reports": memory_reports, "games_with_saved_memory": memory_games,
              "name_error_reports": error_reports, "games": games}
    (output / "arm-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("ARM_RESULT", json.dumps({k: v for k, v in result.items() if k not in ("games", "game_ids")}), flush=True)
    if invalid:
        raise RuntimeError(f"Invalid evaluation: {invalid}")


if __name__ == "__main__":
    asyncio.run(main())
