"""Standalone action-plan guard; not installed in the agent or sandbox.

The caller supplies an observation-only extractor and its existing predictor.
Only their explicit projection is compared: mismatch means the declared
prediction and extraction disagree, not that we know which is wrong. Callbacks
must be pure except execute_one, which must use the existing one-action API.
This is a cooperative control helper, not a security boundary or a hard CPU
timeout. It adds no model calls, actions, RESET, UNDO, or hidden-state access.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class Observation:
    """Public frame and public lifecycle metadata supplied by a future adapter.

    observation_id identifies an observation event, not a hash of its pixels;
    a NO-OP still produces a new event. level_id must remain stable on RESET.
    episode_id may change on RESET. boundary can name level_completed,
    stopped_early, reset, deadline, etc. Unknown lifecycle metadata must not be
    invented by an adapter merely to satisfy this interface.
    """
    data: Any
    observation_id: str
    level_id: str
    episode_id: str
    terminal: bool = False
    boundary: str | None = None


@dataclass(frozen=True)
class ComparableState:
    """Nonempty, JSON-valued fields under an explicit projection definition.

    scope names the extractor version, coordinates/units and selected fields.
    The helper neither guesses objects nor ignores borders/HUD automatically.
    Unselected animation/UI changes are outside this claim. An extractor must
    signal ambiguity by raising or returning no state, not guessed coordinates.
    """
    scope: str
    values: Mapping[str, Any]


def _json_copy(value: Any) -> Any:
    # Roundtrip freezes mutable prediction/action snapshots before execution.
    def check(item: Any) -> None:
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ValueError("JSON object keys must be strings")
            for v in item.values():
                check(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                check(v)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("state/action contains a non-JSON value")
    check(value)
    encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode()) > 65536:
        raise ValueError("state/action exceeds the 64 KiB diagnostic bound")
    return json.loads(encoded)


def _projection(state: Any) -> dict[str, Any]:
    if (not isinstance(state, ComparableState) or not isinstance(state.scope, str)
            or not state.scope.strip() or len(state.scope) > 512):
        raise ValueError("no explicit comparable projection")
    if not isinstance(state.values, Mapping) or not state.values:
        raise ValueError("empty or unavailable projection")
    values = _json_copy(dict(state.values))
    return {"scope": state.scope, "values": values}


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _preview(value: Any) -> Any:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value if len(encoded) <= 256 else {"preview": encoded[:256], "truncated": True,
                                           "sha256": _fingerprint(value)}


def _identity(obs: Observation) -> dict[str, Any]:
    if not isinstance(obs, Observation):
        raise ValueError("execute_one must return Observation")
    for name in ("observation_id", "level_id", "episode_id"):
        if not isinstance(getattr(obs, name), str) or not getattr(obs, name):
            raise ValueError(f"missing public {name}")
    if type(obs.terminal) is not bool or (obs.boundary is not None and not isinstance(obs.boundary, str)):
        raise ValueError("invalid lifecycle flags")
    return {name: getattr(obs, name) for name in
            ("observation_id", "level_id", "episode_id", "terminal", "boundary")}


def execute_checked(
    actions: Sequence[Mapping[str, Any]],
    *,
    initial: Observation,
    execute_one: Callable[[dict[str, Any]], Observation],
    pred: Callable[[ComparableState, dict[str, Any]], ComparableState],
    extract: Callable[[Any], ComparableState],
    max_actions: int = 32,
) -> dict[str, Any]:
    """Predict -> one real action -> lifecycle check -> compare, then repeat.

    All suffix actions remain unattempted after the first mismatch, unavailable
    evidence, callback error or boundary. Full action payloads, including MOUSE
    row/col, are passed unchanged in value to both pred and execute_one. There
    is no fallback to unchecked execution. A returned result must be surfaced
    to the model; invoking another batch is a separate explicit decision.
    """
    if type(max_actions) is not int or not 1 <= max_actions <= 256:
        raise ValueError("max_actions must be 1..256")
    if not isinstance(actions, (list, tuple)) or len(actions) > max_actions:
        raise ValueError("provide a bounded list/tuple of full action mappings")
    plan = []
    for action in actions:
        if not isinstance(action, Mapping) or not isinstance(action.get("action"), str) or not action["action"]:
            raise ValueError("each action needs its existing API action name")
        plan.append(_json_copy(dict(action)))
    _identity(initial)
    events: list[dict[str, Any]] = []
    attempted = observed = 0

    def finish(status: str, reason: str) -> dict[str, Any]:
        return {"status": status, "reason": reason, "planned_actions": len(plan),
                "attempted_actions": attempted, "observed_actions": observed,
                "unattempted_suffix": len(plan) - attempted, "events": events,
                "claim": "agreement/disagreement of declared observable projection only"}

    current = initial
    if current.terminal or current.boundary:
        return finish("boundary", current.boundary or "terminal")
    if not callable(pred) or not callable(extract):
        return finish("unverifiable", "predictor_and_extractor_required")
    for index, action in enumerate(plan):
        event: dict[str, Any] = {"index": index, "action": action, "before": _identity(current)}
        events.append(event)
        try:
            before = _projection(extract(current.data))
            # Give predictor a separate copy; it cannot mutate the recorded action.
            expected = _projection(pred(ComparableState(before["scope"], _json_copy(before["values"])),
                                        _json_copy(action)))
            if before["scope"] != expected["scope"] or before["values"].keys() != expected["values"].keys():
                raise ValueError("prediction changes declared projection schema")
            event.update(scope=expected["scope"], field_count=len(expected["values"]),
                         expected_sha256=_fingerprint(expected), prediction_sha256=_fingerprint(
                             {"before": event["before"], "action": action, "expected": expected}))
        except Exception as exc:
            event.update(comparison="not_executed", error=f"{type(exc).__name__}: {exc}")
            return finish("unverifiable", "pre_action_prediction_or_extraction_failed")
        attempted += 1
        try:
            after = execute_one(_json_copy(action))
            event["after"] = _identity(after)
        except Exception as exc:
            event.update(comparison="unavailable", error=f"{type(exc).__name__}: {exc}")
            # An exception may occur after the API accepted the action: no retry.
            return finish("execution_error", "action_outcome_unknown_no_retry")
        observed += 1
        # Normal level/game completion must never be reported as model mismatch.
        boundary = (after.boundary or ("terminal" if after.terminal else None)
                    or ("level_changed" if after.level_id != current.level_id else None)
                    or ("episode_changed" if after.episode_id != current.episode_id else None))
        if boundary:
            event["comparison"] = "skipped_boundary"
            return finish("boundary", boundary)
        if after.observation_id == current.observation_id:
            event["comparison"] = "unavailable"
            return finish("unverifiable", "observation_event_not_advanced")
        try:
            actual = _projection(extract(after.data))
            event["actual_sha256"] = _fingerprint(actual)
            if actual["scope"] != expected["scope"] or actual["values"].keys() != expected["values"].keys():
                event["comparison"] = "incomparable"
                return finish("unverifiable", "projection_schema_changed")
            diffs = [{"field": k, "expected": _preview(v), "actual": _preview(actual["values"][k])}
                     for k, v in expected["values"].items()
                     if json.dumps(v, sort_keys=True) != json.dumps(actual["values"][k], sort_keys=True)]
        except Exception as exc:
            event.update(comparison="unavailable", error=f"{type(exc).__name__}: {exc}")
            return finish("unverifiable", "post_action_extraction_failed")
        event.update(comparison="mismatch" if diffs else "match", diff_count=len(diffs), diffs=diffs[:8])
        if diffs:
            return finish("mismatch", "declared_prediction_differs_stop_and_inspect")
        current = after
    return finish("completed", "all_executed_actions_match_selected_projection")
