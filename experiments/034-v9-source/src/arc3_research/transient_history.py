"""Expose earlier executed actions' existing transient metadata, on demand.

Only the model-visible tool JSON changes. The original Python tool executes
normally; its refreshed public history supplies every real action, including
actions inside a batch. This module never executes actions or queries a model.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from functools import wraps
import importlib
import json
from pathlib import Path
import threading
from typing import Any


MAX_EVENTS = 4
MAX_ADDED_CHARS = 1600
FIELD = "earlier_action_transients"
NOTE = (
    "Historical metadata from earlier executed actions in this Python call, "
    "not a description of current_frame. last_animation_frames and "
    "last_animation_timeline remain the latest-action view; they do not "
    "retrieve these earlier events. bbox is [top,left,bottom,right], inclusive."
)


class TransientHistoryPatch:
    def __init__(self, tool_agent_class: type, enabled: bool) -> None:
        self.tool_agent_class = tool_agent_class
        self.enabled = bool(enabled)
        self._original = tool_agent_class._run_python_tool
        self._load = importlib.import_module(tool_agent_class.__module__).load_runtime_state
        self._lock = threading.Lock()
        self._calls: list[dict[str, Any]] = []

    def set_enabled(self, enabled: bool) -> None:
        """Switch between completed arms only; the research runner uses fresh processes."""
        self.enabled = bool(enabled)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            calls = [dict(call) for call in self._calls]
        reasons: Counter[str] = Counter()
        for call in calls:
            reasons.update(call.get("filtered_reasons", {}))
        fields = (
            "new_executed_actions", "captured_transient_events",
            "eligible_earlier_events", "attached_events", "omitted_events",
            "added_chars",
        )
        return {
            "intervention": "transient-history-v1",
            "enabled": self.enabled,
            "max_events_per_call": MAX_EVENTS,
            "max_added_chars_per_call": MAX_ADDED_CHARS,
            "calls_observed": len(calls),
            "calls_with_attachment": sum(bool(c.get("attached")) for c in calls),
            **{field: sum(c.get(field, 0) for c in calls) for field in fields},
            "filtered_reasons": dict(reasons),
            "calls": calls,
        }

    def _record(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._calls.append(record)

    def _augment(self, state_path: Any, before: Any, dispatch: Any,
                 record: dict[str, Any]) -> Any:
        after, history = self._load(state_path)
        if after is None or after.step < before.step:
            record["status"] = "missing_or_rewound_frame"
            return dispatch
        record.update(after_step=after.step, after_level=after.level)
        new = []
        seen: set[int] = set()
        previous_level = before.level
        for entry in history:
            frame = entry.frame
            result = entry.result or {}
            step = result.get("action_num")
            level_before = previous_level
            previous_level = frame.level
            if (
                result.get("executed") is not True or type(step) is not int
                or not before.step < step <= after.step or step in seen
            ):
                continue
            seen.add(step)
            # Frame/result references must identify the same actual transition.
            if step != frame.step or result.get("level") != frame.level:
                record["unmatched_history_entries"] = record.get("unmatched_history_entries", 0) + 1
                continue
            new.append((result, level_before, frame.level))
        record["new_executed_actions"] = len(new)
        if not new:
            record["status"] = "no_new_executed_actions"
            return dispatch

        # Conservatively discard observations before the latest terminal/reset
        # boundary in this call, even if the restarted level has the same number.
        boundary = -1
        last_player_action = -1
        for index, (result, level_before, level_after) in enumerate(new):
            automatic = bool(result.get("automatic"))
            is_reset = (result.get("action_name") == "RESET"
                        or result.get("action_display") == "RESET")
            if not automatic:
                last_player_action = index
            if (
                automatic or is_reset or level_before != level_after
                or any(result.get(key) for key in
                       ("level_completed", "game_over", "run_complete", "done"))
            ):
                boundary = index

        candidates = []
        captured = []
        reasons: Counter[str] = Counter()
        for index, (result, level_before, level_after) in enumerate(new):
            animation = result.get("animation") or {}
            if not isinstance(animation, dict):
                continue
            pixels = animation.get("transient_pixels")
            if type(pixels) is not int or pixels <= 0:
                continue
            step = result["action_num"]
            captured.append({"action_num": step, "level_before": level_before,
                             "level_after": level_after})
            if index <= boundary:
                reasons["at_or_before_terminal_reset_boundary"] += 1
                continue
            if level_before != level_after or level_after != after.level:
                reasons["different_level"] += 1
                continue
            if index == last_player_action:
                reasons["latest_action_already_has_baseline_channel"] += 1
                continue
            frames, bbox = animation.get("frames"), animation.get("transient_bbox")
            if (
                type(frames) is not int or frames < 2
                or not isinstance(bbox, (list, tuple)) or len(bbox) != 4
                or any(type(value) is not int for value in bbox)
                or not (0 <= bbox[0] <= bbox[2] and 0 <= bbox[1] <= bbox[3])
            ):
                reasons["incomplete_animation_metadata"] += 1
                continue
            candidates.append({
                "action_num": step,
                "level": level_after,
                "action": str(result.get("action_display") or result.get("action_name") or "")[:80],
                "frames": frames,
                "transient_pixels": pixels,
                "bbox": list(bbox),
            })
        record.update(captured_transient_events=len(captured), captured=captured,
                      eligible_earlier_events=len(candidates),
                      filtered_reasons=dict(reasons))
        if not candidates:
            record["status"] = "no_eligible_earlier_transients"
            return dispatch
        record["omitted_events"] = len(candidates)
        payload = json.loads(dispatch.content)
        if not isinstance(payload, dict) or FIELD in payload:
            record["status"] = "unavailable_output_field"
            return dispatch
        selected = candidates[:MAX_EVENTS]
        while True:
            extension = {"note": NOTE, "events": selected,
                         "omitted_events": len(candidates) - len(selected)}
            rendered = json.dumps({**payload, FIELD: extension}, indent=2)
            added_chars = len(rendered) - len(dispatch.content)
            if added_chars <= MAX_ADDED_CHARS:
                break
            if not selected:
                record["status"] = "attachment_exceeds_char_limit"
                record["omitted_events"] = len(candidates)
                return dispatch
            selected = selected[:-1]
        record.update(status="attached", attached=True, attached_events=len(selected),
                      omitted_events=len(candidates) - len(selected),
                      added_chars=added_chars,
                      attached_metadata=selected,
                      attached_action_nums=[event["action_num"] for event in selected])
        return replace(dispatch, content=rendered)

    def install(self) -> None:
        patch = self

        @wraps(self._original)
        def run_python_tool(agent: Any, state_path: Any, arguments: dict[str, Any]) -> Any:
            if not patch.enabled:
                # Baseline: no additional runtime reads and no prompt changes.
                return patch._original(agent, state_path, arguments)
            run_ref = Path(state_path).name.removesuffix("_tool_runtime_state.json")
            record = {"state_path": str(state_path), "run_ref": run_ref,
                      "dispatch_id": str(getattr(agent, "_diag_name", "")),
                      "attached": False}
            try:
                before, _ = patch._load(state_path)
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                before = None
                record["read_error"] = type(exc).__name__
            dispatch = patch._original(agent, state_path, arguments)
            if before is None:
                record["status"] = "missing_before_frame"
                patch._record(record)
                return dispatch
            record.update(before_step=before.step, before_level=before.level)
            try:
                output = patch._augment(state_path, before, dispatch, record)
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                record.update(status="observation_read_error", read_error=type(exc).__name__)
                output = dispatch
            patch._record(record)
            return output

        self.tool_agent_class._run_python_tool = run_python_tool


def install_transient_history(
    tool_agent_class: type | None = None, *, enabled: bool = True,
) -> TransientHistoryPatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    existing = getattr(tool_agent_class, "_research_transient_history_patch", None)
    if existing is not None:
        existing.set_enabled(enabled)
        return existing
    patch = TransientHistoryPatch(tool_agent_class, enabled)
    patch.install()
    tool_agent_class._research_transient_history_patch = patch
    return patch
