"""021: optional prediction stop on the existing Python action entry.

Ordinary action(actions) stays the original one-batch call. A call that passes
pred, extract, and scope runs execute_checked, one existing action per step.
The child process has no repository imports, so the maintained helper source is
copied into the sandbox bootstrap. This does not add a tool, a model call, an
UNDO, or a second game channel.
"""
from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path


PREFIX_ENV = "ARC3_SYSTEM_PROMPT_PREFIX"
CHECKED_EXECUTION_PREFIX = (
    "When you already have a predictor and an extractor for the same visible "
    "fields, execute that plan with action(plan, pred=pred, extract=extract, "
    'scope="coordinates-and-fields"). extract(frame) and pred(values, action) '
    "must return the same nonempty JSON object. action is the full action dict: "
    'use action["action"], and for a click also action["row"] and action["col"]. '
    "Only the fields you return are compared. Do not compare the whole frame, and "
    "do not drop border cells unless your own extractor does. Each step sends one "
    "action through the existing action entry. Public level_completed, game_over, "
    "done, and run_complete stop the plan before comparison. The first field "
    "mismatch stops the remaining suffix and reports status, attempted_actions, "
    "unattempted_suffix, and diffs so the next code can repair the rule. If pred "
    "or extract fails, the plan stops and is not run unchecked. Ordinary "
    "action(actions) is unchanged. At most 32 actions per checked call."
)

_ACTION_DEF = "    def action(actions):\n"
_UNCHECKED_DEF = "    def _action_unchecked(actions):\n"
_ACTION_BIND = '    runtime_globals["action"] = action\n'
_WRAPPER = '''    def action(actions, *, pred=None, extract=None, scope=None):
        if pred is None and extract is None and scope is None:
            return _action_unchecked(actions)
        if not callable(pred) or not callable(extract):
            raise ValueError("checked action requires callable pred and extract; refusing unchecked fallback")
        if not isinstance(scope, str) or not scope.strip() or len(scope) > 512:
            raise ValueError("checked action requires an explicit scope for the compared fields")
        frame = runtime_globals.get("current_frame")
        if frame is None or type(getattr(frame, "level", None)) is not int:
            raise ValueError("checked action requires the live public current_frame level")
        event_i = [0]

        def _boundary(action_result):
            if not isinstance(action_result, dict):
                raise ValueError("missing public action result")
            # Same public flags, and the same priority, as the existing latch.
            # FrameView has no terminal fields; pixel equality is not a verdict.
            if action_result.get("run_complete") or action_result.get("done"):
                return "run_complete", True
            if action_result.get("level_completed"):
                return "level_completed", True
            if action_result.get("game_over"):
                return "game_over", True
            reason = action_result.get("stop_reason")
            if isinstance(reason, str) and reason:
                return reason, False
            return None, False

        def _observe(action_result):
            live = runtime_globals.get("current_frame")
            if live is None or type(getattr(live, "level", None)) is not int:
                raise ValueError("missing public level after action")
            boundary, terminal = _boundary(action_result)
            event_i[0] += 1
            # observation_id counts this call's action events, including a
            # no-op that still returned. episode_id stays a public constant:
            # the action result has no episode id, and RESET is game_over.
            return Observation(
                data=live,
                observation_id="public-action-event:" + str(event_i[0]),
                level_id="public-level:" + str(live.level),
                episode_id="public-session",
                terminal=terminal,
                boundary=boundary,
            )

        def _project(value):
            if isinstance(value, ComparableState):
                return value
            if not isinstance(value, dict) or not value:
                raise ValueError("pred/extract must return a nonempty object of declared fields")
            return ComparableState(scope, value)

        def _extract(data):
            return _project(extract(data))

        def _pred(state, one):
            return _project(pred(dict(state.values), one))

        def _one(payload):
            # Original signature is action(actions), including MOUSE row/col.
            outcome = _action_unchecked([payload])
            return _observe(outcome)

        initial = Observation(
            data=frame,
            observation_id="public-action-event:0",
            level_id="public-level:" + str(frame.level),
            episode_id="public-session",
            terminal=False,
            boundary=None,
        )
        summary = execute_checked(
            _normalize_actions(actions),
            initial=initial,
            execute_one=_one,
            pred=_pred,
            extract=_extract,
        )
        last = summary["events"][-1] if summary.get("events") else {}
        brief = {
            "status": summary.get("status"),
            "reason": summary.get("reason"),
            "planned_actions": summary.get("planned_actions"),
            "attempted_actions": summary.get("attempted_actions"),
            "observed_actions": summary.get("observed_actions"),
            "unattempted_suffix": summary.get("unattempted_suffix"),
            "comparison": last.get("comparison"),
            "diffs": last.get("diffs"),
            "error": last.get("error"),
        }
        print("checked_execution " + json.dumps(brief, sort_keys=True, ensure_ascii=False))
        return summary

'''


def _helper_source() -> str:
    return Path(__file__).with_name("checked_execution.py").read_text()


def build_checked_bootstrap(bootstrap: str) -> str:
    """Return a child script whose public action grows an optional checked path."""
    if (bootstrap.count(_ACTION_DEF) != 1 or bootstrap.count(_ACTION_BIND) != 1
            or "_action_unchecked" in bootstrap or "execute_checked" in bootstrap):
        raise RuntimeError("Unsupported or already patched action bootstrap")
    source = _helper_source()
    # dataclasses looks up the class module in sys.modules while the class
    # statement runs. A bare exec dict has no module entry, so register one.
    preamble = "\n".join([
        "import types as _checked_types",
        "import sys as _checked_sys",
        "_checked_mod = _checked_types.ModuleType('checked_execution')",
        "_checked_sys.modules['checked_execution'] = _checked_mod",
        "exec(" + repr(source) + ", _checked_mod.__dict__)",
        "execute_checked = _checked_mod.execute_checked",
        "ComparableState = _checked_mod.ComparableState",
        "Observation = _checked_mod.Observation",
        "",
    ])
    modified = preamble + bootstrap.replace(_ACTION_DEF, _UNCHECKED_DEF, 1)
    modified = modified.replace(_ACTION_BIND, _WRAPPER + _ACTION_BIND, 1)
    if (modified.count(_UNCHECKED_DEF) != 1 or modified.count(_ACTION_DEF) != 0
            or modified.count("def action(actions, *, pred=None, extract=None, scope=None):") != 1):
        raise RuntimeError("Checked action wrapper did not land on the existing entry")
    compile(modified, "<checked_execution_sandbox>", "exec")
    return modified


class CheckedExecutionPatch:
    def __init__(self, sandbox_module):
        self._module = sandbox_module
        self._before = sandbox_module._SANDBOX_BOOTSTRAP
        self._after = build_checked_bootstrap(self._before)
        self._previous_prefix = os.environ.get(PREFIX_ENV)
        self.active = False

    def snapshot(self):
        helper = _helper_source()
        return {
            "name": "checked_execution",
            "enabled": self.active,
            "mechanism": "optional_pred_extract_on_existing_action_entry",
            "ordinary_action_preserved": True,
            "one_action_per_checked_step": True,
            "sandbox_bootstrap_before_sha256": hashlib.sha256(self._before.encode()).hexdigest(),
            "sandbox_bootstrap_after_sha256": hashlib.sha256(self._after.encode()).hexdigest(),
            "checked_execution_sha256": hashlib.sha256(helper.encode()).hexdigest(),
            "prefix_sha256": hashlib.sha256(CHECKED_EXECUTION_PREFIX.encode()).hexdigest(),
            "adds_tools": False,
            "adds_framework_model_calls": False,
            "adds_framework_game_actions": False,
            "adds_undo_or_rollback": False,
            "unchecked_fallback": False,
            "projection": "caller scope and returned fields only; no full-frame compare and no border crop",
            "lifecycle": "public level_completed, game_over, done/run_complete, and stop_reason before compare",
            "episode_id": "stable public-session; game_over carries RESET because no public episode id is available",
            "runtime_adoption_counts": "not collected; inspect request code and tool results",
        }

    def uninstall(self):
        if not self.active:
            return
        if self._module._SANDBOX_BOOTSTRAP != self._after:
            raise RuntimeError("Checked-execution bootstrap changed while installed")
        if os.environ.get(PREFIX_ENV) != CHECKED_EXECUTION_PREFIX:
            raise RuntimeError("Checked-execution prefix changed while installed")
        self._module._SANDBOX_BOOTSTRAP = self._before
        if self._previous_prefix is None:
            os.environ.pop(PREFIX_ENV, None)
        else:
            os.environ[PREFIX_ENV] = self._previous_prefix
        delattr(self._module, "_research_checked_execution_patch")
        self.active = False


def install_checked_execution(sandbox_module=None):
    """Install in the candidate CPU process before constructing ToolAgent."""
    if os.environ.get(PREFIX_ENV, "").strip():
        raise RuntimeError("Checked execution requires an empty system prefix; refusing replacement or duplicate")
    if sandbox_module is None:
        sandbox_module = importlib.import_module("inference.agent.python_tool_sandbox")
    if hasattr(sandbox_module, "_research_checked_execution_patch"):
        raise RuntimeError("Checked execution is already installed")
    patch = CheckedExecutionPatch(sandbox_module)
    sandbox_module._SANDBOX_BOOTSTRAP = patch._after
    os.environ[PREFIX_ENV] = CHECKED_EXECUTION_PREFIX
    sandbox_module._research_checked_execution_patch = patch
    patch.active = True
    return patch
