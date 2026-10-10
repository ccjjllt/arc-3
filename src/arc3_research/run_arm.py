"""Run one public OFFLINE research arm against an already loaded model server.

The notebook owns SGLang and the overall GPU deadline. Each arm gets a fresh
CPU process so its scheduler clocks, imported switches and agent histories do
not leak into the next arm. This module never launches or stops the model.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import signal
import sys
import threading
import time
import traceback
from typing import Any


def _stage(name: str, **fields: Any) -> None:
    print("[ARC3_RESEARCH] " + json.dumps({
        "stage": name,
        "utc": datetime.now(timezone.utc).isoformat(),
        **fields,
    }, ensure_ascii=False, default=str), flush=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                    default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _source_paths(bundle_dir: Path) -> list[str]:
    return [str(candidate) for repo in sorted((bundle_dir / "src").iterdir(),
                                              reverse=True)
            for candidate in (repo / "src", repo) if candidate.is_dir()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _game_ids(source: str) -> list[str]:
    path = Path(source)
    if "," in source or not path.is_file():
        value = [part.strip() for part in source.split(",")]
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    values = value.get("game_ids") if isinstance(value, dict) else value
    if not isinstance(values, list) or not values:
        raise ValueError("game-list must be a nonempty array or {game_ids: [...]}.")
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise ValueError("game-list entries must be nonempty game ID strings.")
    if len(set(values)) != len(values):
        raise ValueError("game-list contains duplicate IDs.")
    return values


def run_arm(args: argparse.Namespace) -> int:
    started = time.monotonic()
    job_dir = args.working_dir.resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "arm": args.arm,
        "status": "initializing",
        "operation_mode": "OFFLINE",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "budget_seconds": args.budget_seconds,
        "soft_deadline_grace_seconds": 0,
        "cancel_drain_timeout_seconds": 120,
        "active_streams": 10,
        "warmup_action_games": 0,
        "model_server_owned_by_runner": False,
    }
    metadata_path = job_dir / "arm-metadata.json"
    patch = None
    bm = None
    exit_code = 0
    _write_json(metadata_path, metadata)
    _stage("arm_initializing", arm=args.arm, working_dir=job_dir,
           budget_seconds=args.budget_seconds)
    try:
        if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}:
            raise RuntimeError("run_arm only supports public OFFLINE research.")
        if args.budget_seconds <= 0:
            raise ValueError("budget-seconds must be positive.")
        requested_ids = _game_ids(args.game_list)
        bundle_dir = args.bundle_dir.resolve()
        sys.path[:0] = _source_paths(bundle_dir)
        # The launcher's baseline setup_env must already be in this process.
        os.environ["TAAF_RUN_AS_SUBMISSION"] = "0"
        os.environ["TAAF_MINIMAL_DIAGNOSTICS"] = "0"
        os.environ["ARC3_MAX_ACTIVE_STREAMS"] = "10"
        # This runner is OFFLINE-only and its parent waits for server readiness.
        # The competition first-action warmup would add a nondeterministic RESET
        # to whichever game first claims a slot, so omit it in future research.
        os.environ["ARC3_WARMUP_ACTION_GAMES"] = "0"
        os.environ["RECORDINGS_DIR"] = str(job_dir / "server_recording")
        os.environ["ONLY_RESET_LEVELS"] = "true"

        import arc_agi
        import taaf.game_api
        from arc3_research.goal_evidence import install_goal_evidence

        env_dir = Path(os.environ.get(
            "ARC3_RESEARCH_ENV_DIR",
            "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/environment_files",
        )).resolve()
        if not env_dir.is_dir():
            raise FileNotFoundError(f"Public environment directory not found: {env_dir}")
        arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
                                environments_dir=str(env_dir))
        available_ids = [item.game_id for item in arcade.available_environments]
        ids = []
        for requested in requested_ids:
            matches = ([requested] if requested in available_ids else
                       [game_id for game_id in available_ids if game_id.startswith(requested)])
            if len(matches) != 1:
                raise ValueError(f"Expected one public environment for {requested!r}; got {matches}")
            ids.append(matches[0])
        if len(set(ids)) != len(ids):
            raise ValueError("Different requested prefixes resolved to the same game ID.")
        with (bundle_dir / "deploy_target.pkl").open("rb") as file:
            target = pickle.load(file)
        target.actual_run_as_submission = False
        target.is_competition_rerun = False
        target.run_as_submission = False
        with (bundle_dir / "benchmark_initial.pkl").open("rb") as file:
            bm = pickle.load(file)
        bm.label = f"003-{args.arm}"
        bm.job_dir = job_dir
        bm.n_passes = 1
        bm.game_weights = None
        bm.solver.start_local_server = False
        bm.solver.concurrency = len(ids)
        bm.solver.max_runtime_s_per_game = float(args.budget_seconds)
        bm.solver.max_generated_tokens_per_game = None
        bm.solver.analyzer_timeout = 900.0
        bm.solver.max_actions_per_game = None
        bm.solver.save_request_logs = True
        bm.solver.cancel_drain_timeout_s = 120.0
        spec = taaf.game_api.ArcadeSpec(
            operation_mode=arc_agi.OperationMode.OFFLINE,
            environments_dir=str(env_dir),
        )
        bm.games = [taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec)
                    for game_id in ids]
        patch = install_goal_evidence(enabled=args.arm == "goal_evidence")
        git_status = bundle_dir / "git_status.txt"
        if git_status.is_file():
            (job_dir / "git_status.txt").write_bytes(git_status.read_bytes())
        relevant_env = {key: value for key, value in os.environ.items()
                        if key.startswith(("ARC3_", "MULTIMODAL_"))
                        and not any(word in key.upper() for word in ("KEY", "SECRET", "TOKEN"))}
        # Names ending in TOKENS are benign budgets; retain those explicitly.
        for key in ("ARC3_CONTEXT_DRAIN_TOKENS", "LOCAL_ANALYZER_MAX_OUTPUT",
                    "LOCAL_ANALYZER_TEMPERATURE", "LOCAL_ANALYZER_TOP_P",
                    "LOCAL_ANALYZER_TOP_K", "LOCAL_ANALYZER_CONTEXT_WINDOW"):
            if key in os.environ:
                relevant_env[key] = os.environ[key]
        metadata.update({
            "status": "running",
            "game_ids": ids,
            "requested_game_ids": requested_ids,
            "game_count": len(ids),
            "game_order_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            "normalized_budget_seconds": 532 * 60 * len(ids) // 110,
            "concurrency": len(ids),
            "n_passes": 1,
            "analyzer_timeout_seconds": 900.0,
            "source_sha256": {
                "run_arm.py": _sha256(Path(__file__)),
                "goal_evidence.py": _sha256(Path(__file__).with_name("goal_evidence.py")),
                "benchmark_initial.pkl": _sha256(bundle_dir / "benchmark_initial.pkl"),
                "tool_agent.py": _sha256(bundle_dir / "src/ARC3-Inference/inference/agent/tool_agent.py"),
            },
            "environment": relevant_env,
            "public_environment_dir": str(env_dir),
        })

        async def play() -> None:
            loop = asyncio.get_running_loop()

            def request_stop() -> None:
                metadata["external_stop_requested"] = True
                _stage("arm_stop_requested", arm=args.arm)
                bm.request_stop()

            loop.add_signal_handler(signal.SIGUSR1, request_stop)
            soft_end = datetime.now() + timedelta(seconds=args.budget_seconds)
            metadata["benchmark_started_utc"] = datetime.now(timezone.utc).isoformat()
            metadata["soft_end_local"] = soft_end.isoformat()
            _write_json(metadata_path, metadata)
            _stage("arm_benchmark_started", arm=args.arm, games=ids,
                   soft_end_local=soft_end.isoformat())
            benchmark_start = time.monotonic()
            try:
                await bm.run(soft_end_time=soft_end, runtime_environment=target,
                             minimal_diagnostics=False)
            finally:
                metadata["benchmark_wall_seconds"] = time.monotonic() - benchmark_start
                loop.remove_signal_handler(signal.SIGUSR1)

        asyncio.run(play())
        metadata["status"] = "completed"
    except asyncio.CancelledError:
        metadata["status"] = "stopped"
        exit_code = 130
    except Exception as exc:
        metadata.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        exit_code = 1
    finally:
        if bm is not None:
            metadata["soft_deadline_fired"] = bool(getattr(bm, "_deadline_fired", False))
            runs = getattr(bm, "game_runs", [])
            metadata["game_state_counts"] = dict(Counter(run.state for run in runs))
            metadata["game_results"] = [{
                "game_id": run.game_id,
                "state": run.state,
                "levels_completed": run.levels_completed,
                "number_of_levels": run.number_of_levels,
                "final_score": run.final_score,
                "actions_per_level": run.actions_per_level,
                "solver_note": run.solver_note,
            } for run in runs]
        if patch is not None:
            _write_json(job_dir / "goal-evidence.json", patch.snapshot())
        # TAAF shutdown(wait=False) can return before cancelled workers leave.
        # Briefly allow completed workers to exit, but never wait without a cap.
        join_end = time.monotonic() + 2.0
        for thread in threading.enumerate():
            if thread.name.startswith("harness-game") and thread.is_alive():
                thread.join(max(0.0, join_end - time.monotonic()))
        live = [thread.name for thread in threading.enumerate()
                if thread.name.startswith("harness-game") and thread.is_alive()]
        metadata.update({
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": time.monotonic() - started,
            "lingering_worker_threads": live,
            "forced_cpu_process_exit": bool(live),
            "exit_code": exit_code,
        })
        _write_json(metadata_path, metadata)
        _stage("arm_finished", arm=args.arm, status=metadata["status"],
               wall_seconds=metadata["wall_seconds"], exit_code=exit_code,
               game_state_counts=metadata.get("game_state_counts", {}),
               lingering_worker_threads=live)
        if live:
            # Only this disposable CPU runner exits. The independent model
            # server remains alive; the parent must drain/flush before B.
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(exit_code)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=("baseline", "goal_evidence"))
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--working-dir", required=True, type=Path,
                        help="Output directory for this arm only.")
    parser.add_argument("--game-list", required=True,
                        help="Comma-separated prefixes, or JSON file with an array/game_ids.")
    parser.add_argument("--budget-seconds", required=True, type=int)
    return run_arm(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
