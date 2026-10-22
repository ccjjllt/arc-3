"""Compact, evidence-labelled input for the bounded executable-plan branch.

This module never decides game rules, targets or actions. It supplies complete
current pixels, the untruncated paused program and its retained dependencies,
plus exact recent public transitions. Token limits are enforced against the
final HTTP payload by ``program_repair._completion``, not a character estimate.
"""
from __future__ import annotations

import builtins
import copy
import hashlib
import json
import symtable
from typing import Any


_NATIVE_NAMES = {
    "current_frame", "previous_frame", "history", "transitions", "last_transition",
    "valid_actions", "last_action_call_result", "frame_diff", "action", "result",
    "print", "display", "show", "read_region", "observe_region",
}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    default=str).encode()).hexdigest()


def _frame_id(frame) -> dict[str, Any]:
    return {"level": frame.level, "step": frame.step,
            "shape": list(frame.shape), "grid_sha256": _hash(frame.grid)}


def recent_transition_facts(current, history_entries, *, limit=2) -> list[dict[str, Any]]:
    """Return exact public action/result transitions, without inferred state.

    Runtime ``HistoryEntry.frame`` is the AFTER frame, including history[-1].
    Deltas contain letter-coded before/after colors; together with the complete
    current board they preserve preceding same-shaped frames. A shape/level
    boundary carries the complete two frames instead of an invalid pixel delta.
    """
    del current  # The caller separately supplies the full live current frame.
    entries = list(history_entries)
    indices = [i for i, h in enumerate(entries) if str(h.action).strip()][-limit:]
    output = []
    for index in indices:
        entry = entries[index]
        fact = {"action": str(entry.action), "after": _frame_id(entry.frame),
                "result": copy.deepcopy(entry.result), "before_available": index > 0}
        if index > 0:
            before, after = entries[index - 1].frame, entry.frame
            fact["before"] = _frame_id(before)
            if before.shape == after.shape and before.level == after.level:
                a, b = before.ascii.splitlines(), after.ascii.splitlines()
                changes = [[r, c, old, new] for r, (ar, br) in enumerate(zip(a, b))
                           for c, (old, new) in enumerate(zip(ar, br)) if old != new]
                # Full frames are shorter for large changes and avoid dropping
                # evidence at level starts or large board transformations.
                if len(json.dumps(changes)) < len(before.ascii) + len(after.ascii):
                    fact["changed_pixels"] = changes
                else:
                    fact["before_ascii"], fact["after_ascii"] = before.ascii, after.ascii
            else:
                fact["before_ascii"], fact["after_ascii"] = before.ascii, after.ascii
        else:
            fact["after_ascii"] = entry.frame.ascii
        output.append(fact)
    return output


def _global_references(source: str) -> set[str]:
    """Names loaded from the global scope, excluding function-local bindings."""
    root = symtable.symtable(source, "<compact-plan-context>", "exec")
    names = {s.get_name() for s in root.get_symbols() if s.is_referenced()}
    pending = list(root.get_children())
    while pending:
        table = pending.pop()
        names.update(s.get_name() for s in table.get_symbols()
                     if s.is_referenced() and s.is_global())
        pending.extend(table.get_children())
    return names


def _bound_names(source: str) -> set[str]:
    # Function locals must not hide a different helper's missing global.
    root = symtable.symtable(source, "<compact-plan-bindings>", "exec")
    return {s.get_name() for s in root.get_symbols()
            if s.is_assigned() or s.is_imported() or s.is_namespace()}


def related_function_sources(source: str, previous_program: str,
                             kept_functions: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Follow references to retained functions, rejecting malformed sources.

    Unknown free names are returned explicitly. They can be old ephemeral data,
    which the new program must reconstruct, rather than silently usable globals.
    A retained function whose source is absent/malformed is a missing dependency
    and fails context construction before any model request or game action.
    """
    roots = [text for text in (source, previous_program) if text.strip()]
    references, defined = set(), set()
    for text in roots:
        references.update(_global_references(text))
        defined.update(_bound_names(text))
    related = {}
    todo = sorted(references & set(kept_functions))
    while todo:
        name = todo.pop(0)
        if name in related:
            continue
        text = kept_functions[name]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing retained dependency source: " + name)
        try:
            refs = _global_references(text)
            bindings = _bound_names(text)
        except (SyntaxError, ValueError) as exc:
            raise ValueError("Invalid retained dependency source: " + name) from exc
        if name not in bindings:
            raise ValueError("Retained dependency does not define its binding: " + name)
        related[name] = text
        references.update(refs)
        defined.update(bindings)
        todo.extend(sorted((refs & set(kept_functions)) - set(related)))
    unknown = sorted(references - defined - set(related) - set(dir(builtins)) - _NATIVE_NAMES)
    return related, unknown


def prepare_compact_context(agent, state, trigger, current, history_entries,
                            prompt: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Build a standalone branch request; never append the old conversation."""
    source = str(trigger.get("source_code", state.source_code) or "")
    previous = str(trigger.get("previous_program") or "")
    related, unknown = related_function_sources(source, previous,
                                                dict(getattr(agent, "_kept_functions", {})))
    public_trigger = {k: copy.deepcopy(v) for k, v in trigger.items()
                      if k not in {"source_code", "previous_program"}}
    transitions = recent_transition_facts(current, history_entries)
    from arc3_research.program_repair import _remaining
    facts = {"current_observation": {**_frame_id(current), "ascii": current.ascii},
             "recent_real_transitions": transitions,
             "last_actual_result": copy.deepcopy(getattr(agent, "_last_action_call_result", None)),
             "available_actions": list(getattr(agent, "_current_valid_actions", [])),
             "remaining_game_seconds": _remaining(agent),
             "auxiliary_seconds_already_used": float(getattr(state, "extra_seconds", 0)),
             "trigger": public_trigger}
    # Facts above come from the public runtime. Assistant reasoning, including
    # evicted summaries and prior targets, is not promoted into this object.
    hypotheses = {"status": "unverified", "source": "paused code and prior predictor",
                  "note": "Their targets, rules and old layout constants are hypotheses, not environment facts.",
                  "unresolved_old_globals": unknown}
    package = {"facts": facts, "paused_code": source,
               "related_functions": related, "previous_program": previous,
               "unverified_hypotheses": hypotheses}
    messages = [
        {"role": "system", "content": "You produce a small executable Python program for a live visual puzzle. "
         "Use only supplied public facts. Prior code/rules are unverified. "
         "Return exactly one python tool call; definitions and imports only, no explanatory prose."},
        {"role": "user", "content": prompt + "\n\nCOMPACT LIVE EVIDENCE PACKAGE:\n"
         + json.dumps(package, ensure_ascii=False, separators=(",", ":"))},
    ]
    metadata = {"context_schema": "034-compact-evidence-v1", "messages_sha256": _hash(messages),
                "old_conversation_included": False, "source_truncated": False,
                "paused_code_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "related_functions": sorted(related), "related_sources_truncated": False,
                "unresolved_old_globals": unknown, "recent_transition_count": len(transitions),
                "current_observation": _frame_id(current),
                "message_characters": sum(len(m["content"]) for m in messages),
                "token_limit_check": "final_payload_server_tokenize_before_generation"}
    return messages, metadata
