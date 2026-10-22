"""Keep the last retained-source set when a sandbox returns no new snapshot.

This opt-in repair changes only the missing-key case. Valid empty snapshots,
ordinary Python exceptions with snapshots, and normal scope resets remain the
baseline's responsibility. Neither live variables nor game actions roll back.
"""
from __future__ import annotations

from collections import Counter
from functools import wraps
import importlib
from pathlib import Path
import threading
from typing import Any


class ProgramStatePatch:
    def __init__(self, tool_agent_class: type, enabled: bool) -> None:
        self.tool_agent_class = tool_agent_class
        self.enabled = bool(enabled)
        module = importlib.import_module(tool_agent_class.__module__)
        self._persistence_enabled = module._persistent_functions
        self._scope = module._persistent_functions_scope
        self._original_record = tool_agent_class._record_retained_functions
        self._original_tool = tool_agent_class._run_python_tool
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()
        self._events: list[dict[str, Any]] = []

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "intervention": "program-state-v1",
                "enabled": self.enabled,
                "counts": dict(self._counts),
                "events": [dict(event) for event in self._events],
                "boundary": "Only absent keepable_functions preserves the previous set; present snapshots use baseline semantics.",
            }

    def install(self) -> None:
        patch = self

        @wraps(self._original_tool)
        def run_python_tool(agent: Any, state_path: Any, arguments: dict[str, Any]) -> Any:
            if not patch.enabled:
                return patch._original_tool(agent, state_path, arguments)
            previous_context = getattr(agent, "_research_program_state_context", None)
            agent._research_program_state_context = {
                "state_path": str(state_path),
                "run_ref": Path(state_path).name.removesuffix("_tool_runtime_state.json"),
                "dispatch_id": str(getattr(agent, "_diag_name", "")),
            }
            try:
                return patch._original_tool(agent, state_path, arguments)
            finally:
                agent._research_program_state_context = previous_context

        @wraps(self._original_record)
        def record_retained_functions(agent: Any, sandbox_result: Any, payload: dict) -> Any:
            if not patch.enabled or not patch._persistence_enabled():
                return patch._original_record(agent, sandbox_result, payload)
            if not isinstance(sandbox_result, dict) or "keepable_functions" in sandbox_result:
                with patch._lock:
                    patch._counts["snapshot_passthrough_calls"] += 1
                return patch._original_record(agent, sandbox_result, payload)

            # A killed/failed child provided no namespace snapshot. Do not
            # synthesize an empty set or restore state outside this commit point:
            # subsequent baseline level/session reset handling must still win.
            kept = getattr(agent, "_kept_functions", {})
            names = sorted(kept) if isinstance(kept, dict) else []
            action_results = sandbox_result.get("action_results") or []
            executed = [item for item in action_results
                        if isinstance(item, dict) and item.get("executed")]
            event = {
                **(getattr(agent, "_research_program_state_context", None) or {}),
                "scope": patch._scope(),
                "status": "missing_snapshot_preserved",
                "retained_function_count": len(names),
                "retained_function_names": names,
                "sandbox_error": str(sandbox_result.get("error") or "")[:500],
                "executed_action_calls": len(executed),
                "last_action_num": executed[-1].get("action_num") if executed else None,
                "last_level": executed[-1].get("level") if executed else None,
                "terminal_feedback_seen": any(
                    item.get("level_completed") or item.get("game_over") or item.get("run_complete")
                    for item in executed
                ),
            }
            with patch._lock:
                patch._counts["missing_snapshot_calls"] += 1
                patch._counts["calls_preserving_nonempty_set"] += bool(names)
                patch._counts["preserved_function_occurrences"] += len(names)
                patch._events.append(event)
            payload["function_retention"] = (
                "This call returned no function snapshot. The last committed function/import "
                f"set was kept ({len(names)} functions). Function definitions, changes and "
                "deletions from this failed call were not saved. Already executed game "
                "actions were not rolled back. Normal level/session reset rules still apply."
            )
            return None

        self.tool_agent_class._run_python_tool = run_python_tool
        self.tool_agent_class._record_retained_functions = record_retained_functions


def install_program_state(
    tool_agent_class: type | None = None, *, enabled: bool = True,
) -> ProgramStatePatch:
    if tool_agent_class is None:
        tool_agent_class = importlib.import_module("inference.agent.tool_agent").ToolAgent
    existing = getattr(tool_agent_class, "_research_program_state_patch", None)
    if existing is not None:
        existing.set_enabled(enabled)
        return existing
    patch = ProgramStatePatch(tool_agent_class, enabled)
    patch.install()
    tool_agent_class._research_program_state_patch = patch
    return patch
