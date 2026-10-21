"""031 single-arm continuations from the frozen 028 public checkpoints.

Run baseline and runs in separate CPU processes against the same model server.
The three sessions within one arm share its one segmentation policy. No repair
call, answer hint or historical continuation is supplied to the model.
"""
from __future__ import annotations

import base64
import contextlib
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import threading
import time


GAME_IDS = ("ft09-0d8bbf25", "tu93-0768757b", "r11l-495a7899")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def load_package():
    relative = "experiments/028-fork-package.json.gz.b64"
    for root in (Path("/kaggle/research"), Path(__file__).resolve().parents[2]):
        path = root / relative
        if path.is_file():
            package = json.loads(gzip.decompress(base64.b64decode(path.read_text())))
            if set(package["forks"]) != set(GAME_IDS):
                raise ValueError("031 requires exactly the three frozen 028 checkpoints")
            return package
    raise FileNotFoundError(relative)


def _request_evidence(path):
    result = {"path": str(path), "requests": 0, "responses": 0,
              "recorded_usage": {}, "malformed_lines": []}
    if not path.is_file():
        result["exists"] = False
        return result
    raw = path.read_bytes()
    result.update(exists=True, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            result["malformed_lines"].append(line_number)
            continue
        event = record.get("event")
        if event == "request":
            result["requests"] += 1
        elif event == "response":
            result["responses"] += 1
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = record.get("usage", {}).get(key)
                if isinstance(value, (int, float)):
                    result["recorded_usage"][key] = result["recorded_usage"].get(key, 0) + value
    result["usage_note"] = "Returned usage only; timed-out requests may have unreported cost"
    return result


def run_forks(*, bm, job_dir: Path, budget_seconds: int, use_runs: bool,
              dry_run: bool = False):
    import arcengine
    import arc_agi
    import taaf.game_api
    import taaf.game
    from inference.framework.solver import _HarnessGameSession, _grid_from_state, _engine_action_names
    from inference.agent.runtime_state import RUNTIME_STATE_FILENAME
    from inference.agent.tool_agent import _resolve_request_log_path
    from arc3_research import segmentation_runs

    if segmentation_runs._INSTALLED is not None:
        raise RuntimeError("Fork arm must start without an installed segmentation patch")
    package = load_package()
    for fork in package["forks"].values():
        if (int(fork["max_extra_seconds"]), int(fork["max_extra_actions"])) != (250, 30):
            raise ValueError("Frozen continuation budgets changed")
    if budget_seconds < 250:
        raise ValueError("Arm allowance cannot shorten a frozen 250-second continuation")
    started = time.monotonic()
    label = "B" if use_runs else "A"
    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "artifacts").mkdir(exist_ok=True)
    (job_dir / "transcripts").mkdir(exist_ok=True)
    output = {
        "kind": "single_arm_recorded_checkpoint_continuations",
        "arm": label, "use_runs": use_runs, "forks": [], "restored": [],
        "input_sha256": _digest(package), "arm_allowance_seconds": budget_seconds,
        "parallel_sessions": len(GAME_IDS), "repair_calls": 0,
        "comparison": "Separate baseline/runs arm processes; three concurrent 250-second, 30-action continuations per arm",
        "scope": "Checkpoint diagnostic, not natural-start full-pool scoring or hidden leaderboard evidence",
        "history_limit": "Frozen 028 package retains text and accepted functions; historical images were removed symmetrically",
        "dry_run": dry_run,
    }
    patch = segmentation_runs.install_segmentation_runs() if use_runs else None
    output["patch"] = patch.snapshot() if patch is not None else None
    prepared = []
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    try:
        for index, game_id in enumerate(GAME_IDS):
            fork = package["forks"][game_id]
            local_solver = copy.copy(bm.solver)
            local_solver._stop_event = threading.Event()
            local_solver._warmup_remaining = 0
            local_solver.max_runtime_s_per_game = None  # Replay is not continuation time.
            local_solver.max_actions_per_game = None
            local_solver.save_request_logs = True
            game = taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec)
            game.start_game(taaf.game.RunSession(record_intermediate_states=True))
            stem = f"{game_id}_{label}"
            state_path = job_dir / "artifacts" / f"{stem}_{RUNTIME_STATE_FILENAME}"
            # The runtime resolver uses a shared filename until at least two
            # state files exist. At execution all three will exist, so reserve
            # the final per-session path now and verify it after restoration.
            request_path = job_dir / f"{stem}_requests.jsonl"
            if request_path.exists():
                raise FileExistsError(f"Use a fresh arm directory: {request_path}")
            analyzer = local_solver._make_analyzer(game, index, None)
            session = _HarnessGameSession(solver=local_solver, game=game, analyzer=analyzer,
                game_index=index, pass_index=0, state_path=state_path,
                transcript_path=job_dir / "transcripts" / f"{stem}.txt",
                analysis_html_relpath=f"solver_analysis/{stem}.html",
                stop_event=local_solver._stop_event,
                viewer_data_path=job_dir / "artifacts" / f"{stem}_viewer_data.json")
            prepared.append((game_id, fork, session, request_path))
            session.seed_initial_history()
            for action in fork["actions"]:
                raw = action.get("action", action)
                name = raw.get("id", raw.get("a"))
                data = dict(raw.get("data", raw.get("d", {})) or {})
                payload = session._execute_action(arcengine.ActionInput(
                    id=arcengine.GameAction.from_name(name), data=data),
                    generated_tokens=0, batch_index=1, batch_size=1,
                    flush_viewer_payload=False)
                if not payload.get("executed"):
                    raise RuntimeError(f"{stem} replay refused {name}: {payload}")
            grid = [list(map(int, row)) for row in _grid_from_state(game.current_state)]
            if grid != fork["current_frame"]["grid"]:
                raise RuntimeError(f"{stem} replay differs from recorded original frame")
            if game.game_run.levels_completed != int(fork["current_frame"]["level"]) - 1:
                raise RuntimeError(f"{stem} replay level differs from recorded checkpoint")
            prefix_count = len(game.game_run.history)
            if prefix_count != len(fork["actions"]):
                raise RuntimeError(f"{stem} replay action count differs from checkpoint")
            analyzer._ensure_session(state_path)
            analyzer._history_messages = copy.deepcopy([
                message for message in fork["messages"] if message.get("role") != "system"])
            analyzer._kept_functions = dict(fork.get("kept_functions", {}))
            analyzer._step_env_callback = session.step_env
            analyzer._current_valid_actions = _engine_action_names(game)
            session.analysis_step = int(fork["analysis_step"]) - 1
            session.write_runtime_state()
            local_solver.max_runtime_s_per_game = 250.0
            local_solver.max_actions_per_game = prefix_count + 30
            output["restored"].append({
                "game_id": game_id, "arm": label, "cut": fork["cut"],
                "recorded_frame_matches": True, "grid_sha256": _digest(grid),
                "initial_levels_completed": game.game_run.levels_completed,
                "prefix_recorded_actions": prefix_count,
                "restored_messages": len(analyzer._history_messages),
                "messages_sha256": _digest(analyzer._history_messages),
                "restored_functions": sorted(analyzer._kept_functions),
                "kept_functions_sha256": _digest(analyzer._kept_functions),
                "request_log": str(request_path), "fresh_request_log": True,
                "budget_seconds": 250, "max_extra_actions": 30,
            })
        for _, _, session, request_path in prepared:
            if _resolve_request_log_path(session.state_path) != request_path:
                raise RuntimeError("Runtime request artifact layout changed")
        _write(job_dir / "segmentation-forks-restored.json", output["restored"])
        if dry_run:
            output["model_calls"] = 0
            return output

        barrier = threading.Barrier(len(prepared))

        def continue_one(item):
            game_id, fork, session, request_path = item
            run = session.game.game_run
            entry = copy.deepcopy(next(x for x in output["restored"] if x["game_id"] == game_id))
            prefix_count = entry["prefix_recorded_actions"]
            barrier.wait(timeout=30)
            session.started_at = time.monotonic()
            try:
                session.play()
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
                if run.state == "playing":
                    run.state = "crashed"
            finally:
                if run.state == "playing":
                    run.state = "cancelled"
                with contextlib.suppress(Exception):
                    session.game.finish_game()
                if run.final_score is None:
                    with contextlib.suppress(Exception):
                        run.final_score = run._compute_final_score()
            # ActionRecord is a dataclass; serialize before reading complete ID/data.
            history = run.to_json_dict()["history"][prefix_count:]
            entry.update(state=run.state, levels_completed=run.levels_completed,
                added_levels=run.levels_completed - entry["initial_levels_completed"],
                final_score=run.final_score, actions_per_level=run.actions_per_level,
                continuation_actions=[record["action"] for record in history],
                continuation_history=history, continuation_action_count=len(history),
                elapsed_seconds=time.monotonic() - session.started_at,
                solver_note=run.solver_note, requests=_request_evidence(request_path),
                final_retained_functions=sorted(session.analyzer._kept_functions))
            _write(job_dir / f"{game_id}-{label}.json", entry)
            return entry, run

        with ThreadPoolExecutor(max_workers=len(prepared), thread_name_prefix="segmentation-fork") as pool:
            for future in as_completed([pool.submit(continue_one, item) for item in prepared]):
                entry, run = future.result()
                output["forks"].append(entry)
                bm.game_runs.append(run)
                _write(job_dir / "segmentation-forks.json", output)
                print("[031 fork]", entry["game_id"], label, entry["state"],
                      entry["added_levels"], entry["continuation_action_count"], flush=True)
        return output
    finally:
        for _, _, session, _ in prepared:
            if session.game.game_run.state == "playing":
                session.game.game_run.state = "cancelled"
                with contextlib.suppress(Exception):
                    session.game.finish_game()
        if patch is not None:
            patch.uninstall()
        output["elapsed_seconds"] = time.monotonic() - started
        output["patch_uninstalled"] = segmentation_runs._INSTALLED is None
        _write(job_dir / "segmentation-forks.json", output)
