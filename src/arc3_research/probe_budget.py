"""026 host-side probe budget: per-action pre-dispatch quota.

Contract (corrected 2026-10-20): a plain result dict with a stop_reason
does NOT stop model-written Python loops. The only terminating path is
the solver's guard-hook refusal (``action_guard_hook -> (stop_reason,
detail)``): the solver returns a refusal payload and the sandbox raises
an uncatchable BaseException-derived error that ends the snippet while
preserving prior stdout and retained functions
(``python_tool_sandbox.py`` refusal classes + error handler; solver
refusal payload ``solver.py:1136-1155``). So this guard is consulted
BEFORE each single env dispatch through that hook path, and quota stops
travel as hook refusals, never as normal results.
"""
from __future__ import annotations

from typing import Any


class ProbeBudget:
    """K env actions max. K=0 means pure recompute (no env action at all)."""

    def __init__(self, max_actions: int) -> None:
        if type(max_actions) is not int or max_actions < 0:
            raise ValueError("max_actions must be a non-negative int")
        self.max_actions = max_actions
        self.used = 0
        self.stopped: str | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.max_actions - self.used)

    def request(self) -> bool:
        """Call before dispatching one env action. False => do not dispatch."""
        if self.stopped is not None:
            return False
        if self.used >= self.max_actions:
            self.stopped = "probe_budget_reached"
            return False
        return True

    def report(self, result: dict[str, Any]) -> None:
        """Call after each dispatched action with its result payload."""
        self.used += 1
        if not isinstance(result, dict):
            return
        if result.get("level_completed") or result.get("run_complete"):
            self.stopped = "boundary_level_completed"
        elif result.get("game_over"):
            self.stopped = "boundary_game_over"
        elif result.get("done"):
            self.stopped = "boundary_done"
        elif self.used >= self.max_actions:
            self.stopped = "probe_budget_reached"

    def stop_payload(self, *, skipped: list[str],
                     level: int | None = None) -> dict[str, Any]:
        """Graceful normal result: same shape family as the solver's
        partial-batch payload (executed/stopped_early/stop_reason), plus the
        skipped action displays so the next turn can narrate precisely."""
        return {
            "executed": False,
            "level": level,
            "requested_count": self.used + len(skipped),
            "executed_count": 0,
            "stopped_early": True,
            "stop_reason": self.stopped or "probe_budget_reached",
            "skipped_actions": list(skipped),
            "probe_used": self.used,
            "probe_quota": self.max_actions,
        }


def run_probe_batch(plan: list[str], budget: ProbeBudget,
                    dispatch, *, level: int | None = None) -> dict[str, Any]:
    """Drive a short probe plan through single-action dispatches.

    dispatch(action) -> result-dict. Stops early on quota/boundary and
    returns {"executed_results": [...], "stop": stop_payload | None}.
    Never raises for quota/boundary stops.
    """
    executed: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(plan):
        if not budget.request():
            break
        result = dispatch(plan[cursor])
        cursor += 1
        executed.append(result)
        budget.report(result)
        if budget.stopped is not None and budget.stopped.startswith("boundary"):
            break
    skipped = plan[cursor:]
    stop = budget.stop_payload(skipped=skipped, level=level) if (
        skipped or budget.stopped is not None) else None
    return {"executed_results": executed, "stop": stop}
