"""Small synthetic CPU demonstration; no model, game engine or recorded code runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arc3_research.checked_execution import ComparableState, Observation, execute_checked
from arc3_research.bounded_probe import GoalProbeBudget


def frame(x=0, i=0, level="1", episode="a", terminal=False, boundary=None, scope="player-x/v1", hud=0):
    return Observation({"x": x, "scope": scope, "hud": hud}, f"event-{i}", level, episode, terminal, boundary)


def extract(data):
    return ComparableState(data["scope"], {"x": data["x"]})


def pred(state, action):
    return ComparableState(state.scope, {"x": state.values["x"] + action.get("dx", 1)})


def case(name, successors, *, count=3, predictor=pred, extractor=extract, initial=None, actions=None):
    sent = []
    def step(action):
        sent.append(action)
        value = successors[len(sent) - 1]
        if isinstance(value, Exception):
            raise value
        return value
    result = execute_checked(actions or [{"action": "RIGHT"}] * count,
                             initial=initial or frame(), execute_one=step,
                             pred=predictor, extract=extractor)
    return {"name": name, "sent": sent, **result}


def main():
    records = [
        case("first_mismatch_stops_18_action_suffix", [frame(1, 1), frame(-1, 2)], count=18),
        case("terminal_precedes_changed_projection", [frame(999, 1, terminal=True, scope="new-animation")]),
        case("level_change_precedes_extraction", [frame(999, 1, level="2", scope="different-board")]),
        case("reset_episode_stops_without_undo", [frame(0, 1, episode="b")]),
        case("explicit_stopped_early_boundary", [frame(0, 1, boundary="stopped_early")]),
        case("hud_changes_outside_declared_projection", [frame(1, 1, hud=42), frame(2, 2, hud=9)], count=2),
        case("incomparable_projection_is_not_model_mismatch", [frame(1, 1, scope="ambiguous-player/v2")]),
        case("missing_prediction_does_not_execute", [], predictor=None),
        case("extractor_failure_does_not_execute", [], extractor=lambda _: None),
        case("uncertain_action_exception_never_retried", [RuntimeError("synthetic transport failure")]),
        case("mouse_payload_is_preserved", [frame(7, 1)], count=1,
             actions=[{"action": "MOUSE", "row": 12, "col": 34, "dx": 7}],
             predictor=lambda s, a: ComparableState(s.scope, {"x": 7 if (a["row"], a["col"]) == (12, 34) else -99})),
    ]
    expected = [("mismatch", 2), ("boundary", 1), ("boundary", 1), ("boundary", 1),
                ("boundary", 1), ("completed", 2), ("unverifiable", 1),
                ("unverifiable", 0), ("unverifiable", 0), ("execution_error", 1), ("completed", 1)]
    for record, (status, sent) in zip(records, expected):
        if record["status"] != status or len(record["sent"]) != sent:
            raise RuntimeError(f"Unexpected CPU demonstration outcome: {record['name']}")
    budget = GoalProbeBudget()
    budget.open_window(game_id="synthetic", level_id="1", trigger="predicted_goal_without_completion",
                       evidence_refs=["observed-goal-claim-but-no-level-completion"],
                       alternatives={"contact": "contact suffices", "activate": "contact then activate"}, max_probes=2)
    for i in (1, 2):
        budget.reserve("synthetic", "1", action={"action": "SPACE"},
                       predicted_outcomes={"contact": "no change", "activate": "observable activation"})
        budget.record("synthetic", "1", probe_index=i, observation_id=f"probe-{i}",
                      finding="synthetic observation; no causal validity claimed")
    denials = []
    for operation in (
        lambda: budget.reserve("synthetic", "1", action={"action": "SPACE"}, predicted_outcomes={}),
        lambda: budget.open_window(game_id="synthetic", level_id="1", trigger="model_reported_stall",
                                   evidence_refs=["reset-same-level"], alternatives={"a": "a", "b": "b"}),
    ):
        try:
            operation()
        except ValueError as exc:
            denials.append(str(exc))
    if len(denials) != 2:
        raise RuntimeError("probe budget/reset should both deny further admission")
    report = {"kind": "synthetic-CPU-demonstration-NOT-game-evaluation",
              "scope": "Local helper behavior only; no GPU/model/game/logged code, no adoption or score claim.",
              "checked_execution": records, "bounded_probe": budget.snapshot("synthetic", "1"),
              "budget_denials": denials,
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                                 ("src/arc3_research/checked_execution.py", "src/arc3_research/bounded_probe.py",
                                  "scripts/demos/demo_020_behavior_mechanisms.py")}}
    target = ROOT / "experiments/020-behavior-cpu/demo.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(target), "cases": len(records), "budget_denials": len(denials),
                      "mismatch_suffix_unattempted": records[0]["unattempted_suffix"]}, indent=2))


if __name__ == "__main__":
    main()
