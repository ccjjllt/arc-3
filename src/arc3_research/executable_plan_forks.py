"""034 forced ft09/su15 diagnostics, one isolated process per A/B arm.

The two games share a model server and start their 450-second continuations
together. B spends its forced bootstrap and any repair inside that same window.
This is a checkpoint diagnostic, never natural coverage or a full-pool score.
"""
from __future__ import annotations

import base64
import contextlib
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import threading
import time

GAME_IDS = ("ft09-0d8bbf25", "su15-1944f8ab")
CONTINUATION_SECONDS = 450
# Frozen before any online run: the audited su15 baseline spent 40 actions on
# L5. A symmetric cap of 60 avoids truncating ordinary recovery at 30; it is
# not a shortest-path claim and no baseline action is supplied to the actor.
MAX_ACTIONS = 60
PACKAGE_PATHS = {
    "ft09-0d8bbf25": "experiments/034-fork-inputs/ft09-package.json.gz.b64",
    "su15-1944f8ab": "experiments/034-fork-inputs/su15-package.json.gz.b64",
}
COMBINED_PACKAGE_PATH = "experiments/034-fork-inputs/combined-forks.json.xz.b64"


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def load_forks():
    roots = (Path("/kaggle/research"), Path(__file__).resolve().parents[2])
    combined_path = next((root / COMBINED_PACKAGE_PATH for root in roots
                          if (root / COMBINED_PACKAGE_PATH).is_file()), None)
    combined_raw, combined_package = None, None
    if combined_path is not None:
        combined_raw = combined_path.read_bytes()
        combined_package = json.loads(lzma.decompress(base64.b64decode(combined_raw)))
        if (combined_package.get("schema_version") != 1
                or set(combined_package.get("forks", {})) != set(GAME_IDS)):
            raise ValueError(f"Unsupported combined frozen fork package: {combined_path}")
    forks, sources = {}, {}
    for game_id, relative in PACKAGE_PATHS.items():
        if combined_package is not None:
            path, raw, package = combined_path, combined_raw, combined_package
        else:
            path = next((root / relative for root in roots if (root / relative).is_file()), None)
            # Local dry runs can consume the original source before the notebook
            # builder emits its smaller, identical-ft09-entry payload.
            if path is None and game_id == "ft09-0d8bbf25":
                original = Path(__file__).resolve().parents[2] / "experiments/028-fork-package.json.gz.b64"
                path = original if original.is_file() else None
            if path is None:
                raise FileNotFoundError(relative)
            raw = path.read_bytes()
            package = json.loads(gzip.decompress(base64.b64decode(raw)))
        if package.get("schema_version") != 1 or game_id not in package.get("forks", {}):
            raise ValueError(f"Unsupported frozen fork package: {path}")
        fork = package["forks"][game_id]
        expected_cut = 27 if game_id == "ft09-0d8bbf25" else 86
        expected_level = 3 if game_id == "ft09-0d8bbf25" else 5
        if (fork["cut"] != expected_cut or len(fork["actions"]) != expected_cut
                or fork["current_frame"]["level"] != expected_level):
            raise ValueError(f"034 frozen checkpoint changed: {game_id}")
        if int(fork.get("seed", 0)) != 0:
            raise ValueError("034 restoration currently requires the frozen seed 0")
        forks[game_id] = fork
        sources[game_id] = {"path": str(path), "package_sha256": hashlib.sha256(raw).hexdigest(),
                            "fork_sha256": _hash(fork),
                            "source_package_sha256": package.get("source_package_sha256s", {}).get(
                                game_id, package.get("source_package_sha256")),
                            "transport_encoding": "xz+base64" if combined_package is not None else "gzip+base64"}
    return forks, sources


def latest_python_source(messages):
    """Read only the last Python call already present in the frozen request."""
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        for call in reversed(message.get("tool_calls") or []):
            function = call.get("function") or {}
            if function.get("name") != "python":
                continue
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            code = arguments.get("code") if isinstance(arguments, dict) else None
            if isinstance(code, str) and code.strip():
                return code
    raise ValueError("Frozen prefix has no current Python source for the forced diagnostic")


def _request_evidence(path):
    result = {"path": str(path), "exists": path.is_file(), "requests": 0, "responses": 0,
              "returned_usage": {}, "usage_note": "Main requests only; bounded branch usage is in executable-plan events; timeouts may lack usage"}
    if not path.is_file():
        return result
    raw = path.read_bytes()
    result["sha256"] = hashlib.sha256(raw).hexdigest()
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            result.setdefault("malformed_lines", []).append(line_number)
            continue
        event = record.get("event")
        if event in ("request", "response"):
            result[event + "s"] += 1
        if event == "response":
            for key, value in (record.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    result["returned_usage"][key] = result["returned_usage"].get(key, 0) + value
    return result


def run_forks(*, bm, job_dir, budget_seconds, use_plan, dry_run=False):
    import arcengine
    import arc_agi
    import taaf.game_api
    import taaf.game
    from inference.framework.solver import _HarnessGameSession, _grid_from_state, _engine_action_names
    from inference.agent.runtime_state import RUNTIME_STATE_FILENAME
    from inference.agent.tool_agent import _resolve_request_log_path
    from arc3_research.executable_plan import install_executable_plan, _bindings

    if budget_seconds != 600:
        raise ValueError("034 diagnostic requires 600s runner allowance for 450s continuations")
    forks, sources = load_forks()
    job_dir = Path(job_dir)
    for path in (job_dir, job_dir / "artifacts", job_dir / "transcripts"):
        path.mkdir(parents=True, exist_ok=True)
    label = "B" if use_plan else "A"
    started = time.monotonic()
    output = {"kind": "034_forced_program_repair_diagnostic", "arm": label,
              "diagnostic_forced_trigger": bool(use_plan), "natural_coverage_claim": False,
              "scope": "Same-prefix continuation evidence only, not full-pool or hidden-score improvement",
              "input_sources": sources, "forks_sha256": _hash(forks),
              "continuation_seconds_per_game": CONTINUATION_SECONDS,
              "max_continuation_actions_per_game": MAX_ACTIONS,
              "arm_allowance_seconds": budget_seconds, "parallel_games": len(GAME_IDS),
              "repair_budget_included": True, "dry_run": dry_run,
              "candidate_branch_contract": {"max_extra_processing_seconds": 120,
                  "max_request_seconds": 60, "max_actions_per_short_contract": 3,
                  "scope": "all branch processing inside each 450-second continuation"} if use_plan else None,
              "history_images": "Removed symmetrically in frozen packages; current frames/history regenerated by replay",
              "restored": [], "forks": []}
    patch = install_executable_plan(min_remaining_seconds=180, request_seconds=60,
                                   extra_seconds=120) if use_plan else None
    prepared = []
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    try:
        for index, game_id in enumerate(GAME_IDS):
            fork = forks[game_id]
            solver = copy.copy(bm.solver)
            solver._stop_event = threading.Event()
            solver._warmup_remaining = 0
            solver.max_runtime_s_per_game = None
            solver.max_actions_per_game = None
            solver.soft_end_time = None
            solver.save_request_logs = True
            game = taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec)
            game.start_game(taaf.game.RunSession(record_intermediate_states=True))
            stem = f"{game_id}_{label}"
            state_path = job_dir / "artifacts" / f"{stem}_{RUNTIME_STATE_FILENAME}"
            request_path = job_dir / f"{stem}_requests.jsonl"
            if request_path.exists() or state_path.exists():
                raise FileExistsError(f"034 requires a fresh arm output directory: {state_path}")
            analyzer = solver._make_analyzer(game, index, None)
            session = _HarnessGameSession(solver=solver, game=game, analyzer=analyzer,
                game_index=index, pass_index=0, state_path=state_path,
                transcript_path=job_dir / "transcripts" / f"{stem}.txt",
                analysis_html_relpath=f"solver_analysis/{stem}.html", stop_event=solver._stop_event,
                viewer_data_path=job_dir / "artifacts" / f"{stem}_viewer_data.json")
            prepared.append((game_id, fork, session, request_path))
            session.seed_initial_history()
            for raw in fork["actions"]:
                result = session._execute_action(arcengine.ActionInput(
                    id=arcengine.GameAction.from_name(raw["id"]), data=dict(raw.get("data") or {})),
                    generated_tokens=0, batch_index=1, batch_size=1, flush_viewer_payload=False)
                if not result.get("executed"):
                    raise RuntimeError(f"034 prefix action refused for {game_id}: {result}")
            run = game.game_run
            grid = [list(map(int, row)) for row in _grid_from_state(game.current_state)]
            if (grid != fork["current_frame"]["grid"]
                    or run.levels_completed != fork["current_frame"]["level"] - 1
                    or len(run.history) != fork["cut"]):
                raise RuntimeError(f"034 restored checkpoint differs for {game_id}")
            analyzer._ensure_session(state_path)
            analyzer._history_messages = copy.deepcopy([m for m in fork["messages"] if m.get("role") != "system"])
            analyzer._kept_functions = dict(fork.get("kept_functions", {}))
            analyzer._step_env_callback = session.step_env
            analyzer._current_valid_actions = _engine_action_names(game)
            session.analysis_step = int(fork["analysis_step"]) - 1
            session.write_runtime_state()
            solver.max_runtime_s_per_game = float(CONTINUATION_SECONDS)
            solver.max_actions_per_game = len(run.history) + MAX_ACTIONS
            source_code = latest_python_source(fork["messages"])
            output["restored"].append({"game_id": game_id, "cut": fork["cut"],
                "grid_sha256": _hash(grid), "recorded_frame_matches": True,
                "initial_levels_completed": run.levels_completed,
                "prefix_recorded_actions": len(run.history),
                "native_frame_step": session.current_frame().step,
                "messages_sha256": _hash(analyzer._history_messages),
                "history_messages": len(analyzer._history_messages),
                "functions_sha256": _hash(analyzer._kept_functions),
                "retained_functions": sorted(analyzer._kept_functions),
                "branch_source_code_sha256": _hash(source_code),
                "request_log": str(request_path)})
        for _, _, session, request_path in prepared:
            if _resolve_request_log_path(session.state_path) != request_path:
                raise RuntimeError("034 per-game request log layout differs from frozen runtime")
        _write(job_dir / "executable-plan-restored.json", output["restored"])
        if dry_run:
            output["model_calls"] = 0
            return output
        if time.monotonic() - started > budget_seconds - CONTINUATION_SECONDS:
            raise RuntimeError("034 replay consumed continuation allowance; refusing to shorten the paired window")
        barrier = threading.Barrier(len(prepared))

        def continue_one(item):
            game_id, fork, session, request_path = item
            run, agent = session.game.game_run, session.analyzer
            entry = copy.deepcopy(next(e for e in output["restored"] if e["game_id"] == game_id))
            prefix_count = entry["prefix_recorded_actions"]
            barrier.wait(timeout=30)
            session.started_at = time.monotonic()
            session.solver.soft_end_time = datetime.now() + timedelta(seconds=CONTINUATION_SECONDS)
            entry.update(continuation_started_at_epoch=time.time(),
                         max_total_recorded_actions=prefix_count + MAX_ACTIONS)
            entry["continuation_deadline_epoch"] = entry["continuation_started_at_epoch"] + CONTINUATION_SECONDS
            try:
                if patch is not None:
                    state = patch.state(agent, session.state_path)
                    state.bootstrap_used = True
                    state.should_stop = session.should_stop
                    state.source_code = latest_python_source(fork["messages"])
                    state.source_bindings = _bindings(state.source_code, agent._kept_functions)
                    state.latest_messages = copy.deepcopy(fork["messages"])
                    trigger = {"kind": "bootstrap", "diagnostic_forced_trigger": True,
                               "source_code": state.source_code,
                               "source_bindings": state.source_bindings,
                               "already_executed_in_snippet": 0,
                               "before_grid_sha256": _hash(session.current_frame().grid)}
                    patch.event(state, {"kind": "forced_diagnostic_bootstrap", "trigger": trigger})
                    entry["forced_branch"] = patch.run_branch(agent, state, trigger)
                    # Direct host invocation has no caller tool-message wrapper.
                    # Return actual results to the ordinary actor explicitly.
                    agent._history_messages.append({"role": "user", "content":
                        "The forced diagnostic program branch has finished. Inspect current_frame before continuing; "
                        "any executed actions already happened and must not be repeated automatically. Actual report:\n" +
                        json.dumps(entry["forced_branch"], ensure_ascii=False)})
                after_branch = len(run.history)
                entry["actions_during_forced_branch"] = after_branch - prefix_count
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
            history = run.to_json_dict()["history"][prefix_count:]
            entry.update(state=run.state, levels_completed=run.levels_completed,
                added_levels=run.levels_completed - entry["initial_levels_completed"],
                final_score=run.final_score, actions_per_level=run.actions_per_level,
                continuation_history=history, continuation_actions=[h["action"] for h in history],
                continuation_action_count=len(history), elapsed_seconds=time.monotonic() - session.started_at,
                solver_note=run.solver_note, requests=_request_evidence(request_path),
                final_retained_functions=sorted(agent._kept_functions))
            entry["continuation_budget_observed"] = {
                "action_cap_respected": len(history) <= MAX_ACTIONS,
                "elapsed_over_450_seconds": max(0.0, entry["elapsed_seconds"] - CONTINUATION_SECONDS),
                "note": "Includes in-flight response and cleanup tails; report overshoot rather than silently clipping elapsed."}
            _write(job_dir / f"{game_id}-{label}.json", entry)
            return entry, run

        with ThreadPoolExecutor(max_workers=len(prepared), thread_name_prefix="harness-game-034-fork") as pool:
            for future in as_completed([pool.submit(continue_one, item) for item in prepared]):
                entry, run = future.result()
                bm.game_runs.append(run)
                output["forks"].append(entry)
                output["forks"].sort(key=lambda e: GAME_IDS.index(e["game_id"]))
                _write(job_dir / "executable-plan-forks.json", output)
                print("[034 fork]", entry["game_id"], label, entry["state"],
                      entry["added_levels"], entry["continuation_action_count"], flush=True)
        return output
    finally:
        for _, _, session, _ in prepared:
            if session.game.game_run.state == "playing":
                session.game.game_run.state = "cancelled"
                with contextlib.suppress(Exception):
                    session.game.finish_game()
        if patch is not None:
            output["patch"] = patch.snapshot()
            patch.uninstall()
            output["patch_uninstalled"] = True
        output["elapsed_seconds"] = time.monotonic() - started
        _write(job_dir / "executable-plan-forks.json", output)
