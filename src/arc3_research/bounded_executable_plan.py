"""036 compact, non-thinking program delivery on the existing 034 executor.

Only the additional program request changes. The actor's ordinary reasoning,
tools, scheduler, deadlines and 034 zero-action validation remain unchanged.
Retained helpers are evidence about the current code, not a certified planner.
Natural triggering is inherited from 034 and is not restricted to failures.
"""
from __future__ import annotations

import ast
import copy
from functools import partial
import hashlib
import json
import math
from typing import Any

from arc3_research.executable_plan import ExecutablePlanPatch
from arc3_research.executable_plan_contract import binding_names


DEFAULT_CONFIG = {
    "max_output_tokens": 4096,
    "max_prompt_chars": 32000,
    "max_prompt_bytes": 64000,
    "max_hypothesis_chars": 1600,
    "min_remaining_seconds": 180,
    "max_check_seconds": 5,
    "request_seconds": 60,
    "extra_seconds": 120,
    "enable_thinking": False,
    "preserve_thinking": False,
    "tool_choice": "required",
    "parallel_tool_calls": False,
}

PROMPT = """You are delivering a small executable revision of the paused game
program. Use the current public observation and the supplied complete code.
Retained helpers may be controllers or probes, not a complete planner; their
names and previous hypotheses do not prove their rules. Recompute the current
input, goal and short action plan from frame instead of copying stale targets.

Return exactly one python tool call, with only code as its argument. The code
must contain pure function definitions and permitted computational imports:
plan_program(frame) -> {"goal": nonempty description/data,
 "actions": [at most 12 model-facing action dicts],
 "evidence_pixels": [[row,col,color_character], ...],
 "replaces": [one or more supplied live binding names], "reason": str}
predict(frame, action) -> {"expected_pixels": [[row,col,color_character], ...],
 "scope": description of the action-relevant observable consequence}

The host computes both functions in a zero-action sandbox, checks current pixel
evidence, recomputes deterministically, and executes the plan through the real
action path. Predictions are frozen before each action and compared afterwards.
Cover the task object or interaction affected by that action, including expected
changed pixels when supported. An unchanged background pixel cannot substitute
for a prediction of the task-relevant consequence. A matching pixel projection
does not certify a goal or complete dynamics. If no defensible short plan can
be computed, raise ValueError from plan_program rather than inventing evidence.

Read frame.ascii, frame.shape, frame.level and frame.step. Coordinates are zero-
based row/column and colors are characters. MOUSE has row and col; other actions
have only action. Never propose RESET/UNDO. No function may call action(), an
effectful retained helper, or I/O. Allowed imports include math, collections,
itertools, heapq and numpy. No prints, top-level calls/assignments, decorators,
default arguments, annotations, global or nonlocal. Ordinary globals do not
persist: put dependencies inside the returned definitions and read live frame.
Deliver the definitions now; no prose or extended restatement of the game.
"""

PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "python",
        "description": "Deliver pure program definitions for host validation; this request executes no actions.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        },
    },
}


class RequestPreparationError(ValueError):
    def __init__(self, message, *, failure_stage="request_preparation", metadata=None):
        super().__init__(message)
        self.failure_stage = failure_stage
        self.metadata = metadata or {}


def _config(config=None):
    values = copy.deepcopy(DEFAULT_CONFIG)
    if config is not None:
        unknown = set(config) - set(values)
        if unknown:
            raise ValueError("Unknown 036 config keys: " + repr(sorted(unknown)))
        values.update(copy.deepcopy(config))
    for name in ("max_output_tokens", "max_prompt_chars", "max_prompt_bytes", "max_hypothesis_chars"):
        value = values[name]
        if type(value) is not int or value < (0 if name == "max_hypothesis_chars" else 1):
            raise ValueError(name + " must be a nonnegative/positive integer")
    for name in ("min_remaining_seconds", "max_check_seconds", "request_seconds", "extra_seconds"):
        value = values[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(name + " must be positive and finite")
    if (values["enable_thinking"] is not False or values["preserve_thinking"] is not False
            or values["parallel_tool_calls"] is not False or values["tool_choice"] != "required"):
        raise ValueError("036 requires request-local non-thinking and exactly one required Python tool call")
    return values


def _source_tree(source: str, label: str):
    if type(source) is not str:
        raise RequestPreparationError(label + " is not source text", failure_stage="source_unavailable")
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise RequestPreparationError(label + " is not complete parseable source",
                                      failure_stage="source_unparseable") from exc


def _references(tree):
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    # Reflection or indirect call lookup cannot be closed reliably by name.
    # Include every retained source in that case, or decline if it will not fit.
    indirect = any(isinstance(n, ast.Call) and (
        isinstance(n.func, ast.Subscript)
        or isinstance(n.func, ast.Name) and n.func.id in {"globals", "locals", "eval", "exec", "getattr"}
    ) for n in ast.walk(tree))
    return names, indirect


def _related_sources(source, previous_program, functions):
    if not source.strip() and not previous_program.strip():
        raise RequestPreparationError("No current program source was supplied", failure_stage="source_unavailable")
    roots = set()
    include_all = False
    for label, text in (("paused code", source), ("registered program", previous_program)):
        if text:
            names, indirect = _references(_source_tree(text, label))
            roots.update(names)
            include_all |= indirect
    selected = {}
    pending = set(functions) if include_all else roots.intersection(functions)
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in selected:
            continue
        text = functions[name]
        names, indirect = _references(_source_tree(text, "retained function " + name))
        selected[name] = text
        if indirect:
            include_all = True
        pending.update((set(functions) if include_all else names.intersection(functions)) - set(selected))
    return dict(sorted(selected.items())), include_all


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(p["text"] for p in value
                         if isinstance(p, dict) and isinstance(p.get("text"), str))
    return ""


def _hypothesis(messages, limit):
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        for field in ("reasoning_content", "reasoning", "content"):
            text = _text(message.get(field)).strip()
            if text:
                return {"unverified": True, "source": "most recent assistant " + field,
                        "excerpt_from_end": len(text) > limit,
                        "text": text[-limit:] if limit else ""}
    return {"unverified": True, "source": "unavailable", "excerpt_from_end": False, "text": ""}


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_bounded_request(agent, state, trigger, current, history_entries, functions, *, valid_actions, config=None):
    """Keep complete sources and the live frame, or reject before any request.

    Source selection is a conservative name-dependency closure, not a proof of
    relevance or purity. Only optional model prose may be shortened/removed.
    """
    cfg = _config(config)
    source = trigger.get("source_code", state.source_code)
    previous = trigger.get("previous_program") or ""
    if type(source) is not str or type(previous) is not str:
        raise RequestPreparationError("Current code must be source text", failure_stage="source_unavailable")
    sources, reflection = _related_sources(source, previous, functions)
    bindings = set(functions)
    if source.strip():
        bindings.update(binding_names(source))
    messages_so_far = state.latest_messages or agent._history_messages
    hypothesis = _hypothesis(messages_so_far, cfg["max_hypothesis_chars"])
    public_trigger = {k: trigger[k] for k in (
        "kind", "proposed_actions", "already_executed_in_snippet", "counterexample",
    ) if k in trigger}
    task = {
        "live_bindings": sorted(bindings),
        "paused_code": source,
        "related_retained_sources": sources,
        "registered_program": previous,
        "latest_model_hypothesis_unverified": hypothesis,
        "trigger": public_trigger,
        "current_public_observation": {
            "ascii": current.ascii, "shape": current.shape,
            "level": current.level, "step": current.step,
            # The adapter supplies the same normalized names used by plan
            # validation; forced forks may still store ACTION6/ACTION7 on actor.
            "valid_actions": [name for name in valid_actions if name not in {"RESET", "UNDO", "ACTION0", "ACTION7"}],
        },
        "recent_real_actions": [{"action": h.action, "step": h.frame.step,
                                 "level": h.frame.level, "result": h.result}
                                for h in history_entries[-2:]],
        "last_actual_result": agent._last_action_call_result,
    }
    metadata = {
        "mode": "036-compact-program-delivery", "whole_sources": True,
        "source_sha256": _digest(source), "previous_program_sha256": _digest(previous),
        "retained_source_sha256": {name: _digest(text) for name, text in sources.items()},
        "selected_retained_functions": list(sources),
        "omitted_retained_functions": sorted(set(functions) - set(sources)),
        "reflection_includes_all_sources": reflection,
        "program_context_kind": "retained_helpers" if sources else "paused_snippet_only",
        "program_semantics": "Supplied code may be a controller or probe; no complete planner is assumed.",
        "hypothesis_chars": len(hypothesis["text"]),
        "max_prompt_chars": cfg["max_prompt_chars"], "max_prompt_bytes": cfg["max_prompt_bytes"],
    }
    tools = [copy.deepcopy(PYTHON_TOOL)]

    def render():
        messages = [{"role": "system", "content": PROMPT},
                    {"role": "user", "content": json.dumps(task, ensure_ascii=False, separators=(",", ":"), allow_nan=False)}]
        encoded = json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
        return messages, encoded

    messages, encoded = render()
    if len(encoded) > cfg["max_prompt_chars"] or len(encoded.encode("utf-8")) > cfg["max_prompt_bytes"]:
        # Drop optional prose as a whole; never trim a function, counterexample
        # or board to make the request fit.
        task["latest_model_hypothesis_unverified"] = {
            "unverified": True, "source": "omitted_for_budget", "excerpt_from_end": False, "text": ""}
        metadata["hypothesis_chars"] = 0
        messages, encoded = render()
    metadata.update(prompt_chars=len(encoded), prompt_bytes=len(encoded.encode("utf-8")),
                    estimated_prompt_tokens=math.ceil(len(encoded) / 3),
                    token_estimate_method="characters / 3 heuristic, not tokenizer measurement",
                    prompt_sha256=_digest(encoded))
    if metadata["prompt_chars"] > cfg["max_prompt_chars"] or metadata["prompt_bytes"] > cfg["max_prompt_bytes"]:
        raise RequestPreparationError("Complete current sources and observation exceed the 036 prompt budget",
                                      failure_stage="context_too_large", metadata=metadata)
    return {"messages": messages, "tools": tools, "metadata": metadata}


def install_bounded_executable_plan(config=None, completion=None):
    cfg = _config(config)
    return ExecutablePlanPatch(
        min_remaining_seconds=cfg["min_remaining_seconds"], max_check_seconds=cfg["max_check_seconds"],
        request_seconds=cfg["request_seconds"], extra_seconds=cfg["extra_seconds"],
        completion=completion, request_builder=partial(build_bounded_request, config=cfg),
        completion_options={k: cfg[k] for k in (
            "enable_thinking", "preserve_thinking", "tool_choice", "parallel_tool_calls")},
        max_output_tokens=cfg["max_output_tokens"], patch_name="036-bounded-executable-plan-v1",
        request_config=cfg,
    )
