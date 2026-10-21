"""033 single-ft09 recorded-state extraction-repair diagnostic.

Each arm is a fresh CPU process sharing only the external model server.
600s runner allowance covers replay/drain; both actual continuations get 450s,
including the candidate's at-most-120s controller repair.
"""
from __future__ import annotations

import base64
import contextlib
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import threading
import time

GAME_ID = "ft09-0d8bbf25"
CONTINUATION_SECONDS = 450
MAX_ACTIONS = 30


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _package():
    relative = "experiments/028-fork-package.json.gz.b64"
    for root in (Path("/kaggle/research"), Path(__file__).resolve().parents[2]):
        path = root / relative
        if path.is_file():
            return json.loads(gzip.decompress(base64.b64decode(path.read_text())))
    raise FileNotFoundError(relative)


def run_forks(*, bm, job_dir, budget_seconds, use_repair, dry_run=False):
    import arcengine
    import arc_agi
    import taaf.game_api
    import taaf.game
    from inference.framework.solver import _HarnessGameSession, _grid_from_state, _engine_action_names
    from inference.agent.runtime_state import RUNTIME_STATE_FILENAME
    from inference.agent.tool_agent import _resolve_request_log_path
    from arc3_research.controller_repair import run_controller_repair

    if budget_seconds < CONTINUATION_SECONDS:
        raise ValueError("033 runner allowance must preserve 450s continuation")
    package = _package()
    fork = package["forks"][GAME_ID]
    job_dir = Path(job_dir)
    for path in (job_dir, job_dir / "artifacts", job_dir / "transcripts"):
        path.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    label = "B" if use_repair else "A"
    stem = f"{GAME_ID}_{label}"
    state_path = job_dir / "artifacts" / f"{stem}_{RUNTIME_STATE_FILENAME}"
    output = {"kind": "single_ft09_controller_extraction_diagnostic", "arm": label,
        "use_repair": use_repair, "diagnostic_forced_trigger": True, "dry_run": dry_run,
        "arm_allowance_seconds": budget_seconds, "continuation_budget_seconds": CONTINUATION_SECONDS,
        "repair_budget_included_seconds": 120 if use_repair else 0,
        "max_continuation_actions": MAX_ACTIONS, "input_sha256": _hash(fork), "forks": [],
        "scope": "Recorded failure continuation only; no online trigger, full-pool or hidden-score claim",
        "prior_history_images": "Frozen 028 package removed historical images symmetrically"}
    solver = copy.copy(bm.solver)
    solver._stop_event = threading.Event()
    solver._warmup_remaining = 0
    solver.max_runtime_s_per_game = None
    solver.max_actions_per_game = None
    solver.save_request_logs = True
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    game = taaf.game_api.GameAPI(env_name=GAME_ID, arcade_spec=spec)
    game.start_game(taaf.game.RunSession(record_intermediate_states=True))
    analyzer = solver._make_analyzer(game, 0, None)
    session = _HarnessGameSession(solver=solver, game=game, analyzer=analyzer,
        game_index=0, pass_index=0, state_path=state_path,
        transcript_path=job_dir / "transcripts" / f"{stem}.txt",
        analysis_html_relpath=f"solver_analysis/{stem}.html", stop_event=solver._stop_event,
        viewer_data_path=job_dir / "artifacts" / f"{stem}_viewer_data.json")
    run = game.game_run
    try:
        session.seed_initial_history()
        for action in fork["actions"]:
            payload = session._execute_action(arcengine.ActionInput(
                id=arcengine.GameAction.from_name(action["id"]), data=dict(action.get("data") or {})),
                generated_tokens=0, batch_index=1, batch_size=1, flush_viewer_payload=False)
            if not payload.get("executed"):
                raise RuntimeError(f"Replay refused: {action}: {payload}")
        grid = [list(map(int, row)) for row in _grid_from_state(game.current_state)]
        if grid != fork["current_frame"]["grid"] or run.levels_completed != fork["current_frame"]["level"] - 1:
            raise RuntimeError("033 checkpoint differs from frozen original observation")
        prefix_count = len(run.history)
        if prefix_count != len(fork["actions"]):
            raise RuntimeError("033 replay count differs from frozen prefix")
        analyzer._ensure_session(state_path)
        analyzer._history_messages = copy.deepcopy([m for m in fork["messages"] if m.get("role") != "system"])
        analyzer._kept_functions = dict(fork.get("kept_functions", {}))
        analyzer._step_env_callback = session.step_env
        analyzer._current_valid_actions = _engine_action_names(game)
        session.analysis_step = int(fork["analysis_step"]) - 1
        session.write_runtime_state()
        request_path = _resolve_request_log_path(state_path)
        if request_path.exists():
            raise FileExistsError(f"Use a fresh 033 arm directory: {request_path}")
        output["restored"] = {"game_id": GAME_ID, "arm": label, "cut": fork["cut"],
            "recorded_frame_matches": True, "grid_sha256": _hash(grid),
            "prefix_recorded_actions": prefix_count, "initial_levels_completed": run.levels_completed,
            "history_messages": len(analyzer._history_messages), "history_sha256": _hash(analyzer._history_messages),
            "retained_functions": sorted(analyzer._kept_functions), "functions_sha256": _hash(analyzer._kept_functions),
            "request_log": str(request_path)}
        if dry_run:
            output["model_calls"] = 0
            return output
        solver.max_runtime_s_per_game = float(CONTINUATION_SECONDS)
        solver.max_actions_per_game = prefix_count + MAX_ACTIONS
        session.started_at = time.monotonic()
        entry = dict(output["restored"])
        if use_repair:
            entry["controller_repair"] = run_controller_repair(analyzer, state_path,
                remaining_seconds=session.request_timeout_seconds(), should_stop=session.should_stop,
                max_calls=2, event_seconds=120)
        actions_after_controller = len(run.history)
        entry["actions_executed_during_controller"] = actions_after_controller - prefix_count
        try:
            session.play()
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
            if run.state == "playing":
                run.state = "crashed"
        finally:
            if run.state == "playing":
                run.state = "cancelled"
            game.finish_game()
            if run.final_score is None:
                run.final_score = run._compute_final_score()
        serialized = run.to_json_dict()
        continuation = serialized["history"][prefix_count:]
        entry.update(state=run.state, levels_completed=run.levels_completed,
            added_levels=run.levels_completed - output["restored"]["initial_levels_completed"],
            final_score=run.final_score, actions_per_level=run.actions_per_level,
            continuation_actions=[h["action"] for h in continuation], continuation_history=continuation,
            continuation_action_count=len(continuation),
            subsequent_main_actions=[h["action"] for h in serialized["history"][actions_after_controller:]],
            elapsed_seconds=time.monotonic() - session.started_at, solver_note=run.solver_note,
            final_retained_functions=sorted(analyzer._kept_functions))
        if request_path.is_file():
            entry["request_log_sha256"] = hashlib.sha256(request_path.read_bytes()).hexdigest()
            marker = (entry.get("controller_repair") or {}).get("delivery_message_sha256")
            entry["verified_delivery_seen_in_main_request"] = False if marker else None
            usage = {}
            for line in request_path.read_text().splitlines():
                record = json.loads(line)
                if marker and record.get("event") == "request":
                    entry["verified_delivery_seen_in_main_request"] |= any(
                        isinstance(m.get("content"), str) and hashlib.sha256(m["content"].encode()).hexdigest() == marker
                        for m in record.get("messages", []))
                if record.get("event") == "response":
                    for key, value in (record.get("usage") or {}).items():
                        if key in ("prompt_tokens", "completion_tokens", "total_tokens") and isinstance(value, (int, float)):
                            usage[key] = usage.get(key, 0) + value
            entry["main_response_recorded_usage"] = usage
        entry["adoption_note"] = "Delivery in a real next request and actual subsequent actions are distinct from proof those actions consumed the corrected extraction"
        output["forks"].append(entry)
        bm.game_runs.append(run)
        (job_dir / f"{GAME_ID}-{label}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
        print("[033 fork]", GAME_ID, label, entry["state"], entry["added_levels"],
              entry["continuation_action_count"], flush=True)
        return output
    finally:
        if run.state == "playing":
            run.state = "cancelled"
            with contextlib.suppress(Exception):
                game.finish_game()
        output["elapsed_seconds"] = time.monotonic() - started
        (job_dir / "controller-repair-forks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
