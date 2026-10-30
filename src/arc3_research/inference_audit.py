"""Original H3v2.1 inference audit from ondrewsha's ARC-AGI-3 Stack S9.

Source: https://www.kaggle.com/code/ondrewsha/arc-agi-3-stack-s9
Credits: ondrewsha; based on Daniel Franzen's Apache-2.0 Milestone-2 notebook
and Tufa Labs. The functional body below is preserved
verbatim from source cell20; only its notebook-specific __main__ installer is
omitted. Install with install_inference_audit(ToolAgent) before game creation.
No other S9 component (HF/H1/SCH/RESET) is included here.
"""

# H3v2: inference audit (replaces H3). Built from the failure analysis of the 25x4 demo
# (docs/analysis/failure-modes.md): runs got stuck on a false MECHANIC generalised from one state ("UP does
# nothing", "the windows are decorative"), rejected the right idea without a test, then doubted a correct goal.
# The decisive experiment usually cost 1-4 actions. So the audit asks about conclusions, not strategy, and it
# fires earlier and on stagnation:
#   T1 level tokens >= 30k, then every +30k;  T2 >= 20k generated tokens since the last executed action;
#   T3 >= 3 assistant messages declaring the goal impossible/unreachable since the last audit.
# At most one audit per 12k generated tokens. The text is appended to the turn's user prompt, so the prompt
# prefix (and its cache) is untouched. Unit-tested locally (tests/test_h3v2_inference_audit.py).
# H3v2.1, from the S6 demo (docs/analysis/audit-s6.md; 658 audits in 100 plays):
#   - T2 never fired: a turn that executed nothing keeps the previous step summary marked "stale" with its old
#     executed_count, which reset the stagnation clock every turn. Stale summaries no longer count as actions,
#     and T2 gets its own short text (the 4-point list was ignored in 6 of 7 deliberation episodes).
#   - All 5 discoveries in a 40-event sample followed the FIRST audit on a level; the 3rd and later (42% of all)
#     were mentioned in 10% of replies and produced none. T1/T3 now fire at most twice per level.
#   - On a new level the previous level's "impossible" messages were counted again (the seen-set was cleared).
#   - The text asks for each hypothesis' prediction and for testing an untested extrapolation before a long batch
#     (ft09 p2: a 14-click batch built on an untested extrapolation).
import os
import re

H3V2_LEVEL_TOKENS = int(os.environ.get("H3V2_LEVEL_TOKENS", "30000"))
H3V2_STAGNATION_TOKENS = int(os.environ.get("H3V2_STAGNATION_TOKENS", "20000"))
H3V2_IMPOSSIBLE_COUNT = int(os.environ.get("H3V2_IMPOSSIBLE_COUNT", "3"))
H3V2_MIN_GAP_TOKENS = int(os.environ.get("H3V2_MIN_GAP_TOKENS", "12000"))
H3V2_MAX_PER_LEVEL = int(os.environ.get("H3V2_MAX_PER_LEVEL", "2"))  # T1 + T3; T2 has its own once-per-episode rule
H3V2_MARKER = "Inference audit for this turn"
H3V2_TEXT = (
    f"\n{H3V2_MARKER}\n"
    "Before acting, check the conclusions you are relying on:\n"
    "1. Single-state generalisations: list each rule like 'X does nothing', 'X is blocked', 'Y is a wall' or "
    "'Y cannot move' that you established in only one state or on one object. Name one other state, position or "
    "object where it could behave differently.\n"
    "2. Rejected without a test: list hypotheses about controls, mechanics or the goal that you dismissed by "
    "reasoning, a simulation or a proxy measurement instead of trying them in the game.\n"
    "3. Untried interactions: list action x object pairs you have not tried - each distinct object type, each "
    "action after a state change (size, colour, mode, selection), and known mechanics combined in a new order.\n"
    "4. Unexplained observations: list any change you wrote off as an artifact or noise; reproduce it within "
    "three actions and print a full before/after comparison.\n"
    "Then run the cheapest discriminating experiment (1-4 actions) from these lists before revising the goal or "
    "calling the level impossible; first write what each competing hypothesis predicts it will show. If your plan "
    "extrapolates a rule to cells, objects or states you have not tested, test one such case before committing a "
    "long batch. If your current plan is making verified progress, say so in one line and continue it.\n"
)
H3V2_STAGNATION_TEXT = (
    f"\n{H3V2_MARKER}\n"
    "You have generated about {tokens}k tokens since your last game action. More reasoning will not settle this: "
    "name the two hypotheses you are torn between, write what each predicts, and now run the one or two actions "
    "that tell them apart.\n"
)
_IMPOSSIBLE_RE = re.compile(
    r"\b(impossible|unsolvable|unreachable|not reachable|no way to|"
    r"can(?:not|'t|’t) be (?:done|reached|solved|filled|completed))\b",
    re.I,
)


_MOUSE_RE = re.compile(r"^MOUSE\(row=(\d+),\s*col=(\d+)\)$")
# H3v2.1 (S6 demo transcripts): valid_actions reach _build_user_prompt as engine names (ACTION1..ACTION7) while the
# history uses model names (UP, MOUSE, UNDO), so all 637 "never tried" lines in the demo falsely listed actions the
# model had used, plus RESET; and clicks were grouped by numeric colour ids the model never sees. Names now go
# through the harness mapping, RESET is left out (restarting is not an interaction to explore), and colours are
# the board letters of current_frame.ascii.
ARC_COLOR_CHARS = "WwgGcBMPRbSYOrNp"  # inference/utils/grid_utils.py
_ENGINE_TO_MODEL = {"ACTION1": "UP", "ACTION2": "DOWN", "ACTION3": "LEFT", "ACTION4": "RIGHT", "ACTION5": "SPACE",
                    "ACTION6": "MOUSE", "ACTION7": "UNDO"}


def _model_action(name):
    """Model-facing action name; the harness mapping when importable (it honours EXPOSE_UNDO), else the table."""
    raw = str(name or "").split("(", 1)[0].strip().upper()
    try:
        from inference.agent.action_names import to_model_action
    except Exception:  # outside the notebook the harness package may not import (tests, local checks)
        return _ENGINE_TO_MODEL.get(raw, raw)
    return to_model_action(raw)


def _letter(value):
    try:
        return ARC_COLOR_CHARS[int(value)]
    except (TypeError, ValueError, IndexError):
        return str(value)


def _effect(result):
    if not isinstance(result, dict):
        return "executed"
    animated = int(((result.get("animation") or {}).get("transient_pixels")) or 0) > 0
    if result.get("gameplay_changed") is True or result.get("level_completed"):
        return "effect"
    if result.get("gameplay_changed") is False:
        return "animated" if animated else "no-op"
    return "executed"


def coverage_lines(history_entries, level, valid_actions=None, current_frame=None, max_lines=14):
    """Harness-verified coverage of the current level: each action (clicks grouped by the clicked cell's colour),
    in how many distinct board states it was tried and with what result. history[i].frame is the frame AFTER
    history[i].action, so an action belongs to - and was taken in - the frame before it."""
    stats, prev = {}, None
    for entry in history_entries or []:
        frame = getattr(entry, "frame", None)
        action = str(getattr(entry, "action", "") or "").strip()
        if action and action.upper() != "RESET" and prev is not None and getattr(prev, "level", None) == level:
            grid = getattr(prev, "grid", None)
            mouse = _MOUSE_RE.match(action)
            if mouse:
                row, col = int(mouse.group(1)), int(mouse.group(2))
                try:
                    key = f"MOUSE on {_letter(grid[row][col])} cells"
                except (TypeError, IndexError):
                    key = "MOUSE"
            else:
                key = action.split("(", 1)[0]
            rec = stats.setdefault(key, {"n": 0, "states": set(), "cells": set(), "effect": 0, "no-op": 0, "animated": 0})
            rec["n"] += 1
            rec["states"].add(hash(grid))
            if mouse:
                rec["cells"].add((mouse.group(1), mouse.group(2)))
            outcome = _effect(getattr(entry, "result", None))
            if outcome in ("effect", "no-op", "animated"):
                rec[outcome] += 1
        if frame is not None:
            prev = frame
    if not stats:
        return []
    lines = ["Coverage on this level so far (from the action log; a no-op in one state does not prove the action "
             "is useless):"]
    for key, rec in sorted(stats.items(), key=lambda kv: -kv[1]["n"]):
        parts = [f"{n} {name}" for name, n in (("effect", rec["effect"]), ("animated", rec["animated"]),
                                                ("no-op", rec["no-op"])) if n]
        where = f"{len(rec['cells'])} cells, " if rec["cells"] else ""
        note = " - tried in only one state" if len(rec["states"]) == 1 and rec["n"] > 0 else ""
        lines.append(f"- {key}: {rec['n']} tries ({where}{len(rec['states'])} states) -> "
                     f"{', '.join(parts) or 'no result recorded'}{note}")
    tried = {key.split(" ", 1)[0] for key in stats}
    available = []
    for name in valid_actions or []:
        model_name = _model_action(name)
        if model_name and model_name != "RESET" and model_name not in available:
            available.append(model_name)
    untried = [a for a in available if a not in tried]
    if untried:
        lines.append("- never tried on this level: " + ", ".join(untried))
    grid = getattr(current_frame, "grid", None)
    if grid and ("MOUSE" in tried or "MOUSE" in available):
        counts = {}
        for row in grid:
            for value in row:
                counts[value] = counts.get(value, 0) + 1
        clicked = {k[len("MOUSE on "):-len(" cells")] for k in stats if k.startswith("MOUSE on ")}
        background = max(counts, key=counts.get) if counts else None
        never = [_letter(c) for c in sorted(counts) if _letter(c) not in clicked and c != background]
        if never:
            lines.append("- board letters never clicked: " + ", ".join(never))
    return lines[:max_lines]


def _message_text(msg):
    parts = []
    if isinstance(msg, dict):
        for key in ("content", "reasoning_content", "reasoning"):
            value = msg.get(key)
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts += [p.get("text", "") for p in value if isinstance(p, dict) and isinstance(p.get("text"), str)]
    return "\n".join(parts)


def install_inference_audit(agent_cls, log_limit=300):
    """Wrap agent_cls._build_user_prompt; idempotent. Returns the wrapped original."""
    original = getattr(agent_cls, "_h3v2_original_build", None) or agent_cls._build_user_prompt
    logged = {"n": 0}

    def build_user_prompt_with_audit(self, *args, **kwargs):
        prompt = original(self, *args, **kwargs)
        try:
            tokens = int(getattr(self, "_session_generated_tokens", 0))
            level_start = int(getattr(self, "_tokens_at_level_start", 0))
            history = [m for m in (getattr(self, "_history_messages", None) or []) if isinstance(m, dict)]
            if getattr(self, "_h3v2_level_start", None) != level_start:  # new level (or first call)
                self._h3v2_level_start = level_start
                self._h3v2_next_level_audit = level_start + H3V2_LEVEL_TOKENS
                self._h3v2_last_action_tokens = tokens
                self._h3v2_impossible = 0
                self._h3v2_stagnation_fired = False
                self._h3v2_level_audits = 0
                # messages already in history belong to the previous level: mark them seen without counting them.
                # Keyed by text, not id(): ids of evicted messages are reused and trimming may copy message dicts.
                self._h3v2_seen = getattr(self, "_h3v2_seen", set()) | {hash(_message_text(m)) for m in history}
            summary = kwargs.get("previous_step_summary") or {}
            try:
                executed = int(summary.get("executed_count") or 0)
            except (TypeError, ValueError):
                executed = 0
            # the harness ends a turn right after a call that executed actions; a turn that executed nothing
            # carries the previous summary over marked "stale" (tool_agent._run_python_tool)
            if executed > 0 and not summary.get("stale"):
                self._h3v2_last_action_tokens = tokens
                self._h3v2_stagnation_fired = False
            for msg in history[-8:]:
                key = hash(_message_text(msg))
                if msg.get("role") == "assistant" and key not in self._h3v2_seen:
                    self._h3v2_seen.add(key)
                    if _IMPOSSIBLE_RE.search(_message_text(msg)):
                        self._h3v2_impossible += 1
            trigger = None
            capped = self._h3v2_level_audits >= H3V2_MAX_PER_LEVEL
            if not self._h3v2_stagnation_fired and tokens - self._h3v2_last_action_tokens >= H3V2_STAGNATION_TOKENS:
                trigger = "stagnation"
            elif not capped and tokens >= self._h3v2_next_level_audit:
                trigger = "level-tokens"
            elif not capped and self._h3v2_impossible >= H3V2_IMPOSSIBLE_COUNT:
                trigger = "impossible"
            last_audit = getattr(self, "_h3v2_last_audit_tokens", None)
            if trigger and (last_audit is None or tokens - last_audit >= H3V2_MIN_GAP_TOKENS):
                self._h3v2_last_audit_tokens = tokens
                self._h3v2_audits = getattr(self, "_h3v2_audits", 0) + 1
                if trigger == "stagnation":
                    self._h3v2_stagnation_fired = True
                else:
                    self._h3v2_level_audits += 1
                    if trigger == "level-tokens":
                        self._h3v2_next_level_audit = tokens + H3V2_LEVEL_TOKENS
                    else:
                        self._h3v2_impossible = 0
                if logged["n"] < log_limit:
                    logged["n"] += 1
                    print(f"[H3v2] inference audit #{self._h3v2_audits} ({trigger}) at "
                          f"{tokens - level_start} level tokens", flush=True)
                if trigger == "stagnation":
                    idle_k = max(1, round((tokens - self._h3v2_last_action_tokens) / 1000))
                    prompt = prompt + H3V2_STAGNATION_TEXT.format(tokens=idle_k)
                else:
                    prompt = prompt + H3V2_TEXT
                try:
                    frame = kwargs.get("current_frame")
                    level_now = getattr(frame, "level", None)
                    if isinstance(level_now, int):
                        cov = coverage_lines(kwargs.get("history_entries"), level_now,
                                             kwargs.get("valid_actions"), frame)
                        if cov:
                            prompt = prompt + "\n".join(cov) + "\n"
                except Exception as exc:  # the table is optional; the audit text is already in
                    print(f"[H3v2] coverage skipped: {exc!r}", flush=True)
        except Exception as exc:  # never break a turn because of the audit
            print(f"[H3v2] audit skipped: {exc!r}", flush=True)
        return prompt

    agent_cls._h3v2_original_build = original
    agent_cls._build_user_prompt = build_user_prompt_with_audit
    return original

