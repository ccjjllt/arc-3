"""024: one automatic rule-or-goal probe after a level stays unfinished.

The host counts executed actions on the current level. Visible pixel changes
do not reset that count: the community failures kept moving, or changed only
state the frame does not draw. The 64th action on a level that has not been
completed appends one instruction to that tool result. The next three executed
actions are recorded and then the window closes. RESET and a lost life stay
on the same level, so they count and do not open the window again. Completing
the level clears the count. This does not add an action API or a standing prompt.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading

from .bounded_probe import GoalProbeBudget


STALL_ACTIONS = 64
PROBE_ACTIONS = 3
STALL_INSTRUCTION = (
    "stall_probe: this level has used 64 actions without completing. "
    "Before repeating that plan, use at most three real actions to distinguish "
    "a different rule from a different target. Say which outcome you saw, then "
    "continue with that one. This window does not open again on this level, "
    "including after RESET."
)


def executed_action_count(item: dict) -> int:
    """How many actions one host result actually ran.

    A tool call can carry a whole batch. Counting the batch as one step is
    what hid tt03's 421-action level inside 24 model turns.
    """
    names = item.get("executed_actions")
    if isinstance(names, list) and names:
        return len(names)
    count = item.get("executed_count")
    if type(count) is int and count > 0:
        return count
    return 1


class StallTracker:
    def __init__(self) -> None:
        self.budget = GoalProbeBudget()
        self.streak: dict[tuple[str, str], int] = {}
        self.triggered: set[tuple[str, str]] = set()
        self.following: dict[tuple[str, str], int] = {}
        self.log: list[dict] = []
        self._lock = threading.Lock()

    def observe(self, game_id: str, action_results: list[dict]) -> dict | None:
        opened: dict | None = None
        opened_now: set[tuple[str, str]] = set()
        with self._lock:
            for item in action_results:
                if not isinstance(item, dict) or not item.get("executed"):
                    continue
                level = item.get("level")
                if type(level) is not int:
                    continue
                key = (game_id, "level:" + str(level))
                count = executed_action_count(item)
                completed = bool(
                    item.get("level_completed") or item.get("run_complete") or item.get("done")
                )
                # Actions in the triggering call already ran before the model
                # can read the note, so they are not part of the probe window.
                if key in self.following and key not in opened_now:
                    self.following[key] -= count
                    self.log.append({
                        "game_id": game_id, "level_id": key[1], "following_action": True,
                        "actions": count, "level_completed": completed,
                        "actions_left_after_this": self.following[key],
                    })
                    if completed or self.following[key] <= 0:
                        self.budget.close(
                            game_id, key[1], "boundary" if completed else "one_window_completed")
                        self.following.pop(key, None)
                    if completed:
                        self.streak[key] = 0
                    continue
                if completed:
                    self.streak[key] = 0
                    continue
                self.streak[key] = self.streak.get(key, 0) + count
                if self.streak[key] < STALL_ACTIONS or key in self.triggered:
                    continue
                self.triggered.add(key)
                self.budget.open_window(
                    game_id=game_id, level_id=key[1], trigger="repeated_plan_no_progress",
                    evidence_refs=[f"same-level-actions:{self.streak[key]}"],
                    alternatives={
                        "rule": "the visible failure comes from the wrong rule",
                        "goal": "the visible failure comes from the wrong target",
                    },
                    max_probes=PROBE_ACTIONS,
                )
                self.following[key] = PROBE_ACTIONS
                opened_now.add(key)
                opened = {
                    "triggered": True, "game_id": game_id, "level_id": key[1],
                    "actions_on_level": self.streak[key], "max_probe_actions": PROBE_ACTIONS,
                    "instruction": STALL_INSTRUCTION,
                }
                self.log.append(opened)
            return opened

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "events": list(self.log), "triggered_levels": len(self.triggered),
                "open_windows": len(self.following), "stall_actions": STALL_ACTIONS,
                "count": "executed_actions_on_level",
            }


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
        note = self.tracker.observe(
            game_id_from_state_path(state_path),
            list(getattr(self._bucket, "actions", []) or []),
        )
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
        return {
            "name": "stall_probe", "enabled": self.active,
            "trigger": "same_level_without_completion",
            "stall_actions": STALL_ACTIONS, "standing_prompt": False,
            **self.tracker.snapshot(),
        }


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
