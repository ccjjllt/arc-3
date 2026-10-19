"""023: one automatic rule-or-goal probe after a level stops making progress.

The host counts executed action batches that do not change play. The fourth
such batch on a level appends one instruction to that tool result. The next
three executed actions are recorded and then the window closes. RESET does
not open it again. This does not add an action API or a standing prompt.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading

from .bounded_probe import GoalProbeBudget


STALL_INSTRUCTION = (
    "stall_probe: this level has had four action batches with no visible "
    "progress. Before repeating that plan, use at most three real actions to "
    "distinguish a different rule from a different target. Say which outcome "
    "you saw, then continue with that one. This window does not open again "
    "on this level, including after RESET."
)
_NO_PROGRESS_BATCHES = 4
_PROBE_ACTIONS = 3


class StallTracker:
    def __init__(self) -> None:
        self.budget = GoalProbeBudget()
        self.streak: dict[tuple[str, str], int] = {}
        self.triggered: set[tuple[str, str]] = set()
        self.following: dict[tuple[str, str], int] = {}
        self.log: list[dict] = []
        self._lock = threading.Lock()

    def observe(self, game_id: str, action_results: list[dict]) -> dict | None:
        executed = [item for item in action_results if isinstance(item, dict) and item.get("executed")]
        if not executed:
            return None
        levels = [item.get("level") for item in executed]
        if any(type(level) is not int for level in levels) or len(set(levels)) != 1:
            return None
        level_id = "level:" + str(levels[0])
        key = (game_id, level_id)
        boundary = any(
            item.get("level_completed") or item.get("game_over")
            or item.get("run_complete") or item.get("done")
            for item in executed
        )
        progressed = boundary or any(item.get("gameplay_changed") for item in executed)
        with self._lock:
            if key in self.following:
                self.following[key] -= 1
                self.log.append({
                    "game_id": game_id, "level_id": level_id, "following_action": True,
                    "progressed": progressed, "boundary": boundary,
                    "actions_left_after_this": self.following[key],
                })
                if boundary or self.following[key] <= 0:
                    self.budget.close(game_id, level_id, "boundary" if boundary else "one_window_completed")
                    self.following.pop(key, None)
                return None
            if boundary:
                self._close_game(game_id, "boundary")
            if progressed:
                self.streak[key] = 0
                return None
            self.streak[key] = self.streak.get(key, 0) + 1
            if self.streak[key] < _NO_PROGRESS_BATCHES or key in self.triggered:
                return None
            self.triggered.add(key)
            self.budget.open_window(
                game_id=game_id, level_id=level_id, trigger="repeated_plan_no_progress",
                evidence_refs=[f"no-progress-batch:{i}" for i in range(1, _NO_PROGRESS_BATCHES + 1)],
                alternatives={
                    "rule": "the visible failure comes from the wrong rule",
                    "goal": "the visible failure comes from the wrong target",
                },
                max_probes=_PROBE_ACTIONS,
            )
            self.following[key] = _PROBE_ACTIONS
            note = {
                "triggered": True, "game_id": game_id, "level_id": level_id,
                "no_progress_batches": self.streak[key], "max_probe_actions": _PROBE_ACTIONS,
                "instruction": STALL_INSTRUCTION,
            }
            self.log.append(note)
            return note

    def _close_game(self, game_id: str, reason: str) -> None:
        for key in list(self.following):
            if key[0] == game_id:
                self.budget.close(key[0], key[1], reason)
                self.following.pop(key, None)

    def snapshot(self) -> dict:
        with self._lock:
            return {"events": list(self.log), "triggered_levels": len(self.triggered),
                    "open_windows": len(self.following)}


def game_id_from_state_path(state_path) -> str:
    path = Path(state_path)
    suffix = "_tool_runtime_state"
    if path.parent.name == "artifacts" and path.stem.endswith(suffix):
        return path.stem[: -len(suffix)] or path.stem
    return path.parent.name or path.stem


class StallProbePatch:
    def __init__(self, tool_agent_module, sandbox_module=None):
        self._tool_agent = tool_agent_module
        self._original_tool = tool_agent_module.ToolAgent._run_python_tool
        # The agent calls the name imported into its own module, not the sandbox module attribute.
        self._original_sandbox = tool_agent_module.run_sandboxed_python
        self.tracker = StallTracker()
        self._bucket = threading.local()
        self.active = False

    def _sandbox_wrapper(self, *args, **kwargs):
        handler = kwargs.get("action_handler")
        bucket: list[dict] = []
        self._bucket.actions = bucket
        if callable(handler):
            def _record(actions, stale_after=None):
                outcome = handler(actions, stale_after=stale_after)
                action_result = outcome.get("action_result") if isinstance(outcome, dict) else None
                if isinstance(action_result, dict):
                    bucket.append(action_result)
                return outcome
            kwargs["action_handler"] = _record
        return self._original_sandbox(*args, **kwargs)

    def _tool_wrapper(self, agent, state_path, arguments):
        self._bucket.actions = []
        result = self._original_tool(agent, state_path, arguments)
        note = self.tracker.observe(game_id_from_state_path(state_path), list(getattr(self._bucket, "actions", []) or []))
        if not note:
            return result
        try:
            payload = json.loads(result.content)
            if not isinstance(payload, dict):
                payload = {"result": payload}
        except json.JSONDecodeError:
            payload = {"stdout": result.content}
        payload["stall_probe"] = note
        return type(result)(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            step_executed=result.step_executed,
            made_progress=result.made_progress,
        )

    def install(self):
        if self.active:
            raise RuntimeError("Stall probe is already installed")
        # A bound method stored on the class is not bound again, so the
        # agent instance would be dropped and arguments would shift.
        def tool_entry(agent, state_path, arguments):
            return self._tool_wrapper(agent, state_path, arguments)
        self._tool_entry = tool_entry
        self._tool_agent.ToolAgent._run_python_tool = tool_entry
        self._tool_agent.run_sandboxed_python = self._sandbox_wrapper
        self.active = True
        return self

    def uninstall(self):
        if not self.active:
            return
        self._tool_agent.ToolAgent._run_python_tool = self._original_tool
        self._tool_agent.run_sandboxed_python = self._original_sandbox
        if getattr(self._tool_agent, "_research_stall_probe_patch", None) is self:
            delattr(self._tool_agent, "_research_stall_probe_patch")
        self.active = False

    def snapshot(self) -> dict:
        return {"name": "stall_probe", "enabled": self.active,
                "trigger": "four_executed_batches_without_visible_progress",
                "standing_prompt": False, **self.tracker.snapshot()}


def install_stall_probe(tool_agent_module=None, sandbox_module=None):
    import importlib
    if tool_agent_module is None:
        tool_agent_module = importlib.import_module("inference.agent.tool_agent")
    if sandbox_module is None:
        sandbox_module = importlib.import_module("inference.agent.python_tool_sandbox")
    if getattr(tool_agent_module, "_research_stall_probe_patch", None):
        raise RuntimeError("Stall probe is already installed")
    patch = StallProbePatch(tool_agent_module, sandbox_module).install()
    tool_agent_module._research_stall_probe_patch = patch
    return patch
