"""026 host-side failure repair: fork continuation with evidence recheck.

No new model-callable tool, no prompt prefix. For each recorded failure
prefix the driver replays the exact benchmark actions to the cut point T in a
fresh harness game, then continues with the model server under a tight extra
budget. The B arm first receives a host-computed evidence recheck as one
opening user message; the A arm continues from the identical state without it.
First version is K=0: the continuation may run Python recompute but no env
action. Env-action refusal goes through the solver's guard-hook path
(uncatchable snippet-ending refusal preserving stdout + retained functions),
never a plain result dict. Cuts are legal tool-call boundaries only
(previous tool already returned, next model request not yet issued).
"""
from __future__ import annotations

import base64
import contextlib
import copy
import gzip
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from arc3_research.probe_budget import ProbeBudget

# game_id -> fork parameters. Cuts are cumulative executed env actions and
# legal tool-call boundaries only (previous tool already returned, next model
# request not yet issued). m0r0 deferred: its cut sits inside an 18-action
# batch call, unrestorable without leaking the future (see research note).
FORKS = {
    "ft09-0d8bbf25": {"cut": 11, "analysis_step": 5, "kind": "legend_recheck",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
    "tr87-cd924810": {"cut": 132, "analysis_step": 17, "kind": "crop_recheck",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
    "r11l-495a7899": {"cut": 40, "analysis_step": 25, "kind": "control",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
}

# Short recorded failure signatures (not solutions) bundled as data. m0r0
# signature retained for the record; its fork is deferred (batch-internal cut).
QUOTED_EVIDENCE = {
    "ft09-0d8bbf25": ("prior run at L3: legend transcription claimed WOW where "
                      "the pattern has gWg/WOg/WWW; that claim cost 91 actions "
                      "vs ~14 for the correct path."),
    "tr87-cd924810": ("prior run: tile-top-as-ink-top crop cut a 15-dot glyph "
                      "to 11 dots; wheel search returned HITS []."),
    "m0r0-492f87ba": ("prior run: 18-step loop where step 2 predicted block "
                      "(44,44) but the frame showed (44,34); the loop ran 16 "
                      "more steps unchanged."),
    "r11l-495a7899": ("control: prior run crossed levels normally here; "
                      "no anomaly recorded."),
}


class FailureRepairPatch:
    """No global hooks. The repair runs only inside the fork driver below."""

    def snapshot(self) -> dict[str, Any]:
        return {"patch": "failure-repair-v2", "forks": list(FORKS),
                "probe_quota": 0,
                "rule": "host evidence only; K=0 recompute-only via guard-hook "
                        "refusal (uncatchable, keeps stdout+functions); no new "
                        "tool API; no answer injection; tool-call boundaries only"}


def install_failure_repair() -> FailureRepairPatch:
    return FailureRepairPatch()


def _nodes(grid) -> list[dict[str, Any]]:
    from inference.utils.segmentation import segment_layer
    from inference.utils.grid_utils import ARC_COLOR_CHARS
    return segment_layer([list(map(int, row)) for row in grid],
                         ARC_COLOR_CHARS).get("nodes", [])


def recheck_legend(grid) -> str:
    """ft09: deterministic node inventory the WOW claim must satisfy."""
    try:
        nodes = _nodes(grid)
        inv: dict[str, int] = {}
        for n in nodes:
            inv[n["color"]] = inv.get(n["color"], 0) + int(n["pixels"])
        lines = [f"{c}:{v}" for c, v in sorted(inv.items())]
        return ("HOST RECHECK (legend audit, 0 env actions): exact node pixel "
                f"inventory of the current frame: {', '.join(lines)}. "
                "Re-derive the target pattern from these counts; the prior "
                "WOW transcription contradicts the g-node totals. "
                + QUOTED_EVIDENCE["ft09-0d8bbf25"])
    except Exception as exc:
        return f"HOST RECHECK inconclusive ({type(exc).__name__}): re-derive the legend manually."


def recheck_crop(grid) -> str:
    """tr87: tight ink bounding box recount for the glyph region."""
    try:
        from inference.utils.grid_utils import ARC_COLOR_CHARS
        rows = [list(map(int, r)) for r in grid]
        ink = [(r, c) for r, row in enumerate(rows)
               for c, v in enumerate(row) if ARC_COLOR_CHARS[v] not in "B"]
        if not ink:
            return "HOST RECHECK inconclusive: no ink cells found."
        r0 = min(r for r, _ in ink)
        r1 = max(r for r, _ in ink)
        return ("HOST RECHECK (crop audit, 0 env actions): ink spans rows "
                f"{r0}..{r1} ({len(ink)} cells). Any crop ending above row "
                f"{r1} drops the bottom ink row and undercounts the glyph. "
                + QUOTED_EVIDENCE["tr87-cd924810"])
    except Exception as exc:
        return f"HOST RECHECK inconclusive ({type(exc).__name__}): recount the glyph manually."


def recheck_sim(grid) -> str:
    """m0r0: current block positions + single-step-verify rule."""
    try:
        nodes = _nodes(grid)
        blocks = sorted(tuple(n["boundary"][0]) for n in nodes if n["color"] == "S")
        return ("HOST RECHECK (sim audit, 0 env actions): S blocks now at "
                f"{blocks}. " + QUOTED_EVIDENCE["m0r0-492f87ba"] +
                " Advance ONE step, compare the true S motion to your sim "
                "before batching any loop.")
    except Exception as exc:
        return f"HOST RECHECK inconclusive ({type(exc).__name__}): single-step first."


def recheck_control(grid) -> str:
    return ("HOST RECHECK (control, 0 env actions): no anomaly recorded at "
            "this state. " + QUOTED_EVIDENCE["r11l-495a7899"] +
            " Continue normally.")


RECHECK = {"legend_recheck": recheck_legend, "crop_recheck": recheck_crop,
           "sim_recheck": recheck_sim, "control": recheck_control}


def install_zero_env_guard(analyzer) -> Any:
    """K=0: refuse every env action via the guard-hook path.

    Wraps the analyzer instance's ``_action_guard_hook`` (instance attribute
    shadows the method; each ``analyze()`` turn re-reads it, so no base patch
    and no install-order coupling with timing/observer patches). The refusal
    ``("probe_budget_reached", detail)`` makes the solver return a refusal
    payload; the sandbox ends the snippet with an uncatchable error that keeps
    prior stdout and retained functions. Pure-Python recompute calls never
    reach this hook and stay allowed. Returns an uninstall closure.
    """
    original = analyzer._action_guard_hook

    def guarded(grid, action_name, action_data, level=None, remaining=None):
        try:
            display = f"{action_name}({action_data})" if action_data else str(action_name)
        except Exception:
            display = str(action_name)
        return ("probe_budget_reached",
                f"Repair window is recompute-only (K=0): {display} was NOT "
                "executed and no action was spent. Re-derive the evidence in "
                "Python, print the corrected finding, and stop. This refusal "
                "is not catchable and ended the snippet.")

    analyzer._action_guard_hook = guarded

    def uninstall() -> None:
        if getattr(analyzer, "_action_guard_hook", None) is guarded:
            analyzer._action_guard_hook = original

    return uninstall


def load_fork_conversations() -> dict[str, list[dict[str, Any]]]:
    """Packed text-only conversations (images stripped at build time; the
    live opening turn re-renders current visuals from replayed state)."""
    candidates = [
        Path("/kaggle/research/experiments/026-fork-conv.json.gz.b64"),
        Path(__file__).resolve().parents[2] / "experiments/026-fork-conv.json.gz.b64",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise FileNotFoundError("026 fork conversations not found in payload or repo.")
    raw = base64.b64decode(path.read_text().split()[0])
    data = json.loads(gzip.decompress(raw).decode())
    for game_id, messages in data.items():
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"Fork conversation for {game_id} is empty.")
        for message in messages:
            if message.get("role") not in ("user", "assistant", "tool"):
                raise ValueError(f"Bad fork message shape for {game_id}.")
    return data


def run_fork_arm(*, bm, job_dir: Path, arm: str, is_b: bool,
                 budget_seconds: int, prefix_actions: dict[str, list[dict]]) -> dict[str, Any]:
    """Fork-continuation arm. Sequential, one game at a time (no scheduler
    confounds). Writes benchmark.json + game_results into metadata."""
    import arcengine
    import taaf.game_api
    import taaf.game
    from inference.framework.solver import _HarnessGameSession
    from inference.agent.runtime_state import RUNTIME_STATE_FILENAME

    started = time.monotonic()
    summary: dict[str, Any] = {"arm": arm, "is_b": is_b, "forks": []}
    game_ids = list(FORKS)
    # Resolve exact public game ids through the same arcade the harness uses.
    import arc_agi
    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    available_ids = [item.game_id for item in arcade.available_environments]
    resolved: dict[str, str] = {}
    for requested in game_ids:
        matches = [requested] if requested in available_ids else [
            g for g in available_ids if g.startswith(requested)]
        if len(matches) != 1:
            raise ValueError(f"Expected one public environment for {requested!r}; got {matches}")
        resolved[requested] = matches[0]

    spec = taaf.game_api.ArcadeSpec(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(Path(os.environ["ARC3_RESEARCH_ENV_DIR"]).resolve()))
    guard = ProbeBudget(0)
    conversations = load_fork_conversations()
    for index, requested in enumerate(game_ids):
        spec_fork = FORKS[requested]
        cut = int(spec_fork["cut"])
        actions = prefix_actions[requested]
        if len(actions) < cut:
            raise ValueError(f"Prefix for {requested} has {len(actions)} actions, need {cut}")
        game = taaf.game_api.GameAPI(env_name=resolved[requested], arcade_spec=spec)
        run_session = taaf.game.RunSession(record_intermediate_states=True)
        game.start_game(run_session)
        run = game.game_run
        assert run is not None
        run_stem = f"{requested.replace('-', '_')}_fork{'B' if is_b else 'A'}_p0"
        state_path = Path(bm.job_dir) / "artifacts" / f"{run_stem}_{RUNTIME_STATE_FILENAME}"
        viewer_path = Path(bm.job_dir) / "artifacts" / f"{run_stem}_viewer_data.json"
        transcript_path = Path(bm.job_dir) / "transcripts" / f"{run_stem}.txt"
        analysis_relpath = f"solver_analysis/{run_stem}.html"
        analyzer = bm.solver._make_analyzer(game, index, None)
        session = _HarnessGameSession(
            solver=bm.solver, game=game, analyzer=analyzer,
            game_index=index, pass_index=0, state_path=state_path,
            transcript_path=transcript_path,
            analysis_html_relpath=analysis_relpath,
            stop_event=threading.Event(), viewer_data_path=viewer_path)
        # Replay to T through the real step path (history + runtime state).
        # Fork inputs are compact {"a","d"}; benchmark histories are
        # {"action":{"id","data"}}. Accept both shapes here.
        for item in actions[:cut]:
            raw = item.get("action", item)
            name = raw.get("id", raw.get("a"))
            data = dict(raw.get("data", raw.get("d", {})) or {})
            member = getattr(arcengine.GameAction, name, None)
            if member is None:
                member = arcengine.GameAction.from_name(name)
            action = arcengine.ActionInput(id=member, data=data)
            payload = session._execute_action(
                action, generated_tokens=0, batch_index=1, batch_size=1,
                flush_viewer_payload=False)
            if not payload.get("executed"):
                raise RuntimeError(f"Fork replay diverged at {requested}: {payload}")
        session.analysis_step = int(spec_fork["analysis_step"])
        analyzer._kept_functions = {}
        # Warm restart: the recorded text-only conversation (historical images
        # were stripped at build; the live opening re-renders current visuals).
        # Exact kept-function sources were never persisted, so both arms start
        # with none and redefine from their own history text when needed.
        analyzer._history_messages = copy.deepcopy(conversations[requested])
        entry = {"game_id": resolved[requested], "cut": cut,
                 "replay_actions": cut,
                 "restored_messages": len(analyzer._history_messages)}
        if is_b:
            from inference.framework.solver import _grid_from_state
            grid = _grid_from_state(session.game.current_state)
            text = RECHECK[spec_fork["kind"]](grid)
            analyzer._history_messages.append({"role": "user", "content": text})
            entry["recheck_kind"] = spec_fork["kind"]
            entry["recheck_chars"] = len(text)
        # Bounded continuation sharing the arm budget. Mirror _play_one error
        # handling so one fork failure is recorded, not silent. K=0: the
        # zero-env guard is installed per fork and always uninstalled.
        prev_max_actions = bm.solver.max_actions_per_game
        prev_max_runtime = bm.solver.max_runtime_s_per_game
        bm.solver.max_actions_per_game = cut + int(spec_fork["max_extra_actions"])
        bm.solver.max_runtime_s_per_game = float(spec_fork["max_extra_seconds"])
        uninstall_guard = install_zero_env_guard(analyzer)
        try:
            try:
                session.play()
            except Exception as exc:
                run.solver_note = f"error: {type(exc).__name__}: {exc}"
                if run.state == "playing":
                    run.state = "crashed"
                with contextlib.suppress(Exception):
                    game.finish_game()
        finally:
            uninstall_guard()
            bm.solver.max_actions_per_game = prev_max_actions
            bm.solver.max_runtime_s_per_game = prev_max_runtime
        # Full-trajectory (prefix + continuation) run record.
        if run.final_score is None:
            with contextlib.suppress(Exception):
                run.final_score = run._compute_final_score()
        if run.state == "playing":
            run.state = "cancelled"
            with contextlib.suppress(Exception):
                game.finish_game()
        bm.game_runs.append(run)
        entry.update({"state": run.state,
                      "levels_completed": run.levels_completed,
                      "actions_per_level": list(run.actions_per_level or []),
                      "final_score": run.final_score,
                      "solver_note": run.solver_note,
                      "probe_used": guard.used, "probe_quota": guard.max_actions})
        summary["forks"].append(entry)
        if time.monotonic() - started > budget_seconds:
            summary["budget_reached"] = True
            break
    summary["elapsed_seconds"] = time.monotonic() - started
    return summary
