"""026 host-side failure repair: fork continuation with evidence recheck.

No new model-callable tool, no prompt prefix. For each recorded failure
prefix the driver replays the exact benchmark actions to the cut point T in a
fresh harness game, then continues with the model server under a tight extra
budget. The B arm first receives a host-computed evidence recheck as one
opening user message (stdout-shaped text, plus corrected data the model must
re-derive itself); the A arm continues from the identical state without it.
All probe env dispatches (none in the current K=0 prefixes) go through
ProbeBudget pre-dispatch checks and stop gracefully with a stop_reason.

Kaggle payload cap (1 MB) carries no request logs: both arms restart from the
identical replayed state with empty conversation. A-vs-original fidelity is
reported as a diagnostic (first post-T actions vs the logged post-T plan),
not as a gate.
"""
from __future__ import annotations

import contextlib
import os
import threading
import time
from pathlib import Path
from typing import Any

from arc3_research.probe_budget import ProbeBudget

# game_id -> fork parameters. Cuts are cumulative executed env actions
# (verified by scripts/replay_026_prefix.py: 111/111 checkpoints exact).
FORKS = {
    "ft09-0d8bbf25": {"cut": 11, "analysis_step": 5, "kind": "legend_recheck",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
    "tr87-cd924810": {"cut": 132, "analysis_step": 17, "kind": "crop_recheck",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
    "m0r0-492f87ba": {"cut": 22, "analysis_step": 6, "kind": "sim_recheck",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
    "r11l-495a7899": {"cut": 40, "analysis_step": 25, "kind": "control",
                      "max_extra_actions": 30, "max_extra_seconds": 250},
}

# Short recorded failure signatures (not solutions) bundled as data. The full
# request logs exceed the notebook payload cap and stay local.
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
        return {"patch": "failure-repair-v1", "forks": list(FORKS),
                "probe_quota": 0,
                "rule": "host evidence only; no new tool API; no answer injection"}


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
        for item in actions[:cut]:
            name = item["action"]["id"]
            data = dict(item["action"].get("data") or {})
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
        entry = {"game_id": resolved[requested], "cut": cut,
                 "replay_actions": cut}
        if is_b:
            from inference.framework.solver import _grid_from_state
            grid = _grid_from_state(session.game.current_state)
            text = RECHECK[spec_fork["kind"]](grid)
            analyzer._history_messages = [{"role": "user", "content": text}]
            entry["recheck_kind"] = spec_fork["kind"]
            entry["recheck_chars"] = len(text)
        # Bounded continuation sharing the arm budget. Mirror _play_one error
        # handling so one fork failure is recorded, not silent.
        prev_max_actions = bm.solver.max_actions_per_game
        prev_max_runtime = bm.solver.max_runtime_s_per_game
        bm.solver.max_actions_per_game = cut + int(spec_fork["max_extra_actions"])
        bm.solver.max_runtime_s_per_game = float(spec_fork["max_extra_seconds"])
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
