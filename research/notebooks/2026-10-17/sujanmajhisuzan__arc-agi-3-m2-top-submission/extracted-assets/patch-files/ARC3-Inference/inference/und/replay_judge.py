"""Replay Judge for ARC-AGI-3 World Models and Trajectories (Contract 02, Section 2; Contract 04, Sections 1 & 5).

Evaluates model edges against recorded session trajectories in two distinct modes:
1. Teacher-Forced (TF): At each step t, the model starts from the true recorded state S_t
   and predicts S_{t+1}.
2. Free-Run (FR): The model rolls out purely in-memory from S_0 using predicted states
   to identify the point of trajectory divergence.

Uses ReplayVerdict:
  - FOLLOW  : Predicted state matches actual next state.
  - NULL    : Predicted state contradicts actual next state (counterexample to model).
  - ABSTAIN : Model returned Unknown / unmodelled transition (Contract 02, Section 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from inference.und.brusentsov_logic import ReplayVerdict
from inference.und.core_model import CoreModel, ObservedEdgesOverlay, SimState, StepTerminal


@dataclass(frozen=True)
class ReplayStepResult:
    """Evaluation result for an individual model transition edge."""
    step_index: int
    action: str
    predicted_state: SimState | StepTerminal | None
    actual_state: SimState | StepTerminal | None
    verdict: ReplayVerdict
    explanation: str
    is_overlay_edge: bool = False


@dataclass(frozen=True)
class ReplayReport:
    """Aggregated evaluation report for a trajectory replay."""
    mode: str  # "TEACHER_FORCED" | "FREE_RUN"
    total_steps: int
    follow_count: int
    null_count: int
    abstain_count: int
    steps: tuple[ReplayStepResult, ...]
    divergence_step: int | None = None
    accuracy: float = 0.0

    @property
    def is_perfect(self) -> bool:
        return self.null_count == 0 and self.abstain_count == 0 and self.total_steps > 0


class ReplayJudge:
    """Pure, deterministic Replay Judge for empirical model verification."""

    def __init__(
        self,
        core_model: CoreModel,
        observed_overlay: ObservedEdgesOverlay | None = None,
    ) -> None:
        self.core_model = core_model
        self.observed_overlay = observed_overlay

    def evaluate_step(
        self,
        step_index: int,
        current_state: SimState,
        action: str,
        actual_next_state: SimState | StepTerminal | None = None,
    ) -> ReplayStepResult:
        """Pure evaluation of a single transition edge against ground truth."""
        act = str(action).upper()
        overlay = self.observed_overlay or getattr(self.core_model, "overlay", None)
        is_overlay = False

        if overlay is not None and overlay.has_edge(current_state.grid_hash, act):
            is_overlay = True

        step_res = self.core_model.step(current_state, act)

        # Unpack CoreModel StepResult
        predicted: SimState | StepTerminal | None = None
        if hasattr(step_res, "state") and hasattr(step_res, "is_idle"):  # StepNext
            predicted = getattr(step_res, "state")
        elif isinstance(step_res, StepTerminal):  # StepTerminal
            predicted = step_res
        elif isinstance(step_res, SimState):  # SimState directly
            predicted = step_res
        elif step_res is None or hasattr(step_res, "action_id"):  # StepUnknown / None
            predicted = None

        # Contract 02, Section 4: If model returned Unknown, verdict is ABSTAIN
        if predicted is None:
            return ReplayStepResult(
                step_index=step_index,
                action=act,
                predicted_state=None,
                actual_state=actual_next_state,
                verdict=ReplayVerdict.ABSTAIN,
                explanation="Model returned Unknown; epistemic neutrality (ABSTAIN).",
                is_overlay_edge=is_overlay,
            )

        if actual_next_state is None:
            return ReplayStepResult(
                step_index=step_index,
                action=act,
                predicted_state=predicted,
                actual_state=None,
                verdict=ReplayVerdict.ABSTAIN,
                explanation="Ground truth unavailable for step; epistemic neutrality (ABSTAIN).",
                is_overlay_edge=is_overlay,
            )

        # Check equality between predicted and actual
        is_match = False
        if predicted == actual_next_state:
            is_match = True
        elif isinstance(predicted, SimState) and isinstance(actual_next_state, SimState):
            is_match = predicted.grid_hash == actual_next_state.grid_hash
        elif isinstance(predicted, StepTerminal) and isinstance(actual_next_state, StepTerminal):
            is_match = predicted.status == actual_next_state.status

        if is_match:
            return ReplayStepResult(
                step_index=step_index,
                action=act,
                predicted_state=predicted,
                actual_state=actual_next_state,
                verdict=ReplayVerdict.FOLLOW,
                explanation="Model prediction necessarily matched observed state (FOLLOW).",
                is_overlay_edge=is_overlay,
            )

        return ReplayStepResult(
            step_index=step_index,
            action=act,
            predicted_state=predicted,
            actual_state=actual_next_state,
            verdict=ReplayVerdict.NULL,
            explanation=(
                f"Model prediction contradicted actual observation: "
                f"predicted={predicted}, actual={actual_next_state} (NULL)."
            ),
            is_overlay_edge=is_overlay,
        )

    def replay_trajectory_teacher_forced(
        self,
        trajectory: Sequence[tuple[SimState, str, SimState | StepTerminal]],
    ) -> ReplayReport:
        """Replay trajectory in Teacher-Forced mode (Contract 02, Section 2).

        At each step t, the model starts from the true recorded state S_t.
        """
        results: list[ReplayStepResult] = []
        follow_count = 0
        null_count = 0
        abstain_count = 0
        first_null_step: int | None = None

        for idx, (curr_state, action, actual_next) in enumerate(trajectory):
            res = self.evaluate_step(
                step_index=idx,
                current_state=curr_state,
                action=action,
                actual_next_state=actual_next,
            )
            results.append(res)
            if res.verdict == ReplayVerdict.FOLLOW:
                follow_count += 1
            elif res.verdict == ReplayVerdict.NULL:
                null_count += 1
                if first_null_step is None:
                    first_null_step = idx
            elif res.verdict == ReplayVerdict.ABSTAIN:
                abstain_count += 1

        total = len(results)
        acc = (follow_count / total) if total > 0 else 0.0
        return ReplayReport(
            mode="TEACHER_FORCED",
            total_steps=total,
            follow_count=follow_count,
            null_count=null_count,
            abstain_count=abstain_count,
            steps=tuple(results),
            divergence_step=first_null_step,
            accuracy=acc,
        )

    def replay_trajectory_free_run(
        self,
        initial_state: SimState,
        actions: Sequence[str],
        ground_truth_states: Sequence[SimState | StepTerminal] | None = None,
    ) -> ReplayReport:
        """Replay trajectory in Free-Run mode (Contract 02, Section 2).

        The model rolls out purely in-memory from initial_state using simulated states.
        """
        results: list[ReplayStepResult] = []
        follow_count = 0
        null_count = 0
        abstain_count = 0
        first_null_step: int | None = None

        current: SimState | None = initial_state
        has_ground_truth = ground_truth_states is not None and len(ground_truth_states) >= len(actions)

        for idx, act in enumerate(actions):
            actual_next = ground_truth_states[idx] if (ground_truth_states is not None and has_ground_truth) else None
            if current is None:
                # Simulation halted due to previous terminal or Unknown state
                res = ReplayStepResult(
                    step_index=idx,
                    action=act,
                    predicted_state=None,
                    actual_state=actual_next,
                    verdict=ReplayVerdict.ABSTAIN,
                    explanation="Simulation halted: preceding step returned terminal or Unknown.",
                )
                results.append(res)
                abstain_count += 1
                continue

            res = self.evaluate_step(
                step_index=idx,
                current_state=current,
                action=act,
                actual_next_state=actual_next,
            )
            results.append(res)

            if res.verdict == ReplayVerdict.FOLLOW:
                follow_count += 1
            elif res.verdict == ReplayVerdict.NULL:
                null_count += 1
                if first_null_step is None:
                    first_null_step = idx
            elif res.verdict == ReplayVerdict.ABSTAIN:
                abstain_count += 1

            if isinstance(res.predicted_state, SimState):
                current = res.predicted_state
            else:
                # Terminal reached or Unknown
                current = None

        total = len(results)
        acc = (follow_count / total) if total > 0 else 0.0
        return ReplayReport(
            mode="FREE_RUN",
            total_steps=total,
            follow_count=follow_count,
            null_count=null_count,
            abstain_count=abstain_count,
            steps=tuple(results),
            divergence_step=first_null_step,
            accuracy=acc,
        )
