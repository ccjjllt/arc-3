"""Install the scoped-memory extension using checked, one-occurrence edits."""
from pathlib import Path
import ast
import sys


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected one patch anchor, found {text.count(before)}: {before[:110]!r}")
    return text.replace(before, after, 1)


def apply(harness_root):
    root = Path(harness_root)
    memory_source = Path(__file__).with_name("scoped_memory.py").read_text(encoding="utf-8")
    sandbox_path = root / "inference/agent/python_tool_sandbox.py"
    agent_path = root / "inference/agent/tool_agent.py"
    sandbox = sandbox_path.read_text(encoding="utf-8")
    agent = agent_path.read_text(encoding="utf-8")
    sandbox = replace_once(sandbox,
        "from inference.utils import retained_functions as _retained_functions\n",
        "from inference.utils import retained_functions as _retained_functions\nfrom inference.utils import scoped_memory as _scoped_memory\n")
    sandbox = replace_once(sandbox, "    __RETAINED_FUNCTIONS_SOURCE__\n",
        "    __RETAINED_FUNCTIONS_SOURCE__\n\n    __SCOPED_MEMORY_SOURCE__\n")
    sandbox = replace_once(sandbox, ').replace("__RETAINED_FUNCTIONS_SOURCE__\\n", inspect.getsource(_retained_functions)).replace(',
        ').replace("__SCOPED_MEMORY_SOURCE__\\n", inspect.getsource(_scoped_memory)).replace("__RETAINED_FUNCTIONS_SOURCE__\\n", inspect.getsource(_retained_functions)).replace(')
    sandbox = replace_once(sandbox, "        _animation_views = []\n", """        _animation_views = []
        _scratch_enabled = bool(initial.get("scoped_memory_enabled"))
        _initial_frame = initial.get("state", {}).get("current_frame", {})
        _scratch_data = restore_scoped_memory(
            initial.get("scoped_memory"), _initial_frame.get("level", 0), _initial_frame.get("step", 0))
        if _scratch_enabled:
            runtime_globals["scratch"] = {s: _scratch_data[s] for s in SCOPED_MEMORY_SCOPES}

        def _collect_memory_payload():
            if not _scratch_enabled:
                return {}
            frame = runtime_globals.get("current_frame")
            saved, notice = snapshot_scoped_memory(
                runtime_globals.get("scratch"), initial.get("scoped_memory"),
                frame.level, frame.step)
            return {"scoped_memory": saved, "memory_notice": notice}
""")
    sandbox = replace_once(sandbox, '            runtime_globals["current_frame"] = current_frame\n',
        '            if _scratch_enabled:\n                active = runtime_globals.get("scratch", {})\n                if type(active) is dict and all(type(active.get(s)) is dict for s in SCOPED_MEMORY_SCOPES):\n                    for scope in SCOPED_MEMORY_SCOPES:\n                        _scratch_data[scope] = active[scope]\n                    refresh_scoped_memory(_scratch_data, current_frame.level, current_frame.step)\n            runtime_globals["current_frame"] = current_frame\n')
    # Include data on both successful and handled-error returns (including action guards).
    anchor = '                    **_collect_retention_payload(),\n'
    if sandbox.count(anchor) != 2:
        raise ValueError("Expected successful and error return anchors")
    sandbox = sandbox.replace(anchor, anchor + '                    **_collect_memory_payload(),\n')
    sandbox = replace_once(sandbox, '    repair_hints: bool = False,\n) -> dict[str, Any]:',
        '    repair_hints: bool = False,\n    scoped_memory: dict[str, Any] | None = None,\n    scoped_memory_enabled: bool = False,\n) -> dict[str, Any]:')
    sandbox = replace_once(sandbox, '                "animation_enabled": animation_handler is not None,\n',
        '                "animation_enabled": animation_handler is not None,\n                "scoped_memory": scoped_memory,\n                "scoped_memory_enabled": scoped_memory_enabled,\n')
    sandbox = replace_once(sandbox, '                    "keepable_functions": list(message.get("keepable_functions") or []),\n',
        '                    "keepable_functions": list(message.get("keepable_functions") or []),\n                    **({"scoped_memory": message.get("scoped_memory"), "memory_notice": message.get("memory_notice", "")} if scoped_memory_enabled else {}),\n')
    agent = replace_once(agent, '            self._history_messages = []\n',
        '            self._scratch_memory = {}\n            self._history_messages = []\n')
    agent = replace_once(agent,
        '            repair_hints=_get_env_bool("ARC3_PERSISTENT_FUNCTIONS_REPAIR_HINTS", False),\n',
        '            repair_hints=_get_env_bool("ARC3_PERSISTENT_FUNCTIONS_REPAIR_HINTS", False),\n            scoped_memory=getattr(self, "_scratch_memory", {}),\n            scoped_memory_enabled=_get_env_bool("ARC3_SCOPED_MEMORY", False),\n')
    agent = replace_once(agent, '        payload: dict[str, Any] = {"tool": "python"}\n', """        payload: dict[str, Any] = {"tool": "python"}
        if _get_env_bool("ARC3_SCOPED_MEMORY", False):
            saved_memory = sandbox_result.get("scoped_memory")
            if isinstance(saved_memory, dict):
                self._scratch_memory = saved_memory
                memory_keys = {s: list(saved_memory.get(s, {}))[:12] for s in ("game", "level", "step")}
                if any(memory_keys.values()):
                    payload["scratch_saved_keys"] = memory_keys
            if sandbox_result.get("memory_notice"):
                payload["scratch_notice"] = sandbox_result["memory_notice"]
""")
    agent = replace_once(agent, '    if _level_transfer_guidance_enabled():\n        prompt = apply_level_transfer_system_guidance(prompt)\n    return prompt', """    if _level_transfer_guidance_enabled():
        prompt = apply_level_transfer_system_guidance(prompt)
    if _get_env_bool("ARC3_SCOPED_MEMORY", False):
        prompt += (
            "\\nPersistent Python data: `scratch` is available in every Python call. "
            "Use `scratch['game']` for compact mechanics/evidence reusable across levels, "
            "`scratch['level']` for this level's inferred rules, parsed layout, simulator parameters or search results, "
            "and `scratch['step']` for observations and coordinates tied to the current frame. "
            "Game data lasts until the game ends; level data is cleared when the level changes; "
            "step data is cleared immediately whenever an action changes the frame's step or level. "
            "Ordinary local variables still reset between calls. Store useful computed results explicitly in scratch, "
            "then reuse them instead of printing/rebuilding them. Saved data is your own hypothesis, not ground truth; "
            "revise it when new observations disagree, and read changing positions from the current frame. "
            "Keep the three scope dictionaries; store only JSON values (string keys, lists, strings, numbers, booleans, null), "
            "up to 128 KiB total. Do not store functions or frame objects there. "
            "Your retained functions may read scratch at call time.\\n"
        )
    return prompt""")
    ast.parse(memory_source)
    ast.parse(sandbox)
    ast.parse(agent)
    (root / "inference/utils/scoped_memory.py").write_text(memory_source, encoding="utf-8")
    sandbox_path.write_text(sandbox, encoding="utf-8")
    agent_path.write_text(agent, encoding="utf-8")
    print("Scoped-memory extension installed; default off unless ARC3_SCOPED_MEMORY=1")


if __name__ == "__main__":
    apply(sys.argv[1])
