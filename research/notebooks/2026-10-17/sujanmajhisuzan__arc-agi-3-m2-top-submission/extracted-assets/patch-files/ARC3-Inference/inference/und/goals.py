"""CONTRACT: Goal Hypotheses, Victory/Defeat Exemplars, and Goal Judge (Rules 01, 02, 05).

Pure Deterministic Classification (Rule 02 В§10, В§11):
Verdicts: HOLDS_DIRECT, VIOLATED, UNCOVERED_WIN, NA, UNOBSERVABLE.
Fallback chain: after_grid -> final_animation_frame -> model_prediction -> UNOBSERVABLE.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from inference.und.perception.frame_diff import compute_grid_frame_diff
from inference.und.types import Grid2D

logger = logging.getLogger(__name__)

CANONICAL_GOAL_KINDS: tuple[str, ...] = ("touch", "reach", "collect_all", "clear_all", "click_all", "custom")
GOAL_KIND_ALIASES: dict[str, str] = {
    "target_color": "touch", "reach_exit": "reach", "eliminate_color": "clear_all",
}


@dataclass
class VictoryExemplar:
    """Precedent of level completion вЂ” grounding for positive invariants (xy -> FOLLOW)."""
    level_index: int
    total_steps: int
    action_sequence: list[str | int] = field(default_factory=list)
    final_action: str | int = 0
    target_color: int | None = None
    target_coords: tuple[int, int] | None = None
    actor_pos_before: tuple[int, int] | None = None
    actor_pos_after: tuple[int, int] | None = None
    before_grid: Grid2D = field(default_factory=list)
    after_grid: Grid2D = field(default_factory=list)
    key_transitions: list[dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    associated_goal_id: str | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level_index": self.level_index, "total_steps": self.total_steps,
            "action_sequence": list(self.action_sequence), "final_action": self.final_action,
            "target_color": self.target_color, "target_coords": self.target_coords,
            "actor_pos_before": self.actor_pos_before, "actor_pos_after": self.actor_pos_after,
            "explanation": self.explanation, "associated_goal_id": self.associated_goal_id,
        }

    def format_for_prompt(self) -> str:
        seq = " -> ".join(str(a) for a in self.action_sequence[:12])
        if len(self.action_sequence) > 12:
            seq += "..."
        lines = [
            f"LAST VICTORY (Level {self.level_index}, {self.total_steps} steps):",
            f"  Sequence: [{seq}], Final Action: {self.final_action}",
        ]
        if self.target_color is not None:
            lines.append(f"  Target Reached: Color {self.target_color}")
        if self.target_coords is not None:
            lines.append(f"  Target Coords: {self.target_coords}")
        if self.associated_goal_id:
            lines.append(f"  Confirmed Goal: {self.associated_goal_id}")
        return "\n".join(lines)


@dataclass
class DefeatExemplar:
    """Precedent of fatal error вЂ” grounding for negative barrier invariants (xy'_0 -> NULL)."""
    level_index: int
    fatal_step: int
    fatal_action: str | int
    fatal_coords: tuple[int, int] | None = None
    actor_pos_before: tuple[int, int] | None = None
    hazard_color: int | None = None
    before_grid: Grid2D = field(default_factory=list)
    fatal_grid: Grid2D = field(default_factory=list)
    environment_signal: str = "DEFEAT"
    explanation: str = ""
    fatal_step_diff: dict[str, Any] = field(default_factory=dict)
    valid_prefix_actions: list[str | int] = field(default_factory=list)
    fatal_transient_trajectory: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level_index": self.level_index, "fatal_step": self.fatal_step,
            "fatal_action": self.fatal_action, "fatal_coords": self.fatal_coords,
            "actor_pos_before": self.actor_pos_before, "hazard_color": self.hazard_color,
            "environment_signal": self.environment_signal, "explanation": self.explanation,
            "valid_prefix_count": len(self.valid_prefix_actions),
            "valid_prefix_actions": list(self.valid_prefix_actions),
            "fatal_transient_trajectory": self.fatal_transient_trajectory,
        }

    def format_for_prompt(self) -> str:
        lines = [f"LAST DEFEAT (Level {self.level_index}, Step {self.fatal_step}): Action {self.fatal_action}"]
        if self.actor_pos_before:
            lines.append(f"  Actor Position: {self.actor_pos_before}")
        if self.hazard_color is not None:
            lines.append(f"  Hazard Color: {self.hazard_color}")
        if self.fatal_transient_trajectory:
            lines.append(f"  Fatal Animation: {self.fatal_transient_trajectory}")
        if self.valid_prefix_actions:
            pref = " -> ".join(str(a) for a in self.valid_prefix_actions[:10]) + ("..." if len(self.valid_prefix_actions) > 10 else "")
            lines.append(f"  Safe Prefix (RETAIN PREFIX): Steps 1..{len(self.valid_prefix_actions)} were SAFE: [{pref}] (AVOID {self.fatal_action} at step {self.fatal_step})")
        return "\n".join(lines)


def triangulate_defeat(
    before_grid: Grid2D,
    fatal_or_reset_grid: Grid2D,
    animation_frames: Sequence[Grid2D] | None = None,
) -> tuple[Grid2D, Grid2D]:
    """Isolate fatal interaction frame F_fatal from alive frame F_alive and reset frame F_reset."""
    if animation_frames and len(animation_frames) > 0:
        return before_grid, animation_frames[-1]
    return before_grid, fatal_or_reset_grid


@dataclass
class GoalHypothesis:
    """Hypothesis about the winning condition for the level (Rule 02 В§10)."""
    goal_id: str
    kind: str
    goal_type: str = ""
    color: int | None = None
    target: Any = None
    criteria: dict[str, Any] = field(default_factory=dict)
    level: int = 0
    step_index: int = 0
    status: str = "PENDING"
    n_confirmed: int = 0
    n_violated: int = 0
    exemplar_ids: list[str] = field(default_factory=list)

    def evaluate_satisfaction(
        self, before_grid: Grid2D, after_grid: Grid2D,
        actor_pos_before: tuple[int, int] | None = None,
        actor_pos_after: tuple[int, int] | None = None,
        action: str | int = 0,
    ) -> bool:
        """Evaluate if the goal hypothesis condition is satisfied on this step."""
        if not after_grid:
            return False
        k = GOAL_KIND_ALIASES.get(self.kind, self.kind)
        if k == "touch":
            if self.color is not None:
                if actor_pos_after and before_grid:
                    r, c = actor_pos_after
                    if 0 <= r < len(before_grid) and 0 <= c < len(before_grid[0]) and before_grid[r][c] == self.color:
                        return True
                c_b = sum(row.count(self.color) for row in before_grid) if before_grid else 0
                return sum(row.count(self.color) for row in after_grid) < c_b
            if self.target is not None and isinstance(self.target, (list, tuple)) and len(self.target) == 2:
                return actor_pos_after == tuple(self.target)
        elif k == "reach":
            if self.target is not None and isinstance(self.target, (list, tuple)) and len(self.target) == 2:
                return actor_pos_after == tuple(self.target)
        elif k in ("collect_all", "clear_all"):
            if self.color is not None:
                c_b = sum(row.count(self.color) for row in before_grid) if before_grid else 0
                return c_b > 0 and sum(row.count(self.color) for row in after_grid) == 0
        elif k == "click_all":
            return str(action).upper() in ("ACTION6", "6", "CLICK")
        elif k == "custom":
            p = self.criteria.get("predicate")
            if p == "color_zero" and self.color is not None:
                return sum(row.count(self.color) for row in after_grid) == 0
            if p == "reached_coords" and self.target is not None:
                return actor_pos_after == tuple(self.target)
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id, "goal_type": self.goal_type or self.kind, "kind": self.kind,
            "color": self.color, "target": self.target, "criteria": dict(self.criteria), "status": self.status,
            "n_confirmed": self.n_confirmed, "n_violated": self.n_violated,
            "exemplar_ids": list(self.exemplar_ids),
        }


@dataclass
class GoalJudgementResult:
    """Result of step classification against active goal (Rule 02 В§10.2)."""
    verdict: str
    goal_id: str | None
    goal_satisfied: bool
    level_completed: bool
    is_defeat: bool
    diagnostic: str = ""
    victory_exemplar: VictoryExemplar | None = None
    defeat_exemplar: DefeatExemplar | None = None

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "verdict": self.verdict, "goal_id": self.goal_id,
            "goal_satisfied": self.goal_satisfied, "level_completed": self.level_completed,
            "is_defeat": self.is_defeat, "diagnostic": self.diagnostic,
        }
        if self.victory_exemplar:
            res["victory_exemplar"] = self.victory_exemplar.to_dict()
        if self.defeat_exemplar:
            res["defeat_exemplar"] = self.defeat_exemplar.to_dict()
        return res


class GoalJudge:
    """Pure deterministic judge classifying transitions against goal hypotheses (Rule 02 В§10)."""

    def __init__(self) -> None:
        self.active_goal: GoalHypothesis | None = None
        self.goals: dict[str, GoalHypothesis] = {}
        self.victory_exemplars: list[VictoryExemplar] = []
        self.defeat_exemplars: list[DefeatExemplar] = []

    def set_goal(
        self, kind: str, color: int | None = None, target: Any = None,
        criteria: dict[str, Any] | None = None, level: int = 0, step_index: int = 0,
    ) -> GoalHypothesis:
        """Register or update active goal focus for current level."""
        canonical_kind = GOAL_KIND_ALIASES.get(kind, kind)
        goal_id = f"goal_{level}_{step_index}"
        goal = GoalHypothesis(
            goal_id=goal_id, kind=canonical_kind, goal_type=kind, color=color, target=target,
            criteria=dict(criteria or {}), level=level, step_index=step_index,
        )
        self.active_goal, self.goals[goal_id] = goal, goal
        return goal

    def record_victory(self, exemplar: VictoryExemplar) -> None:
        self.victory_exemplars.append(exemplar)
        if len(self.victory_exemplars) > 20:
            self.victory_exemplars.pop(0)

    def record_defeat(self, exemplar: DefeatExemplar) -> None:
        self.defeat_exemplars.append(exemplar)
        if len(self.defeat_exemplars) > 20:
            self.defeat_exemplars.pop(0)

    def observe_step(
        self, before_grid: Grid2D, after_grid: Grid2D | None, level_completed: bool,
        is_defeat: bool, action: str | int, actor_before: tuple[int, int] | None = None,
        actor_after: tuple[int, int] | None = None, step_index: int = 0, level: int = 0,
        history_actions: list[str | int] | None = None,
        final_animation_frame: Grid2D | None = None,
        model_prediction_grid: Grid2D | None = None,
        transient_trajectory: str = "",
    ) -> GoalJudgementResult:
        """Classify step outcome per Rule 02 В§10.2 truth table."""
        effective_after = final_animation_frame or after_grid or model_prediction_grid
        if not effective_after:
            return GoalJudgementResult(
                verdict="UNOBSERVABLE", goal_id=self.active_goal.goal_id if self.active_goal else None,
                goal_satisfied=False, level_completed=level_completed, is_defeat=is_defeat,
                diagnostic="State after step is completely unobservable.",
            )
        if history_actions and history_actions[-1] == action:
            actions_hist = list(history_actions)
        else:
            actions_hist = list(history_actions or []) + [action]
        if is_defeat:
            f_alive, f_fatal = triangulate_defeat(before_grid, effective_after, [final_animation_frame] if final_animation_frame else None)
            return self._handle_defeat(f_alive, f_fatal, action, actor_before, step_index, level, actions_hist, transient_trajectory=transient_trajectory)
        satisfied = False
        if self.active_goal:
            satisfied = self.active_goal.evaluate_satisfaction(before_grid, effective_after, actor_before, actor_after, action)
        return self._classify_table(satisfied, level_completed, before_grid, effective_after, action, actor_before, actor_after, step_index, level, actions_hist)

    def _handle_defeat(
        self, before_grid: Grid2D, fatal_grid: Grid2D, action: str | int,
        actor_before: tuple[int, int] | None, step_index: int, level: int, actions_hist: list[str | int],
        transient_trajectory: str = "",
    ) -> GoalJudgementResult:
        diff = compute_grid_frame_diff(before_grid, fatal_grid) if before_grid else {}
        hazard_color: int | None = None
        if actor_before and before_grid:
            r, c = actor_before
            if 0 <= r < len(before_grid) and 0 <= c < len(before_grid[0]):
                hazard_color = before_grid[r][c]
        valid_prefix = actions_hist[:-1] if actions_hist else []
        def_ex = DefeatExemplar(
            level_index=level, fatal_step=step_index, fatal_action=action, actor_pos_before=actor_before,
            hazard_color=hazard_color, before_grid=before_grid, fatal_grid=fatal_grid, fatal_step_diff=diff,
            valid_prefix_actions=valid_prefix, fatal_transient_trajectory=transient_trajectory,
            explanation=f"Fatal defeat on step {step_index} with action {action}",
        )
        self.record_defeat(def_ex)
        verdict, diag = "NA", ""
        if self.active_goal and self.active_goal.color is not None and self.active_goal.color == hazard_color:
            self.active_goal.status, self.active_goal.n_violated = "VIOLATED", self.active_goal.n_violated + 1
            verdict, diag = "VIOLATED", f"Goal targeted hazard color {hazard_color} which triggered defeat."
        return GoalJudgementResult(
            verdict=verdict, goal_id=self.active_goal.goal_id if self.active_goal else None,
            goal_satisfied=False, level_completed=False, is_defeat=True, diagnostic=diag, defeat_exemplar=def_ex,
        )

    def _classify_table(
        self, satisfied: bool, level_completed: bool, before_grid: Grid2D, after_grid: Grid2D,
        action: str | int, actor_before: tuple[int, int] | None, actor_after: tuple[int, int] | None,
        step_index: int, level: int, actions_hist: list[str | int],
    ) -> GoalJudgementResult:
        gid = self.active_goal.goal_id if self.active_goal else None
        if satisfied and level_completed:
            assert self.active_goal is not None
            self.active_goal.status, self.active_goal.n_confirmed = "HOLDS_DIRECT", self.active_goal.n_confirmed + 1
            tgt_coords = actor_after or (self.active_goal.target if isinstance(self.active_goal.target, tuple) else None)
            vic_ex = VictoryExemplar(
                level_index=level, total_steps=step_index, action_sequence=actions_hist, final_action=action,
                target_color=self.active_goal.color, target_coords=tgt_coords, actor_pos_before=actor_before,
                actor_pos_after=actor_after, before_grid=before_grid, after_grid=after_grid, associated_goal_id=gid,
                explanation=f"Goal {gid} directly confirmed on level {level}",
            )
            self.active_goal.exemplar_ids.append(f"vic_{level}_{step_index}")
            self.record_victory(vic_ex)
            return GoalJudgementResult(verdict="HOLDS_DIRECT", goal_id=gid, goal_satisfied=True, level_completed=True, is_defeat=False, victory_exemplar=vic_ex)
        if satisfied and not level_completed:
            assert self.active_goal is not None
            self.active_goal.status, self.active_goal.n_violated = "VIOLATED", self.active_goal.n_violated + 1
            diff_desc = "No prior victory exemplar available for diff comparison."
            if self.victory_exemplars:
                last_v = self.victory_exemplars[-1]
                diff_desc = f"Diff vs last victory (L{last_v.level_index}): prior win target_color={last_v.target_color}, steps={last_v.total_steps}."
            return GoalJudgementResult(verdict="VIOLATED", goal_id=gid, goal_satisfied=True, level_completed=False, is_defeat=False, diagnostic=f"Goal {gid} prematurely satisfied without win. {diff_desc}")
        if not satisfied and level_completed:
            vic_ex = VictoryExemplar(
                level_index=level, total_steps=step_index, action_sequence=actions_hist, final_action=action,
                actor_pos_before=actor_before, actor_pos_after=actor_after, before_grid=before_grid, after_grid=after_grid,
                associated_goal_id=None, explanation=f"Level {level} completed without active goal explanation",
            )
            self.record_victory(vic_ex)
            return GoalJudgementResult(verdict="UNCOVERED_WIN", goal_id=gid, goal_satisfied=False, level_completed=True, is_defeat=False, victory_exemplar=vic_ex)
        return GoalJudgementResult(verdict="NA", goal_id=gid, goal_satisfied=False, level_completed=False, is_defeat=False)

    def check_candidate(
        self, kind: str, color: int | None = None, target: Any = None, criteria: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Check if candidate goal is consistent with exemplars (Rule 00 transparent analysis)."""
        reasons: list[str] = []
        contradicted, supported_count = False, 0
        if color is not None:
            for d in self.defeat_exemplars:
                if d.hazard_color == color:
                    contradicted = True
                    reasons.append(f"Contradicted by Defeat on L{d.level_index} Step {d.fatal_step}: Color {color} is lethal hazard.")
        for v in self.victory_exemplars:
            if color is not None and v.target_color == color:
                supported_count += 1
                reasons.append(f"Supported by Victory on L{v.level_index}: reached Color {color}.")
            elif target is not None and v.target_coords == target:
                supported_count += 1
                reasons.append(f"Supported by Victory on L{v.level_index}: reached coords {target}.")
        return {"valid": not contradicted, "contradicted_by_defeat": contradicted, "supported_by_victories": supported_count, "reasons": reasons}

    def format_card_section(self) -> str:
        """Format goals and exemplars for knowledge card."""
        sections: list[str] = []
        if self.active_goal:
            sections.append(f"[GOAL]: {self.active_goal.kind} (color={self.active_goal.color}, status={self.active_goal.status})")
        if self.victory_exemplars:
            sections.append(self.victory_exemplars[-1].format_for_prompt())
        if self.defeat_exemplars:
            sections.append(self.defeat_exemplars[-1].format_for_prompt())
        return "\n".join(sections)

    def reset(self) -> None:
        self.active_goal = None
        self.goals.clear()
        self.victory_exemplars.clear()
        self.defeat_exemplars.clear()
