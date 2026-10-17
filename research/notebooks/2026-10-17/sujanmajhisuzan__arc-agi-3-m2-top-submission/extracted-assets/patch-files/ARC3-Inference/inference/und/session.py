"""CONTRACT: Host-resident coordinator UndSession for ARC-AGI-3 (Rules 01, 03, 04, 05).
Coordinates game-level world model state on host: passive observation hook (observe),
step prediction and verification hooks for wm.run (begin_step / end_step),
level rollover handling, and JSONL telemetry streaming.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

from inference.und.adapter_duck import adapt_transition, extract_frame_dto, grid_hash
from inference.und.breakers import CircuitBreakerManager
from inference.und.claim_graph import Claim, ClaimConfig, ClaimGraph, GraphEvent, create_transition_record
from inference.und.coder_ast_validator import ModelHookRegistry
from inference.und.undo import UndoProfile, create_undo_profile
from inference.und.config.thresholds import DEFAULT_THRESHOLDS, ThresholdsConfig
from inference.und.core_model import CoreModel, ObservedEdgesOverlay, SimState, StepResult
from inference.und.cycle_detector import VisibleCycle
from inference.und.goals import GoalJudge, GoalJudgementResult
from inference.und.guards import DeathActionGuard, NoopRepeatGuard, action_signature, compute_interior_grid_hash
from inference.und.perception.arga_lite import extract_arga_snapshot
from inference.und.perception.tracker import PersistentObjectTracker
from inference.und.shadow import ShadowVerifier
from inference.und.telemetry import FailureTaxonomy, TelemetryEvent, UndTelemetry
from inference.und.timer import ExplorationPolicy, TimerStatus, TimerTracker
from inference.und.types import FrameDTO, TransitionRecord

logger = logging.getLogger(__name__)


class UndSession:
    """Host-resident session coordinator managing pure world model logic for a single game."""

    def __init__(self, game_id: str = "", level: int = 0, config: ThresholdsConfig | None = None, log_path: Path | str | None = None) -> None:
        self.game_id = game_id
        self.level = level
        self.step_index = 0
        self.config = config or DEFAULT_THRESHOLDS

        cg_cfg = ClaimConfig(n_direct=dict(self.config.n_direct), n_levels=dict(self.config.n_levels), n_minus=self.config.n_minus)
        self.claim_graph = ClaimGraph(cfg=cg_cfg); self.overlay = ObservedEdgesOverlay()
        self.core_model = CoreModel(claim_graph=self.claim_graph, overlay=self.overlay)
        self.timer = TimerTracker(config=self.config); self.tracker = PersistentObjectTracker(config=self.config)
        self.telemetry = UndTelemetry(game_id=self.game_id, log_path=log_path)
        self.shadow_verifier = ShadowVerifier(window_steps=self.config.resolve("shadow_window_steps", 5))
        self.probes_used_on_level: int = 0
        self.exploration_policy = ExplorationPolicy(config=self.config, timer=self.timer)
        self.breakers = CircuitBreakerManager(config=self.config, level=self.level)
        self.undo_profile = create_undo_profile(self.game_id, expose_undo=self.config.expose_undo, max_depth=self.config.undo_max_depth)
        self.hooks = ModelHookRegistry(); self.death_guard = DeathActionGuard(); self.noop_guard = NoopRepeatGuard()
        self.cycle_detector = VisibleCycle(min_actions=4, max_period=8, min_cycles=2)
        self.last_cycle_detected: dict[str, Any] | None = None
        self.last_animation_info: dict[str, Any] | None = None

        self.current_frame: FrameDTO | None = None
        self.history: list[TransitionRecord] = []
        self.pending_step: dict[str, Any] | None = None
        self.pending_category: str = "manual"
        self.last_events: list[GraphEvent] = []
        self.goal_judge = GoalJudge()
        self.last_goal_verdict: GoalJudgementResult | None = None
        self.current_goal: dict[str, Any] | None = None

    def set_log_path(self, log_path: Path | str) -> None:
        self.telemetry.set_log_path(log_path)

    def set_initial_frame(self, raw_frame: Any) -> None:
        """Seed initial frame for the current level or game."""
        self.current_frame = extract_frame_dto(raw_frame, step=self.step_index, level=self.level)
        if self.current_frame and self.current_frame.grid:
            try:
                snap = extract_arga_snapshot(self.current_frame.grid)
                self.tracker.update(snap, self.step_index)
                self.telemetry.log_level_start(self.level, self.step_index, self.current_frame.shape)
            except Exception as e:
                logger.debug("Failed to extract initial ARGA snapshot: %s", e)

    def observe(
        self,
        record: TransitionRecord | dict[str, Any] | Any = None,
        **kwargs: Any,
    ) -> list[GraphEvent]:
        """Passive observation hook processing a single executed transition (Rule 05 В§4)."""
        # 1. Normalize input into a validated TransitionRecord
        if isinstance(record, TransitionRecord):
            tr = record
        elif isinstance(record, dict):
            tr = adapt_transition(
                before=record.get("before", kwargs.get("before")),
                action=record.get("action", kwargs.get("action")),
                after=record.get("after", kwargs.get("after")),
                result=record.get("result", record.get("result_flags", kwargs.get("result"))),
                category=record.get("category", kwargs.get("category", self.pending_category)),
                index=record.get("index", kwargs.get("index", self.step_index)),
            )
        else:
            tr = adapt_transition(
                before=kwargs.get("before"), action=kwargs.get("action"), after=kwargs.get("after"),
                result=kwargs.get("result"), category=kwargs.get("category", self.pending_category),
                index=kwargs.get("index", self.step_index),
            )

        # 2. Check level rollover (Rule 04 В§4; Rule 05 В§1)
        new_level = tr.level
        if self.current_frame is not None and new_level != self.level:
            old_level = self.level
            self.overlay.clear()
            carried = self.claim_graph.carry_to_new_level()
            self.shadow_verifier.on_level_start(level=new_level, carried_claims=carried)
            self.timer.reset()
            self.probes_used_on_level = 0
            self.breakers.on_level_start(new_level); self.undo_profile.on_level_start(new_level)
            self.death_guard.note_level(new_level); self.noop_guard.note_level(new_level); self.cycle_detector.clear()
            self.tracker = PersistentObjectTracker(config=self.config)
            self.level = new_level
            self.telemetry.log_level_finish(old_level, self.step_index, "WIN", "level_completed")
            fshape = (len(tr.after_grid), len(tr.after_grid[0])) if tr.after_grid else (0, 0)
            self.telemetry.log_level_start(new_level, self.step_index, fshape)

        # 3. Record observed edge into overlay (unconditional empirical priority)
        b_hash, a_hash = grid_hash(tr.before_grid), grid_hash(tr.after_grid)
        action_id, res_flags = tr.action.action_id, tr.result_flags
        act_data = tr.action.data if hasattr(tr.action, "data") else {}
        act_sig = action_signature({"action": action_id, "data": act_data})
        # Animation & transient cell detection (Sprint 4)
        anim_frames = res_flags.get("animation_frames") or res_flags.get("animation") or kwargs.get("animation_frames") or []
        anim_info: dict[str, Any] | None = None
        has_transient = False
        if anim_frames:
            try:
                from inference.und.perception.animation import analyze_animation_trajectory, collapse_animation_chain
                anim_info = analyze_animation_trajectory(collapse_animation_chain(tr.before_grid, anim_frames))
                has_transient = bool(anim_info and anim_info.get("transient_pixel_count", 0) > 0)
            except Exception:
                pass
        self.last_animation_info = anim_info

        interior_hash = compute_interior_grid_hash(tr.before_grid)
        is_term = bool(res_flags.get("game_over") or res_flags.get("done") or res_flags.get("run_complete"))
        term_status = "GAME_OVER" if res_flags.get("game_over") else ("WIN" if (res_flags.get("done") or res_flags.get("run_complete")) else None)
        zero_delta = (tr.before_grid == tr.after_grid)
        if term_status == "GAME_OVER":
            self.death_guard.record_death(interior_hash, act_sig)
        if zero_delta and not has_transient:
            self.noop_guard.record_noop(interior_hash, act_sig)
        cyc = self.cycle_detector.observe(b_hash, act_sig, a_hash)
        if cyc:
            self.last_cycle_detected = cyc
        self.breakers.record_transition(zero_delta and not has_transient, is_null=bool(zero_delta and not res_flags.get("gameplay_changed") and not has_transient))
        self.overlay.record(
            before_hash=b_hash, action_id=action_id, after_hash=a_hash, is_terminal=is_term,
            terminal_status=term_status, zero_delta=zero_delta, after_grid=tr.after_grid,
        )

        # 4. Stream to JSONL telemetry
        self.telemetry.log_transition(self.level, self.step_index, action_id, tr.category, b_hash, a_hash, res_flags, zero_delta)
        if is_term and new_level == self.level:
            cur_rec = self.telemetry.level_records.get(self.level)
            if cur_rec is None or cur_rec.outcome == "IN_PROGRESS":
                lvl_out = "DEFEAT" if term_status == "GAME_OVER" else "WIN"
                lvl_reason = "game_over" if term_status == "GAME_OVER" else ("run_complete" if res_flags.get("run_complete") else "level_completed")
                self.telemetry.log_level_finish(self.level, self.step_index, outcome=lvl_out, stop_reason=lvl_reason)
            if res_flags.get("run_complete"):
                self.finish_game(FailureTaxonomy.ALL_LEVELS_COMPLETED)

        # 5-6. Update timer & object tracker
        self.timer.observe_transition(tr.before_grid, tr.after_grid)
        try:
            self.tracker.update(extract_arga_snapshot(tr.after_grid), self.step_index)
        except Exception:
            pass

        # 7. Execute 3-valued ClaimGraph judgment
        ctx_feat: dict[str, Any] = {}
        if action_id in ("ACTION7", "UNDO") and self.history:
            restored = (tr.after_grid == self.history[-1].before_grid)
            ctx_feat["undo_exact"] = restored
            self.undo_profile.record_probe(restored, self.step_index)
        cg_tr = create_transition_record(
            tid=tr.index, level=self.level, action_id=action_id, action_data=act_data,
            before_grid=tr.before_grid, after_grid=tr.after_grid, terminal=term_status, context_features=ctx_feat,
        )
        events = self.claim_graph.judge_transition(cg_tr)
        self.last_events = events
        self.shadow_verifier.observe_transition(cg_tr, self.claim_graph, self.telemetry)

        # 7c. Execute GoalJudge classification with Triangulated Defeat (Rule 02 В§10)
        final_anim = anim_frames[-1] if (isinstance(anim_frames, list) and anim_frames) else None
        summary_traj = str(anim_info.get("summary_phrase", "")) if anim_info else ""
        self.last_goal_verdict = self.goal_judge.observe_step(
            before_grid=tr.before_grid, after_grid=tr.after_grid,
            level_completed=(term_status == "WIN"), is_defeat=(term_status == "GAME_OVER"),
            action=action_id, step_index=self.step_index, level=self.level,
            history_actions=[h.action.action_id for h in self.history],
            final_animation_frame=final_anim, transient_trajectory=summary_traj,
        )
        if self.goal_judge.active_goal:
            self.current_goal = self.goal_judge.active_goal.to_dict()

        # 8. Update current frame and history
        try:
            score_val = int(res_flags.get("score", 0))
        except (ValueError, TypeError):
            score_val = 0
        self.current_frame = extract_frame_dto(tr.after_grid, step=self.step_index, level=self.level, score=score_val)
        if tr.category in ("probe", "evidence_probe"):
            self.probes_used_on_level += 1
        self.history.append(tr)
        self.step_index += 1
        return events

    def _get_actor_color(self) -> int | None:
        for c in self.claim_graph.active_claims():
            if c.kind == "controlled" and "sig" in c.predicate:
                return int(c.predicate["sig"][0])
        if self.current_frame and self.current_frame.grid:
            counts = {c: sum(row.count(c) for row in self.current_frame.grid) for c in {c for row in self.current_frame.grid for c in row if c != 0}}
            return 1 if 1 in counts else (min(counts.keys(), key=lambda c: counts[c]) if counts else None)
        return None

    def begin_step(self, action: Any, category: str = "manual") -> dict[str, Any]:
        """Pre-action simulation hook for wm.run (Rule 05 В§4)."""
        act_str = str(action)
        self.pending_category = category
        pred: StepResult | None = None
        if self.current_frame and self.current_frame.grid:
            pred = self.core_model.step(SimState.from_grid(self.current_frame.grid, actor_color=self._get_actor_color(), step_count=self.step_index), act_str)
        self.pending_step = {"action": act_str, "category": category, "prediction": pred}
        pred_hash = pred.state.grid_hash if pred else None
        self.telemetry.log_begin_step(self.level, self.step_index, act_str, category, pred_hash)
        return {"action": act_str, "category": category, "predicted_hash": pred_hash, "accepted": True}

    def end_step(self) -> dict[str, Any]:
        """Post-action verification hook for wm.run (Rule 05 В§4)."""
        if not self.pending_step:
            return {"ok": True, "verdict": "NO_PREDICTION", "brusentsov_verdict": "ABSTAIN", "diagnostic": ""}
        pending = self.pending_step
        self.pending_step, self.pending_category = None, "manual"
        pred: StepResult | None = pending.get("prediction")
        if not self.history or pred is None:
            return {"ok": True, "verdict": "NO_PREDICTION", "brusentsov_verdict": "ABSTAIN", "predicted_hash": None, "actual_hash": None, "diagnostic": ""}
        last_tr = self.history[-1]
        actual_hash = grid_hash(last_tr.after_grid)
        match = (actual_hash == pred.state.grid_hash)
        self.breakers.record_check_call()
        if pending.get("category") == "planned":
            (self.breakers.record_plan_match() if match else self.breakers.record_plan_divergence())
        diag_msg, counterexample = "", None
        if not match:
            from inference.und.diag import format_step_mismatch_diagnostic
            diag_msg = format_step_mismatch_diagnostic(pending.get("action", ""), [list(r) for r in pred.state.grid], last_tr.after_grid, self.step_index)
            counterexample = {"before": last_tr.before_grid, "action": pending.get("action", ""), "after": last_tr.after_grid}
        leg_v, bru_v = ("MATCH", "FOLLOW") if match else ("MISMATCH", "NULL")
        self.telemetry.log_end_step(self.level, self.step_index, leg_v, pred.state.grid_hash, actual_hash)
        return {
            "ok": True, "verdict": leg_v, "brusentsov_verdict": bru_v,
            "is_follow": match, "is_null": not match, "counterexample": counterexample,
            "predicted_hash": pred.state.grid_hash, "actual_hash": actual_hash, "diagnostic": diag_msg,
        }

    def plan(
        self, target: Any = None, color: int | None = None, max_depth: int = 20,
        strategy: str = "astar", collect_all: bool = False,
    ) -> dict[str, Any]:
        """Execute zero-action in-memory pathfinding towards goal or target."""
        self.breakers.record_replan_call()
        if self.breakers.is_tripped:
            return {"actions": [], "cost": 0, "success": False, "reason": f"Circuit breaker tripped: {self.breakers.primary_tripped_reason}. Disabled on level {self.level}, play normally."}
        if not self.current_frame or not self.current_frame.grid:
            return {"actions": [], "cost": 0, "success": False, "reason": "No current frame"}
        from inference.und.planner import SimulationPlanner
        s_state = SimState.from_grid(self.current_frame.grid, actor_color=self._get_actor_color(), step_count=self.step_index)
        t_pos = tuple(target) if isinstance(target, (list, tuple)) and len(target) == 2 else None
        t_col = color if color is not None else (self.goal_judge.active_goal.color if self.goal_judge.active_goal else None)
        c_all = collect_all or bool(self.goal_judge.active_goal and self.goal_judge.active_goal.kind in ("collect_all", "clear_all"))
        if t_pos is None and self.goal_judge.active_goal and isinstance(self.goal_judge.active_goal.target, (list, tuple)) and len(self.goal_judge.active_goal.target) == 2:
            t_pos = tuple(self.goal_judge.active_goal.target)
        planner = SimulationPlanner(core_model=self.core_model, max_search_nodes=self.config.plan_max_states)
        res = planner.plan_to_target(s_state, target_pos=t_pos, target_color=t_col, collect_all=c_all)
        from inference.und.actions import ENGINE_TO_DUCK_MAP
        d_acts = [ENGINE_TO_DUCK_MAP.get(a, a) for a in res.actions if a not in ("ACTION7", "UNDO")]
        return {"actions": d_acts, "cost": len(d_acts), "success": res.success, "reason": res.reason}

    def get_budget(self) -> dict[str, Any]:
        """Query action and probe exploration budgets for current level (Rule 01 В§4, Rule 04 В§7)."""
        b = self.exploration_policy.get_budget(self.probes_used_on_level, level=self.level).to_dict()
        b["circuit_breaker_tripped"] = self.breakers.is_tripped
        b["tripped_breakers"] = list(self.breakers.tripped_breakers)
        return b

    def can_probe(self) -> tuple[bool, str]:
        """Check if exploratory probing is allowed under current budget and timer constraints."""
        return self.exploration_policy.can_probe(self.probes_used_on_level, level=self.level)

    def status(self) -> dict[str, Any]:
        """Return a structured JSON-serializable status report of current session."""
        frame_shape = (len(self.current_frame.grid), len(self.current_frame.grid[0])) if self.current_frame and self.current_frame.grid else (0, 0)
        return {
            "game_id": self.game_id, "level": self.level, "step_index": self.step_index,
            "current_frame_shape": frame_shape, "timer": self.timer.status(self.level, probes_used=self.probes_used_on_level).to_dict(),
            "budget": self.get_budget(), "probes_used_on_level": self.probes_used_on_level,
            "circuit_breaker": self.breakers.get_status().to_dict(),
            "claims_active": len(self.claim_graph.active_claims()),
            "claims_confirmed": len(self.claim_graph.confirmed_claims()),
            "overlay_edges": len(self.overlay), "tracked_objects": len(self.tracker.tracks),
            "history_length": len(self.history), "telemetry_summary": self.telemetry.get_summary(),
            "current_goal": self.current_goal,
            "victory_exemplars": len(self.goal_judge.victory_exemplars),
            "defeat_exemplars": len(self.goal_judge.defeat_exemplars),
            "shadow": self.shadow_verifier.get_summary(),
        }

    def format_telemetry_report(self) -> str:
        return self.telemetry.format_markdown_report()

    def digest(self, max_tokens: int | None = None) -> str:
        from inference.und.digest import build_mechanics_digest
        return build_mechanics_digest(self, max_tokens=max_tokens)

    def set_goal(self, goal_type: str, color: int | None = None, target: Any = None, criteria: dict[str, Any] | None = None) -> dict[str, Any]:
        g = self.goal_judge.set_goal(kind=goal_type, color=color, target=target, criteria=criteria, level=self.level, step_index=self.step_index)
        self.current_goal = g.to_dict()
        return {"registered": True, "goal_id": g.goal_id, "goal_type": g.goal_type or g.kind, "active": True}

    def register_claim(self, law: str, subject: Any = None, predicate: Any = None, kind: str | None = None, expected: Any = None) -> dict[str, Any]:
        from inference.und.claim_graph import ClaimStatus
        inferred_kind = kind or ("action_effect" if any(k in law.lower() for k in ("up", "down", "left", "right", "move")) else ("passability" if any(k in law.lower() for k in ("wall", "solid", "block")) else ("lethal" if any(k in law.lower() for k in ("kill", "death", "hazard")) else "hypothesis")))
        subj = tuple(subject) if isinstance(subject, (list, tuple)) else ((subject,) if subject is not None else (law,))
        pred = dict(predicate) if isinstance(predicate, dict) else ({"expected": expected} if expected is not None else {"law": law})
        claim_id = f"claim_{len(self.claim_graph.claims) + 1}"
        self.claim_graph.add(Claim(id=claim_id, kind=inferred_kind, subject=subj, predicate=pred, status=ClaimStatus.UNDECIDED))
        return {"registered": True, "claim_id": claim_id, "kind": inferred_kind, "status": "?", "detail": f"Claim {claim_id} registered"}

    def card(self, format: str = "text", max_tokens: int | None = None) -> str | dict[str, Any]:
        """Generate structured knowledge card with confirmed laws and hypotheses."""
        from inference.und.card import build_knowledge_card
        return build_knowledge_card(self, format=format, max_tokens=max_tokens or self.config.card_max_tokens)

    def reset(self, level: int = 0) -> None:
        """Reset state for a new game or restart."""
        self.level, self.step_index, self.probes_used_on_level = level, 0, 0
        self.overlay.clear(); self.timer.reset(); self.breakers.on_level_start(level); self.undo_profile.on_level_start(level); self.hooks.clear()
        self.death_guard.note_level(level); self.noop_guard.note_level(level); self.cycle_detector.clear()
        self.tracker = PersistentObjectTracker(config=self.config)
        self.current_frame, self.pending_step, self.pending_category, self.current_goal = None, None, "manual", None
        self.goal_judge.reset(); self.history.clear(); self.last_events.clear(); self.last_animation_info = None

    def check_action_safety(self, action: Any, grid: Sequence[Sequence[int]] | None = None) -> tuple[bool, str]:
        """Pre-execution safety check against known fatal transitions and no-ops."""
        g = grid or (self.current_frame.grid if self.current_frame else None)
        interior_hash = compute_interior_grid_hash(g)
        act_sig = action_signature(action)
        if self.death_guard.is_known_fatal(interior_hash, act_sig):
            return False, f"KNOWN_FATAL_ACTION: Action '{act_sig}' previously caused GAME_OVER from this state."
        if self.noop_guard.is_known_noop(interior_hash, act_sig):
            return False, f"KNOWN_NOOP_ACTION: Action '{act_sig}' previously produced zero change from this state."
        return True, ""

    def filter_safe_actions(self, available_actions: Sequence[Any], grid: Sequence[Sequence[int]] | None = None) -> list[Any]:
        """Filter out known fatal actions from available action choices."""
        g = grid or (self.current_frame.grid if self.current_frame else None)
        interior_hash = compute_interior_grid_hash(g)
        return self.death_guard.filter_safe_actions(interior_hash, available_actions)

    def register_hook(self, hook_name: str, code: str) -> dict[str, Any]:
        """Validate, hoist constants, and register a world model hook (Rule 04 В§3, Rule 05 В§4)."""
        return self.hooks.register_hook(hook_name, code)

    def finish_game(self, reason: str | FailureTaxonomy = FailureTaxonomy.SUCCESS) -> TelemetryEvent | None:
        """Record game completion in telemetry if not already finished (Rule 05 В§8)."""
        if not self.telemetry.game_stop_reason:
            return self.telemetry.log_game_finish(self.level, self.step_index, reason)
        return None


# Host-side Thread-safe Session Registry (Rule 05 В§3)
_SESSIONS_LOCK = threading.Lock()
_SESSIONS: dict[str, UndSession] = {}


def register_session(session: UndSession) -> None:
    with _SESSIONS_LOCK:
        _SESSIONS[session.game_id] = session


def get_session(game_id: str) -> UndSession | None:
    with _SESSIONS_LOCK:
        if game_id and game_id in _SESSIONS:
            return _SESSIONS[game_id]
        if len(_SESSIONS) == 1:
            return next(iter(_SESSIONS.values()))
        return _SESSIONS.get(game_id)


def clear_sessions() -> None:
    with _SESSIONS_LOCK:
        _SESSIONS.clear()
