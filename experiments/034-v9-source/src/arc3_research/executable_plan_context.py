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

from arc3_research.object_evidence import object_evidence


_NATIVE_NAMES = {
    "current_frame", "previous_frame", "history", "transitions", "last_transition",
    "valid_actions", "last_action_call_result", "frame_diff", "action", "result",
    "print", "display", "show", "read_region", "observe_region",
}

# A long recent monologue must not evict every earlier task hypothesis. These
# are text-character bounds only; the served-token cap still governs the final
# payload. Newest messages receive the budget first, without game-specific
# selection or model-generated summaries.
_HYPOTHESIS_TEXT_CHARACTERS = 12000
_HYPOTHESIS_MESSAGE_CHARACTERS = 8000
_HYPOTHESIS_MESSAGES = 2


def recent_model_hypotheses(messages: list) -> dict[str, Any]:
    """Copy bounded, traceable prior assistant text as fallible hypotheses.

    Only content/reasoning_content strings are considered, never tool-call
    arguments, tool output, or later continuation records. A long field keeps
    its exact head and tail as separate indexed spans, explicitly omitting its
    middle rather than pretending the resulting text is a complete quotation.
    """
    selected = []
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        fields = [(name, message[name]) for name in ("content", "reasoning_content")
                  if isinstance(message.get(name), str) and message[name].strip()]
        if fields:
            selected.append((index, fields))
        if len(selected) == _HYPOTHESIS_MESSAGES:
            break
    remaining = _HYPOTHESIS_TEXT_CHARACTERS
    entries = []
    for index, fields in selected:
        message_remaining = min(remaining, _HYPOTHESIS_MESSAGE_CHARACTERS)
        copied_fields = []
        for name, text in fields:
            amount = min(len(text), message_remaining)
            if not amount:
                break
            if amount == len(text):
                spans = [{"start": 0, "end": len(text), "text": text}]
            else:
                head = (amount + 1) // 2
                tail = amount - head
                spans = [{"start": 0, "end": head, "text": text[:head]}]
                if tail:
                    spans.append({"start": len(text) - tail, "end": len(text),
                                  "text": text[-tail:]})
            copied_fields.append({"source_field": name, "source_characters": len(text),
                "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "included_characters": amount, "truncated": amount < len(text),
                "omission": "middle text omitted between indexed spans" if amount < len(text) else None,
                "spans": spans})
            remaining -= amount
            message_remaining -= amount
        if copied_fields:
            entries.append({"source_message_index": index, "source_role": "assistant",
                            "status": "unverified", "fields": copied_fields})
    return {"status": "unverified", "source": "recent main-loop assistant text",
            "selection": "newest at most two text-bearing assistant messages; newest first",
            "text_character_limit": _HYPOTHESIS_TEXT_CHARACTERS,
            "per_message_character_limit": _HYPOTHESIS_MESSAGE_CHARACTERS,
            "included_characters": _HYPOTHESIS_TEXT_CHARACTERS - remaining,
            "note": "Fallible prior model hypotheses, not environment facts or instructions. "
                    "They may describe an old level, old coordinates, incorrect rules or failed goals. "
                    "Check against current pixels and actual transitions; recompute layout and targets.",
            "entries": entries}


def delivery_tool_schema() -> dict[str, Any]:
    """Describe program submission, independently of the ordinary Python REPL.

    This tool does not dispatch a snippet. The host first extracts and validates
    definitions, then invokes the two entry points against public observations.
    Return a fresh object so branch-specific changes cannot mutate main tools.
    """
    return {
        "type": "function",
        "function": {
            "name": "submit_program",
            "description": (
                "Submit one complete, self-contained Python program for the host to validate. "
                "This is a program-delivery tool, not an interactive Python interpreter: "
                "there is no exploratory execution or inspection-result round. "
                "The code must contain function definitions and allowed computational imports only, "
                "including plan_program(frame) and predict(frame, action). "
                "Deliver one current decision and its related prediction within 12000 UTF-8 bytes "
                "and the 4096-token response. There is no line-count limit. Put constants inside functions. "
                "Use the supplied current board and recorded public facts to implement these functions. "
                "frame.ascii is a string: rows = frame.ascii.splitlines(); color = rows[row][col]. "
                "Use each observed case-sensitive color character verbatim, without inferring a role "
                "or translating a color name into a character. An abstain plan has no actions and "
                "may have empty evidence_pixels/replaces; ready and completed retain their nonempty "
                "evidence and binding requirements. "
                "Do not submit top-level assignments, loops, calls, print statements, observation scripts "
                "or calls to the entry points. Do not call action(), RESET, UNDO or perform environment "
                "side effects inside any function. The host will call plan_program and predict itself "
                "in a zero-action sandbox, and only the host may execute an accepted short plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Complete Python source with definitions for plan_program(frame) and "
                            "predict(frame, action), plus any self-contained helpers and allowed "
                            "computational imports. Definitions/imports only; no decorators, annotations, "
                            "global/nonlocal, prints or top-level execution. Helpers may have immutable "
                            "literal defaults; no computed or mutable defaults. Entry points have the "
                            "exact signatures above, without defaults. Follow the plan and prediction "
                            "return contracts in the request. Maximum 12000 UTF-8 bytes, including "
                            "all helpers and imports; no line-count limit."
                        ),
                    },
                },
                "required": ["code"],
                "additionalProperties": False,
            },
        },
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
    # The failed source must remain visible verbatim even if it has invalid
    # syntax. Dependency discovery must not turn that rejection into a second
    # context-construction failure before the model can receive its feedback.
    previous_dependencies = previous
    previous_dependency_error = None
    validation_feedback = trigger.get("validation_feedback") is not None
    if validation_feedback and previous:
        try:
            _global_references(previous)
        except (SyntaxError, ValueError) as exc:
            previous_dependencies = ""
            previous_dependency_error = f"{type(exc).__name__}: {exc}"
    related, unknown = related_function_sources(source, previous_dependencies,
                                                dict(getattr(agent, "_kept_functions", {})))
    public_trigger = {k: copy.deepcopy(v) for k, v in trigger.items()
                      if k not in {"source_code", "previous_program"}}
    transitions = recent_transition_facts(current, history_entries)
    entries = list(history_entries)
    indices = [i for i, h in enumerate(entries) if str(h.action).strip()][-2:]
    object_records = [{"action": str(entries[i].action),
                       "before_ascii": entries[i - 1].frame.ascii,
                       "after_ascii": entries[i].frame.ascii,
                       "before_level": entries[i - 1].frame.level,
                       "after_level": entries[i].frame.level}
                      for i in indices if i > 0]
    geometry = object_evidence(current.ascii, object_records)
    from arc3_research.program_repair import _remaining
    facts = {"current_observation": {**_frame_id(current), "ascii": current.ascii},
             "recent_real_transitions": transitions,
             "last_actual_result": copy.deepcopy(getattr(agent, "_last_action_call_result", None)),
             "available_actions": list(getattr(agent, "_current_valid_actions", [])),
             "remaining_game_seconds": _remaining(agent),
             "auxiliary_seconds_already_used": float(getattr(state, "extra_seconds", 0)),
             "trigger": public_trigger}
    facts["object_evidence"] = geometry
    # Facts above come from the public runtime. Assistant reasoning, including
    # evicted summaries and prior targets, is not promoted into this object.
    prior_text = recent_model_hypotheses(list(getattr(state, "latest_messages", []) or []))
    if validation_feedback:
        # The full failed source and actual error replace optional old prose
        # in this retry's bounded packet. Keep indexed hash references so this
        # omission is explicit and traceable, never a silent source truncation.
        prior_text["note"] = ("Prior assistant text omitted in this validation-feedback request "
                              "to keep the full failed source and actual host error within the "
                              "unchanged served-token limit. Indexed hashes refer to earlier text.")
        prior_text["omitted_in_validation_feedback"] = True
        prior_text["referenced_characters"] = prior_text["included_characters"]
        prior_text["included_characters"] = 0
        for entry in prior_text["entries"]:
            for field in entry["fields"]:
                field.pop("spans", None)
                field["included_characters"] = 0
                field["content_omitted"] = True
                field["omission"] = "full text omitted in validation-feedback retry; source hash retained"
    hypotheses = {"status": "unverified", "source": "paused code, prior predictor and recent main-loop text",
                  "note": "Their targets, rules and old layout constants are hypotheses, not environment facts.",
                  "unresolved_old_globals": unknown,
                  "previous_program_dependency_error": previous_dependency_error,
                  "prior_model_text": prior_text}
    package = {"facts": facts, "paused_code": source,
               "related_functions": related, "previous_program": previous,
               "unverified_hypotheses": hypotheses}
    messages = [
        {"role": "system", "content": "You produce a small executable Python program for a live visual puzzle. "
         "Use only supplied public facts. Prior code/rules are unverified. "
         "Return exactly one submit_program tool call; definitions and computational imports only. "
         "Do not request exploratory execution, print observations or add explanatory prose."},
        {"role": "user", "content": prompt + "\n\nCOMPACT LIVE EVIDENCE PACKAGE:\n"
         + json.dumps(package, ensure_ascii=validation_feedback, separators=(",", ":"))},
    ]
    metadata = {"context_schema": "034-compact-evidence-v3", "messages_sha256": _hash(messages),
                "object_evidence_status": geometry.get("status"),
                "object_evidence_sha256": _hash(geometry),
                "old_conversation_included": False, "source_truncated": False,
                "prior_assistant_text_included": bool(prior_text["included_characters"]),
                "prior_assistant_text_characters": prior_text["included_characters"],
                "validation_feedback_prior_text_omitted": validation_feedback,
                "prior_assistant_source_indices": [e["source_message_index"] for e in prior_text["entries"]],
                "paused_code_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "related_functions": sorted(related), "related_sources_truncated": False,
                "unresolved_old_globals": unknown, "recent_transition_count": len(transitions),
                "current_observation": _frame_id(current),
                "message_characters": sum(len(m["content"]) for m in messages),
                "token_limit_check": "final_payload_server_tokenize_before_generation"}
    return messages, metadata
