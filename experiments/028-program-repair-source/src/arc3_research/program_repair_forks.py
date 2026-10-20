"""Concurrent recorded-state A/B continuations against one loaded model."""
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


def load_package():
    relative = "experiments/028-fork-package.json.gz.b64"
    roots = (Path("/kaggle/research"), Path(__file__).resolve().parents[2])
    for root in roots:
        path = root / relative
        if path.is_file():
            return json.loads(gzip.decompress(base64.b64decode(path.read_text())))
    raise FileNotFoundError(relative)


def run_forks(*, bm, job_dir: Path, budget_seconds: int, dry_run: bool = False):
    import arcengine
    import arc_agi
    import taaf.game_api
    import taaf.game
    from inference.framework.solver import _HarnessGameSession, _grid_from_state, _engine_action_names
    from inference.agent.runtime_state import RUNTIME_STATE_FILENAME
    from arc3_research.program_repair import install_program_repair, run_program_repair

    package = load_package()
    started = time.monotonic()
    output = {"kind": "concurrent_paired_recorded_forks", "forks": [],
              "comparison": "same wall-time and action caps, six concurrent requests sharing one GPU; diagnostic, not full-pool score",
              "input_sha256": hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()}
    config = {"max_events_per_game": 1, "max_calls_per_event": 1,
              "max_output_tokens": 4096, "call_timeout_seconds": 60,
              "event_timeout_seconds": 120, "min_remaining_seconds": 180}
    patch = install_program_repair(config=config)
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    prepared = []
    for game_id, fork in package["forks"].items():
        for label in ("A", "B"):
            index = len(prepared)
            local_solver = copy.copy(bm.solver)
            local_solver._stop_event = threading.Event()
            local_solver._warmup_remaining = 0
            local_solver.max_runtime_s_per_game = float(fork.get("max_extra_seconds", 250))
            local_solver.max_actions_per_game = None
            game = taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec)
            game.start_game(taaf.game.RunSession(record_intermediate_states=True))
            stem = f"{game_id}_{label}"
            state_path = job_dir / "artifacts" / f"{stem}_{RUNTIME_STATE_FILENAME}"
            analyzer = local_solver._make_analyzer(game, index, None)
            analyzer._program_repair_disabled = label == "A"
            session = _HarnessGameSession(solver=local_solver, game=game, analyzer=analyzer,
                game_index=index, pass_index=0, state_path=state_path,
                transcript_path=job_dir / "transcripts" / f"{stem}.txt",
                analysis_html_relpath=f"solver_analysis/{stem}.html",
                stop_event=local_solver._stop_event,
                viewer_data_path=job_dir / "artifacts" / f"{stem}_viewer_data.json")
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
            expected = fork["current_frame"]["grid"]
            if grid != expected:
                raise RuntimeError(f"{stem} replay differs from recorded original frame")
            analyzer._ensure_session(state_path)
            analyzer._history_messages = copy.deepcopy([
                message for message in fork["messages"] if message.get("role") != "system"])
            analyzer._kept_functions = dict(fork.get("kept_functions", {}))
            analyzer._step_env_callback = session.step_env
            analyzer._current_valid_actions = _engine_action_names(game)
            session.analysis_step = int(fork["analysis_step"]) - 1
            session.write_runtime_state()
            prefix_count = len(game.game_run.history)
            local_solver.max_actions_per_game = prefix_count + int(fork.get("max_extra_actions", 30))
            prepared.append((game_id, label, fork, session, prefix_count))

    if dry_run:
        output["restored"] = [{"game_id": g, "arm": label,
            "recorded_frame_matches": True, "actions": count,
            "history_messages": len(s.analyzer._history_messages),
            "retained_functions": sorted(s.analyzer._kept_functions)}
            for g, label, f, s, count in prepared]
        output["model_calls"] = 0
        patch.uninstall()
        return output

    barrier = threading.Barrier(len(prepared))
    def continue_one(item):
        game_id, label, fork, session, prefix_count = item
        run = session.game.game_run
        analyzer = session.analyzer
        entry = {"game_id": game_id, "arm": label, "cut": fork["cut"],
                 "prefix_recorded_actions": prefix_count,
                 "restored_messages": len(analyzer._history_messages),
                 "restored_functions": sorted(analyzer._kept_functions),
                 "initial_levels_completed": run.levels_completed,
                 "budget_seconds": fork.get("max_extra_seconds", 250)}
        barrier.wait(timeout=30)
        session.started_at = time.monotonic()
        try:
            if label == "B" and not fork.get("control", game_id.startswith("r11l")):
                entry["repair"] = run_program_repair(analyzer, session.state_path,
                    reason="recorded_failure", remaining_seconds=session.request_timeout_seconds(),
                    config=config, should_stop=session.should_stop)
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
        history = run.history[prefix_count:]
        entry.update(state=run.state, levels_completed=run.levels_completed,
            added_levels=run.levels_completed-entry["initial_levels_completed"],
            final_score=run.final_score, actions_per_level=run.actions_per_level,
            continuation_actions=[x.get("action", {}) for x in history],
            continuation_action_count=len(history),
            elapsed_seconds=time.monotonic()-session.started_at,
            solver_note=run.solver_note)
        (job_dir / f"{game_id}-{label}.json").write_text(json.dumps(entry, indent=2, default=str)+"\n")
        return entry, run

    try:
        with ThreadPoolExecutor(max_workers=len(prepared), thread_name_prefix="repair-fork") as pool:
            for future in as_completed([pool.submit(continue_one, item) for item in prepared]):
                entry, run = future.result()
                output["forks"].append(entry)
                bm.game_runs.append(run)
                (job_dir / "program-repair-forks.json").write_text(json.dumps(output, indent=2, default=str)+"\n")
                print("[028]", entry["game_id"], entry["arm"], entry["state"],
                    entry["added_levels"], entry["continuation_action_count"], flush=True)
        output["patch"] = patch.snapshot()
    finally:
        patch.uninstall()
    output["elapsed_seconds"] = time.monotonic()-started
    output["parallel_sessions"] = len(prepared)
    return output
