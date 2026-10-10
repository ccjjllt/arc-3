"""One-factor, opt-in goal-evidence prompt experiment for Franzen v3.

The model reports a candidate condition from its *observed* frame. The harness
only checks the frame reference and real completion feedback; it cannot verify
the model's interpretation of that condition. No actions or extra LLM calls are
introduced. Install after importing the patched baseline, before creating agents.
"""
from __future__ import annotations

from dataclasses import replace
from functools import wraps
import importlib
import json
from typing import Any


MARKER = "GOAL_EVIDENCE "
GUIDANCE = (
    "Goal evidence: matching predicted state transitions does not establish the "
    "victory condition. Only when your candidate winning condition is actually "
    "observed in the current real frame, report it once from Python with "
    "`import json; print('GOAL_EVIDENCE ' + json.dumps({'goal': 'brief condition', "
    "'observed': True, 'step': current_frame.step, 'level': current_frame.level}))`. "
    "Replace the condition with your hypothesis. Do not report simulated states "
    "or intermediate subgoals. This is an optional event report, not a per-turn "
    "summary; continue acting normally when there is no such observation."
)


class GoalEvidencePatch:
    """Runtime switch and small diagnostic ledger for sequential paired arms."""

    def __init__(self, tool_agent_class: type, enabled: bool) -> None:
        self.tool_agent_class = tool_agent_class
        self.enabled = bool(enabled)
        self.epoch = 0
        self.events: list[dict[str, Any]] = []
        self._original_prompt = tool_agent_class._build_user_prompt
        self._original_python = tool_agent_class._run_python_tool
        self._load_runtime_state = importlib.import_module(
            tool_agent_class.__module__
        ).load_runtime_state

    def set_enabled(self, enabled: bool) -> None:
        """Switch only between completed benchmark arms; use fresh sessions."""
        self.enabled = bool(enabled)
        self.epoch += 1

    def snapshot(self) -> dict[str, Any]:
        """Save beside benchmark outputs, without charging another model call."""
        events = [dict(event) for event in self.events]
        return {
            "intervention": "goal-evidence-v1",
            "enabled": self.enabled,
            "epoch": self.epoch,
            "events": events,
            "guidance_count": sum(e["kind"] == "guidance" for e in events),
            "marker_report_count": sum(e["kind"] == "marker_reported" for e in events),
            "frame_validated_count": sum(e["kind"] == "frame_matched" for e in events),
            "feedback_validated_count": sum(e["kind"] == "feedback_matched" for e in events),
            "nudge_count": sum(e["kind"] == "observed_claim_uncompleted" for e in events),
        }

    def _state(self, agent: Any) -> dict[str, Any]:
        session = str(getattr(agent, "_session_runtime_dir", ""))
        key = (self.epoch, session)
        state = getattr(agent, "_research_goal_evidence", None)
        if not state or state["key"] != key:
            state = {"key": key, "introduced": False, "seen": set()}
            agent._research_goal_evidence = state
        return state

    def _record(self, agent: Any, kind: str, **fields: Any) -> None:
        self.events.append({
            "epoch": self.epoch,
            "session": str(getattr(agent, "_session_runtime_dir", "")),
            "kind": kind,
            **fields,
        })

    def _after_python(self, agent: Any, state_path: Any, dispatch: Any) -> Any:
        try:
            payload = json.loads(dispatch.content)
        except (TypeError, ValueError):
            return dispatch
        stdout = payload.get("stdout", "") if isinstance(payload, dict) else ""
        if not isinstance(stdout, str) or MARKER not in stdout:
            return dispatch
        claims = []
        for line in stdout.splitlines():
            if not line.startswith(MARKER):
                continue
            try:
                claim = json.loads(line[len(MARKER):])
            except ValueError:
                self._record(agent, "invalid_marker")
                continue
            if isinstance(claim, dict):
                claims.append(claim)
                self._record(agent, "marker_reported")
        if not claims:
            return dispatch

        try:
            frame, _ = self._load_runtime_state(state_path)
        except (OSError, ValueError):
            self._record(agent, "runtime_unavailable")
            return dispatch
        actual = getattr(agent, "_last_action_call_result", None) or {}
        summary = getattr(agent, "_last_step_summary", None) or {}
        state = self._state(agent)
        for claim in claims:
            goal = " ".join(str(claim.get("goal", "")).split())[:240]
            step, level = claim.get("step"), claim.get("level")
            if (
                not goal or claim.get("observed") is not True or frame is None
                or type(step) is not int or type(level) is not int
                or step != frame.step or level != frame.level
            ):
                self._record(agent, "unmatched_frame_claim", goal=goal, step=step, level=level)
                continue
            self._record(agent, "frame_matched", goal=goal, step=step, level=level)
            # A referenced observation must have actual action feedback. A
            # simulation or a claim on the initial board cannot trigger a nudge.
            if not actual.get("executed") or actual.get("action_num") != step:
                self._record(agent, "no_matching_action_feedback", goal=goal, step=step, level=level)
                continue
            self._record(agent, "feedback_matched", goal=goal, step=step, level=level)
            if (
                actual.get("level_completed") or actual.get("run_complete")
                or actual.get("game_over") or summary.get("level_transition")
                or summary.get("run_complete") or summary.get("game_over")
                or payload.get("error")
            ):
                self._record(agent, "terminal_or_error_claim", goal=goal, step=step, level=level)
                continue
            key = (level, goal.casefold())
            if key in state["seen"]:
                continue
            state["seen"].add(key)
            self._record(agent, "observed_claim_uncompleted", goal=goal, step=step, level=level)
            payload["goal_evidence"] = (
                f"At real frame step {step}, level {level}, the environment did not "
                f"report level completion. You reported this candidate condition: {goal!r}. "
                "If your observation is correct, this condition alone is not yet a "
                "sufficient victory rule. Matching transition predictions does not "
                "validate a victory rule. Keep at most two candidate goals, each with "
                "one supporting or contradicting observation, and choose one short "
                "observation or probe that distinguishes them. No full summary is needed."
            )
            # Preserve the baseline dispatch flags, including made_progress.
            return replace(dispatch, content=json.dumps(payload, indent=2))
        return dispatch

    def install(self) -> None:
        patch = self

        @wraps(self._original_prompt)
        def build_user_prompt(agent: Any, *args: Any, **kwargs: Any) -> str:
            prompt = patch._original_prompt(agent, *args, **kwargs)
            if not patch.enabled:
                return prompt
            state = patch._state(agent)
            if state["introduced"]:
                return prompt
            state["introduced"] = True
            patch._record(agent, "guidance")
            return prompt + "\n" + GUIDANCE

        @wraps(self._original_python)
        def run_python_tool(agent: Any, state_path: Any, arguments: dict[str, Any]) -> Any:
            dispatch = patch._original_python(agent, state_path, arguments)
            if not patch.enabled:
                return dispatch
            return patch._after_python(agent, state_path, dispatch)

        self.tool_agent_class._build_user_prompt = build_user_prompt
        self.tool_agent_class._run_python_tool = run_python_tool


def install_goal_evidence(
    tool_agent_class: type | None = None, *, enabled: bool = True,
) -> GoalEvidencePatch:
    """Install once; repeated calls reuse the patch and start a fresh epoch.

    Example: ``patch = install_goal_evidence(enabled=False)`` for E0, then
    ``patch.set_enabled(True)`` before constructing E1's fresh benchmark.
    This switch does not reset the GPU model, serving settings, or scheduler.
    """
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    existing = getattr(tool_agent_class, "_research_goal_evidence_patch", None)
    if existing is not None:
        existing.set_enabled(enabled)
        return existing
    patch = GoalEvidencePatch(tool_agent_class, enabled)
    patch.install()
    tool_agent_class._research_goal_evidence_patch = patch
    return patch
