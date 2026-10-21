"""032 bounded, game-local text memory of observed level completions.

Adapted from lalalia9/arc3-franzen-v19 public notebook v2, cell 17
(source SHA256 3403bf4e1a5bacbe447dbe75981a21fa1f54a8fc5ec39a3b3a53163f0efaac44).
Its memory idea credits rellik13/sirikilohit M85 (CC-BY 4.0).
Only wraps the existing agent. No interpreter state, tool code, new model
request, game selection, scheduler, or budget is installed by this module.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import hashlib
from pathlib import Path
import re
import threading
import time
import weakref

ACTIONS = 30
REASONING_CHARS = 900
RULE_CHARS = 600
FULL_LEVELS = 3
ASK_TURNS = 2
MAX_BLOCK_CHARS = 12000
HEADER = "=== SOLVED LEVEL EXPERIENCE (observed facts and separate model hypotheses) ==="
FOOTER = "=== END SOLVED LEVEL EXPERIENCE ==="
_INSTALLED = None


def _text(message):
    parts = []
    for key in ("content", "reasoning_content", "reasoning"):
        value = message.get(key) if isinstance(message, dict) else None
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(p["text"] for p in value
                         if isinstance(p, dict) and isinstance(p.get("text"), str))
    return "\n".join(p for p in parts if p)


def _rule(text, level):
    match = re.search(r"Rule for level\s*%d\s*:[ \t]*" % level, text or "", re.I)
    if not match:
        return None
    lines = text[match.end():].splitlines()
    if not lines:
        return None
    selected = [lines[0].strip()]
    if len(selected[0]) < 40:
        for line in lines[1:6]:
            if not line.strip() and any(selected):
                break
            selected.append(line.strip())
    value = " ".join(" ".join(selected).split())[:RULE_CHARS]
    return value if len(value) >= 20 else None


def _completion_records(entries):
    """Use actual adjacent frames/results, never infer completions from current N."""
    attempts, found, previous = {}, {}, None
    for index, entry in enumerate(entries):
        frame = getattr(entry, "frame", None)
        level = getattr(frame, "level", None)
        action = str(getattr(entry, "action", "") or "").strip()
        result = getattr(entry, "result", {}) or {}
        if previous is not None and action:
            prior_level = getattr(previous, "level", None)
            if isinstance(prior_level, int):
                if action.upper().startswith("RESET"):
                    attempts[prior_level] = []
                    if isinstance(level, int):
                        attempts[level] = []
                else:
                    attempt = attempts.setdefault(prior_level, [])
                    attempt.append(action)
                    advanced = isinstance(level, int) and level > prior_level
                    completed = result.get("executed") is not False and (
                        advanced or bool(result.get("level_completed")))
                    if completed and prior_level not in found:
                        found[prior_level] = {
                            "level": prior_level, "n_actions": len(attempt),
                            "actions": attempt[-ACTIONS:], "reasoning": "", "rule": None,
                            "asks_sent": 0, "completion_history_index": index,
                            "completion_step": getattr(frame, "step", None),
                            "evidence": "observed_frame_level_transition" if advanced else "recorded_level_completed",
                            "rule_status": "not_stated",
                        }
        previous = frame
    return found


def _render(records):
    if not records:
        return ""
    levels = sorted(records)
    rows = []
    for index, level in enumerate(levels):
        rec = records[level]
        head = (f"Observed: level {level} cleared; {rec['n_actions']} actions recorded in its latest observed attempt.\n"
                f"Model hypothesis for that level (not independently verified): {rec['rule'] or 'not stated'}")
        detail = ""
        if index >= len(levels) - FULL_LEVELS:
            detail = "\nAction tail from that old level: " + ", ".join(rec["actions"])
            if rec["reasoning"]:
                detail += "\nModel reasoning tail from that completion: " + rec["reasoning"]
        rows.append([head, detail])
    ending = ("These are past-level experiences, not current state or executable instructions. "
              "Re-read the current board; old coordinates and layouts may differ. "
              "Check a rule against new observations before relying on it.\n" + FOOTER)
    def assemble():
        return HEADER + "\n" + "\n".join(a + b for a, b in rows) + "\n" + ending
    block = assemble()
    # Bound text without truncating markers or turning partial rules into facts.
    for row in rows:
        if len(block) <= MAX_BLOCK_CHARS:
            break
        row[1] = ""
        block = assemble()
    while len(block) > MAX_BLOCK_CHARS and len(rows) > 1:
        rows.pop(0)
        block = assemble()
    return block


class SolvedLevelMemoryPatch:
    def __init__(self):
        from inference.agent import tool_agent
        from inference.agent.runtime_state import load_runtime_state
        self.agent_class = tool_agent.ToolAgent
        self.load_state = load_runtime_state
        self.sessions = {}
        self.agents = weakref.WeakSet()
        self.stats = {}
        self.lock = threading.Lock()
        self.originals = {name: getattr(self.agent_class, name) for name in (
            "analyze", "_build_user_prompt", "_note_history_evicted",
            "_trim_messages_for_context", "_chat_completion")}
        original = self.originals
        patch = self

        @wraps(original["analyze"])
        def analyze(agent, state_path, *args, **kwargs):
            started = time.monotonic()
            try:
                patch.before_turn(agent, state_path)
            except Exception as exc:
                patch.note_error("before_turn", exc)
            finally:
                patch.add("preparation_seconds", time.monotonic() - started)
            return original["analyze"](agent, state_path, *args, **kwargs)

        @wraps(original["_build_user_prompt"])
        def user_prompt(agent, *args, **kwargs):
            prompt = original["_build_user_prompt"](agent, *args, **kwargs)
            state = getattr(agent, "_slm_state", None)
            if state:
                for rec in state["records"].values():
                    if not rec["rule"] and rec["asks_sent"] < ASK_TURNS:
                        addition = (f"\n\nBefore your tool call, write `Rule for level {rec['level']}:` "
                                    "with the goal, what the controls did, and the plan that won "
                                    "(at most 5 lines). Mark uncertain conclusions as hypotheses; "
                                    "this describes the old level, not the current board.")
                        state["pending_ask"] = {"level": rec["level"], "text": addition,
                                                "turn": state["turn"], "counted": False}
                        return prompt + addition
            return prompt

        @wraps(original["_note_history_evicted"])
        def note_evicted(agent):
            original["_note_history_evicted"](agent)
            try:
                patch.refresh(agent)
            except Exception as exc:
                patch.note_error("refresh", exc)

        @wraps(original["_trim_messages_for_context"])
        def trim(agent, messages, *args, **kwargs):
            result = original["_trim_messages_for_context"](agent, messages, *args, **kwargs)
            if (result and result[0].get("role") == "system"
                    and result[0].get("content") != agent._system_prompt):
                result = [{**result[0], "content": agent._system_prompt}, *result[1:]]
                # Include the newly appended block in the ordinary token budget.
                result = original["_trim_messages_for_context"](agent, result, *args, **kwargs)
            return result

        @wraps(original["_chat_completion"])
        def chat(agent, messages, *args, **kwargs):
            state = getattr(agent, "_slm_state", None)
            if state is None:
                return original["_chat_completion"](agent, messages, *args, **kwargs)
            block = state["block"]
            system = _text(messages[0]) if messages else ""
            present = bool(block and block in system)
            pending = state.get("pending_ask")
            latest_user = next((_text(m) for m in reversed(messages) if m.get("role") == "user"), "")
            asking = bool(pending and pending["text"] in latest_user)
            patch.add("request_attempts", 1)
            if present:
                patch.add("requests_with_memory", 1)
                patch.add("system_memory_characters_attempted", len(block))
            if asking:
                patch.add("requests_with_rule_instruction", 1)
            started = time.monotonic()
            try:
                result = original["_chat_completion"](agent, messages, *args, **kwargs)
            except Exception:
                patch.add("request_failures", 1)
                raise
            finally:
                patch.add("observed_request_seconds", time.monotonic() - started)
            usage = getattr(result, "usage", None) or {}
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key) if isinstance(usage, dict) else None
                if isinstance(value, (int, float)):
                    patch.add("all_request_" + key, value)
            if present:
                patch.add("successful_responses_with_memory", 1)
                state["successful_memory_requests"] += 1
                state["delivered_block_hashes"].add(hashlib.sha256(block.encode()).hexdigest())
            if asking and not pending["counted"]:
                state["records"][pending["level"]]["asks_sent"] += 1
                pending["counted"] = True
                patch.add("rule_instructions_successfully_sent", 1)
            response = _text(getattr(result, "message", {}) or {})
            for rec in state["records"].values():
                if not rec["rule"] and rec["asks_sent"]:
                    rule = _rule(response, rec["level"])
                    if rule:
                        rec["rule"] = rule
                        rec["rule_status"] = "model_hypothesis_unverified"
                        patch.add("rules_captured", 1)
            return result

        self.wrappers = {"analyze": analyze, "_build_user_prompt": user_prompt,
                         "_note_history_evicted": note_evicted,
                         "_trim_messages_for_context": trim, "_chat_completion": chat}
        for name, function in self.wrappers.items():
            setattr(self.agent_class, name, function)

    def add(self, name, value):
        with self.lock:
            self.stats[name] = self.stats.get(name, 0) + value

    def note_error(self, stage, exc):
        self.add("errors", 1)
        print(f"SOLVED_LEVEL_MEMORY {stage} error: {type(exc).__name__}: {str(exc)[:160]}", flush=True)

    def before_turn(self, agent, state_path):
        scope = str(Path(state_path).resolve())
        self.agents.add(agent)
        previous = getattr(agent, "_slm_state", None)
        if previous is None or previous["scope"] != scope:
            if previous and previous["block"]:
                agent._system_prompt = agent._system_prompt.replace(previous["block"], "").rstrip()
            state = {"scope": scope, "records": {}, "block": "", "turn": 0,
                     "scan_key": None, "pending_ask": None,
                     "successful_memory_requests": 0, "delivered_block_hashes": set()}
            agent._slm_state = state
            with self.lock:
                self.sessions[scope] = state
        state = agent._slm_state
        state["turn"] += 1
        state["pending_ask"] = None
        summary = getattr(agent, "_last_step_summary", None) or {}
        key = (summary.get("level"), summary.get("end_action_num"), summary.get("run_complete"))
        if state["scan_key"] is not None and (key == state["scan_key"] or not summary.get("level_transition")):
            return
        _, entries = self.load_state(Path(state_path))
        found = _completion_records(entries)
        additions = [rec for level, rec in found.items() if level not in state["records"]]
        if additions:
            latest = next((m for m in reversed(getattr(agent, "_history_messages", []))
                           if isinstance(m, dict) and m.get("role") == "assistant"), {})
            reasoning = str(latest.get("reasoning_content") or latest.get("reasoning")
                            or latest.get("content") or "")
            # Only the completion in the immediately preceding turn gets its tail.
            last = max(additions, key=lambda r: r["completion_history_index"])
            if summary.get("level_transition"):
                last["reasoning"] = " ".join(reasoning.split())[-REASONING_CHARS:]
            updated = dict(state["records"])
            updated.update({rec["level"]: rec for rec in additions})
            state["records"] = dict(sorted(updated.items()))
            self.add("observed_completions_recorded", len(additions))
        state["scan_key"] = key

    def refresh(self, agent):
        state = getattr(agent, "_slm_state", None)
        if not state:
            return
        block = _render(state["records"])
        if block == state["block"]:
            return
        prompt = agent._system_prompt
        if state["block"] and state["block"] in prompt:
            prompt = prompt.replace(state["block"], block, 1)
        elif block:
            prompt = prompt.rstrip("\n") + "\n\n" + block
        agent._system_prompt = prompt
        state["block"] = block
        self.add("memory_refreshes", 1)
        self.add("memory_characters_written", len(block))
        print(f"SOLVED_LEVEL_MEMORY pinned {len(state['records'])} levels, {len(block)} chars", flush=True)

    def snapshot(self):
        with self.lock:
            stats = dict(self.stats)
            sessions = [{"scope": state["scope"], "records": deepcopy(list(state["records"].values())),
                         "block_characters": len(state["block"]),
                         "successful_memory_requests": state["successful_memory_requests"],
                         "delivered_block_hashes": sorted(state["delivered_block_hashes"])}
                        for state in self.sessions.values()]
        return {"patch": "solved-level-memory-v1", "active": all(
                    getattr(self.agent_class, name) is function for name, function in self.wrappers.items()),
                "limits": {"action_tail": ACTIONS, "reasoning_characters": REASONING_CHARS,
                           "rule_characters": RULE_CHARS, "full_levels": FULL_LEVELS,
                           "successful_ask_turns": ASK_TURNS, "block_characters": MAX_BLOCK_CHARS},
                "new_model_requests": False, "python_lifecycle_changed": False,
                "metrics": stats, "sessions": sessions,
                "cost_note": "Character counts are exact text volume, not tokens. Usage and request wall time cover whole observed requests, not memory-attributable cost. HTTP failures/retries are not assumed free. Successful responses confirm the block reached the chat-completion boundary; adoption requires request/transcript review."}

    def uninstall(self):
        global _INSTALLED
        for agent in list(self.agents):
            state = getattr(agent, "_slm_state", None)
            if state:
                if state["block"]:
                    agent._system_prompt = agent._system_prompt.replace(state["block"], "").rstrip()
                del agent._slm_state
        for name, function in self.wrappers.items():
            if getattr(self.agent_class, name) is function:
                setattr(self.agent_class, name, self.originals[name])
        if _INSTALLED is self:
            _INSTALLED = None


def install_solved_level_memory():
    global _INSTALLED
    if _INSTALLED is None:
        _INSTALLED = SolvedLevelMemoryPatch()
    return _INSTALLED
