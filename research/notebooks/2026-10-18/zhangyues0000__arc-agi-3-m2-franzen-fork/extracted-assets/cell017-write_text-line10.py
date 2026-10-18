"""ARC3 R3: game-over ledger surfacing (failure-record visibility).

The harness already records death traces (`game_over_trace` in summaries,
`death_ledger` in sandbox globals) but the model only sees them turn-locally.
R3 accumulates every game_over of the current level on the agent object and
prepends a compact ledger to each user message, so the model stops re-trying
known-fatal actions after those turns leave the context.

Hook seams (same defensive pattern as R1/R2):
- summary seam: ToolAgent._summarize_step_sequence (source marker "game_over_trace")
- builder seam: the user-message builder (marker _retained_function_context + role:user)

Env gate: ARC3_R3_GAMEOVER_LEDGER=1 enables; unset = fully inert.
Evidence label: kernel_output only.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_ROLE_USER_RE = re.compile(r"[\"']role[\"']\s*:\s*[\"']user[\"']")

_STATUS: dict[str, Any] = {
    "enabled": os.environ.get("ARC3_R3_GAMEOVER_LEDGER", "").strip() in {"1", "true", "yes", "on"},
    "installed": False,
    "summary_method": None,
    "builder_method": None,
    "game_overs": 0,
    "pins": 0,
    "disabled_reason": None,
}

_MAX_LEDGER = 6
_STATS_PATH = Path("/kaggle/working/arc3_r3_stats.jsonl")


def _log(event: dict[str, Any]) -> None:
    try:
        with _STATS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.time(), **event}, sort_keys=True) + "\n")
    except Exception:
        pass


def _disable(reason: str) -> None:
    if _STATUS["disabled_reason"] is None:
        _STATUS["disabled_reason"] = reason
        _log({"event": "disable", "reason": reason})
        print("ARC3_R3_STATUS disabled: " + reason, flush=True)


def _find_agent_class():
    import importlib

    for mod_name in ("inference.agent.tool_agent", "inference.agent.solver"):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type) and hasattr(obj, "_summarize_step_sequence"):
                return mod_name, obj
    return None, None


def _find_builder_method(cls: type) -> str | None:
    import inspect

    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if getattr(member, "__qualname__", "").rsplit(".", 1)[0] != cls.__name__:
            continue
        try:
            src = inspect.getsource(member)
        except Exception:
            continue
        if "_retained_function_context" in src and _ROLE_USER_RE.search(src):
            return name
    return None


def _prepend_block(message: dict[str, Any], block: str) -> dict[str, Any]:
    content = message.get("content")
    if isinstance(content, str):
        return {**message, "content": block + "\n\n" + content}
    if isinstance(content, list) and content and isinstance(content[0], dict):
        first = dict(content[0])
        if first.get("type") == "text":
            first["text"] = block + "\n\n" + str(first.get("text", ""))
            return {**message, "content": [first] + list(content[1:])}
        return {**message, "content": [{"type": "text", "text": block}] + list(content)}
    return {**message, "content": block + "\n\n" + str(content)}


def install() -> dict[str, Any]:
    if not _STATUS["enabled"]:
        _STATUS["installed"] = True
        print("ARC3_R3_STATUS installed=off (ARC3_R3_GAMEOVER_LEDGER unset) — inert", flush=True)
        return dict(_STATUS)

    mod_name, cls = _find_agent_class()
    if cls is None:
        _disable("agent class with _summarize_step_sequence not found")
        return dict(_STATUS)
    builder_name = _find_builder_method(cls)
    if builder_name is None:
        _disable("builder seam not found")
        return dict(_STATUS)
    _STATUS["summary_method"] = "_summarize_step_sequence"
    _STATUS["builder_method"] = builder_name

    ledger: list[str] = []  # per current level; reset on level_transition

    original_summary = getattr(cls, "_summarize_step_sequence")

    def wrapped_summary(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_summary(self, *args, **kwargs)
        try:
            if _STATUS["disabled_reason"] is None and isinstance(result, dict):
                if result.get("level_transition"):
                    ledger.clear()
                    _log({"event": "ledger_reset"})
                elif result.get("game_over"):
                    trace = result.get("game_over_trace") or []
                    fatal = str(result.get("fatal_action") or "?")[:60]
                    line = f"fatal={fatal}; trace={'; '.join(str(t)[:60] for t in trace[-3:])}"
                    if line not in ledger:
                        ledger.append(line)
                        while len(ledger) > _MAX_LEDGER:
                            ledger.pop(0)
                        _STATUS["game_overs"] += 1
                        _log({"event": "game_over_recorded", "n": _STATUS["game_overs"]})
        except Exception as exc:
            _disable(f"summary wrapper error: {type(exc).__name__}: {exc}")
        return result

    original_builder = getattr(cls, builder_name)

    def wrapped_builder(self: Any, *args: Any, **kwargs: Any) -> Any:
        message = original_builder(self, *args, **kwargs)
        try:
            if _STATUS["disabled_reason"] is None and ledger:
                block = (
                    f"[Death ledger — this level has {len(ledger)} recorded game_over(s). "
                    "These exact action patterns ended the attempt; do not repeat them "
                    "without a changed plan.]"
                    "\n" + "\n".join(f"{i + 1}. {line}" for i, line in enumerate(ledger))
                )
                _STATUS["pins"] += 1
                if _STATUS["pins"] % 25 == 1:
                    _log({"event": "pin", "n_ledger": len(ledger)})
                return _prepend_block(message, block)
        except Exception as exc:
            _disable(f"builder wrapper error: {type(exc).__name__}: {exc}")
        return message

    setattr(cls, "_summarize_step_sequence", wrapped_summary)
    setattr(cls, builder_name, wrapped_builder)
    _STATUS["installed"] = True
    print(
        "ARC3_R3_STATUS installed=on class=" + f"{mod_name}.{cls.__name__}"
        + " builder=" + builder_name,
        flush=True,
    )
    _log({"event": "installed"})
    return dict(_STATUS)
