"""One explicit alternative-goal probe window per game/level, CPU-only ledger.

No policy, prompt injection, game action or model call is installed. The future
host owns one ledger for the game session (not for each sandbox invocation).
Resetting a level must reuse its level_id; budget is not refunded by RESET,
exceptions, tool retries, or a changed goal label. The module does not infer
that a game is stuck or that a model-proposed alternative is correct.
"""
from __future__ import annotations

from typing import Any, Mapping

from .checked_execution import _json_copy


class GoalProbeBudget:
    """Budget accounting only; every probe is ONE normal action API invocation.

    Movement needed to reach a proposed interaction also consumes the 1..3
    slots. A distant experiment is ineligible for this short window; it does
    not receive free setup actions. Only explicit public evidence is recorded.
    """

    def __init__(self) -> None:
        self._windows: dict[tuple[str, str], dict[str, Any]] = {}

    def open_window(self, *, game_id: str, level_id: str, trigger: str,
                    evidence_refs: list[str], alternatives: Mapping[str, str],
                    max_probes: int = 3) -> dict[str, Any]:
        if any(not isinstance(s, str) or not s.strip() for s in (game_id, level_id)):
            raise ValueError("stable public game_id and level_id required")
        key = (game_id, level_id)
        if key in self._windows:
            raise ValueError("this level already used its one probe window")
        if trigger not in {"predicted_goal_without_completion", "repeated_plan_no_progress", "model_reported_stall"}:
            raise ValueError("unsupported evidence-linked trigger")
        if not evidence_refs or any(not isinstance(s, str) or not s.strip() for s in evidence_refs):
            raise ValueError("at least one observed trace reference required")
        if not isinstance(alternatives, Mapping) or len(alternatives) != 2:
            raise ValueError("supply exactly two explicit competing hypotheses")
        if any(not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
               for k, v in alternatives.items()) or len(set(alternatives.values())) != len(alternatives):
            raise ValueError("alternative IDs and descriptions must be distinct and nonempty")
        if type(max_probes) is not int or not 1 <= max_probes <= 3:
            raise ValueError("max_probes must be 1..3")
        self._windows[key] = {"game_id": game_id, "level_id": level_id, "trigger": trigger,
                              "evidence_refs": list(evidence_refs), "alternatives": dict(alternatives),
                              "max_probes": max_probes, "records": [], "closed_reason": None}
        return self.snapshot(game_id, level_id)

    def reserve(self, game_id: str, level_id: str, *, action: Mapping[str, Any],
                predicted_outcomes: Mapping[str, str]) -> dict[str, Any]:
        """Spend one slot BEFORE a normal action attempt; never retry/refund here."""
        window = self._windows[(game_id, level_id)]
        if window["closed_reason"]:
            raise ValueError("probe window closed")
        records = window["records"]
        if records and records[-1]["observation_id"] is None:
            raise ValueError("inspect and record the preceding probe before another")
        if len(records) >= window["max_probes"]:
            raise ValueError("per-level probe budget exhausted")
        if not isinstance(action, Mapping) or not isinstance(action.get("action"), str) or not action["action"]:
            raise ValueError("one full existing-API action mapping required")
        if set(predicted_outcomes) != set(window["alternatives"]):
            raise ValueError("each alternative needs an observable predicted outcome")
        if any(not isinstance(v, str) or not v.strip() for v in predicted_outcomes.values()) or len(set(predicted_outcomes.values())) < 2:
            raise ValueError("probe must claim at least two distinguishable outcomes")
        record = {"probe_index": len(records) + 1, "action": _json_copy(dict(action)),
                  "predicted_outcomes": dict(predicted_outcomes), "observation_id": None,
                  "finding": None, "boundary": False}
        records.append(record)
        return _json_copy(record)

    def record(self, game_id: str, level_id: str, *, probe_index: int,
               observation_id: str, finding: str, boundary: bool = False) -> dict[str, Any]:
        """Record public outcome; a finding is attributed caller interpretation.

        If the action outcome is unknown, close the window via close() instead.
        A boundary always closes it; the next level needs its own evidence.
        """
        window = self._windows[(game_id, level_id)]
        if window["closed_reason"] or not window["records"]:
            raise ValueError("no open pending probe")
        record = window["records"][-1]
        if probe_index != record["probe_index"] or record["observation_id"] is not None:
            raise ValueError("only the unique pending probe may receive a result")
        if any(not isinstance(s, str) or not s.strip() for s in (observation_id, finding)) or type(boundary) is not bool:
            raise ValueError("explicit observation reference, finding and boundary flag required")
        if any(r["observation_id"] == observation_id for r in window["records"][:-1]):
            raise ValueError("a previous observation cannot stand in for this probe outcome")
        record.update(observation_id=observation_id, finding=finding, boundary=boundary)
        if boundary:
            window["closed_reason"] = "boundary"
        elif len(window["records"]) >= window["max_probes"]:
            window["closed_reason"] = "budget_exhausted"
        return self.snapshot(game_id, level_id)

    def close(self, game_id: str, level_id: str, reason: str) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("explicit close reason required")
        window = self._windows[(game_id, level_id)]
        if not window["closed_reason"]:
            window["closed_reason"] = reason
        return self.snapshot(game_id, level_id)

    def snapshot(self, game_id: str, level_id: str) -> dict[str, Any]:
        window = self._windows[(game_id, level_id)]
        return _json_copy({**window, "slots_spent": len(window["records"]),
                           "slots_left": window["max_probes"] - len(window["records"]),
                           "claim": "budget and caller-reported evidence only; no automatic hypothesis validation"})
