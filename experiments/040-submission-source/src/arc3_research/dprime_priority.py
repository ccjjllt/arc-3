"""Isolated public D-prime admission policy for the frozen Franzen harness.

Formula, pace, fade and optional fresh admission follow tantan0327/arc3-franzen-dprime
v2 cell17 (public CC0 / MIT-0 patch, credit shiiin9 / Affectify and red-down).
This does not implement its optional ``base`` or ``ours`` parameter families.
Install after the baseline environment is set and before any game session starts.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import textwrap
import threading
import time


DPRIME = {
    "level_pow": 0.5, "eff_const": 300.0, "eff_pow": 2.5,
    "pace_pow": 0.4, "pace_ref": 30000.0, "c_action": 0.1,
    "action_scale": 115.0, "c_token": 0.9, "token_scale": 225000.0,
    "lin_floor": 0.1, "rel_pow": 0.5, "b1": 10.0, "b2": 14.0, "b3": 16.0,
}
FADE = 0.4
SCALE = 1000.0
ENVIRONMENT = {
    "ARC3_PRIORITY_PACE": "1", "ARC3_PRIORITY_REFRESH_QUEUE": "1",
    "ARC3_PRIORITY_TAIL_FADE": "1", "ARC3_PRIORITY_TAIL_FADE_FRACTION": "0.4",
}
EXPECTED_ORIGINAL_SOURCES = {
    "gate.acquire": "b42cafec50e428f00ed6bd1e26eb6b165170f6d3d8a3ae1468ef99b74cb8eb74",
    "gate.snapshot": "8257ff0e0d898b39cb423b3166848fa062a3d486a35498f4d36ccd79b14e4708",
    "session.play": "cbd293a763b44ab65ba1c6107e7431c06e1644ee56c65885bd02e8d27d4e72e1",
}
_INSTALLED = None


def norm_levels(total_levels):
    try:
        n = int(total_levels)
    except (TypeError, ValueError):
        n = 10
    n = min(10, max(6, n if n > 0 else 10))
    return 55.0 / (n * (n + 1) / 2), n


def value_dprime(level, a, t, pace, total_levels, phi, p=DPRIME):
    norm, n = norm_levels(total_levels)
    A = (1.0 + p["level_pow"] * (level - 1)) * norm * (p["eff_const"] / (p["eff_const"] + a)) ** p["eff_pow"]
    if pace > 0:
        A *= min(4.0, max(0.25, (p["pace_ref"] / max(1.0, pace)) ** p["pace_pow"]))
    rel = pace if pace > 0 else p["pace_ref"]
    scale = p["token_scale"] * (min(2.0, max(0.5, rel / p["pace_ref"])) ** p["rel_pow"])
    C = (p["c_action"] * max(p["lin_floor"], 1.0 - a / p["action_scale"])
         + p["c_token"] * max(p["lin_floor"], 1.0 - t / scale))
    B = (0.0, p["b1"], p["b2"], p["b3"])[min(max(0, n - level), 3)]
    return A * C + B * phi


def priority_value(state, *, tail_fraction=None, **_ignored):
    phi = 1.0 if tail_fraction is None else min(1.0, max(0.0, float(tail_fraction)))
    value = value_dprime(
        max(1, int(state.level)), max(0, int(state.actions)), max(0.0, float(state.tokens)),
        float(getattr(state, "cost_multiplier", 0.0) or 0.0), getattr(state, "total_levels", None), phi,
    )
    if _INSTALLED is not None:
        _INSTALLED.priority_calls += 1
    return max(1, int(value * SCALE))


class PaceTracker:
    """Mean generated tokens per cleared level, or zero before the first clear."""

    def __init__(self):
        self.completed = 0
        self.tokens = 0.0
        if _INSTALLED is not None:
            _INSTALLED.pace_instances += 1

    def record_completion(self, tokens_used, reference_tokens=0.0):
        self.completed += 1
        self.tokens += max(0.0, float(tokens_used))
        if _INSTALLED is not None:
            _INSTALLED.pace_updates += 1

    def cost_multiplier(self):
        return self.tokens / self.completed if self.completed else 0.0


def _source_hash(function):
    source = textwrap.dedent(inspect.getsource(function)).strip() + "\n"
    return hashlib.sha256(source.encode()).hexdigest()


class DprimePriorityPatch:
    def __init__(self, tool_agent, solver, *, price_fresh=False):
        if type(price_fresh) is not bool:
            raise ValueError("price_fresh must be a bool")
        self.tool_agent = tool_agent
        self.solver = solver
        self.gate_class = tool_agent._PriorityGate
        self.session_class = solver._HarnessGameSession
        self.original_priority = tool_agent.priority_value
        self.original_pace = tool_agent.ProgressPace
        self.original_acquire = self.gate_class.acquire
        self.original_play = self.session_class.play
        self.original_environment = {key: os.environ.get(key) for key in ENVIRONMENT}
        self.price_fresh = price_fresh
        self.priority_calls = self.fresh_priced = self.pace_instances = self.pace_updates = 0
        self.local = threading.local()
        self.source_hashes = {
            "gate.acquire": _source_hash(self.original_acquire),
            "gate.snapshot": _source_hash(self.gate_class._snapshot_priority),
            "session.play": _source_hash(self.original_play),
        }
        if self.source_hashes != EXPECTED_ORIGINAL_SOURCES:
            raise ValueError("D-prime requires the audited original Franzen gate/session functions")
        if (tool_agent.ToolAgent.__init__.__globals__ is not tool_agent.__dict__
                or self.gate_class._snapshot_priority.__globals__ is not tool_agent.__dict__
                or solver._priority_gate is not tool_agent._priority_gate
                or solver.ToolAgent is not tool_agent.ToolAgent):
            raise ValueError("D-prime module aliases changed")
        if getattr(tool_agent, "_PRIORITY_GATE", None) is not None:
            raise ValueError("Install D-prime before the first global priority gate is created")
        if getattr(self.original_play, "_priority_form", False):
            raise ValueError("A public priority-form session patch is already installed")
        if (os.environ.get("ARC3_PRIORITY_SCORE_NORMALIZATION") != "1"
                or os.environ.get("ARC3_PRIORITY_TAIL_LOOKUP") != "remaining"):
            raise ValueError("Retain009 total-level snapshot options before installing D-prime")
        patch = self

        def play(session, *args, **kwargs):
            run = getattr(getattr(session, "game", None), "game_run", None)
            patch.local.total_levels = getattr(run, "number_of_levels", None)
            try:
                return patch.original_play(session, *args, **kwargs)
            finally:
                patch.local.total_levels = None

        fresh_floor = tool_agent._PRIORITY_UNTRIMMED_BASE - tool_agent._PRIORITY_BAND
        snapshot_class = tool_agent.PrioritySnapshot

        def acquire(gate, priority):
            if priority < fresh_floor:
                return patch.original_acquire(gate, priority)
            state = snapshot_class(1, 0, 0.0, 0.0, getattr(patch.local, "total_levels", None))
            value = gate._snapshot_priority(state, time.monotonic())
            with gate._cond:
                gate._enqueue_and_wait(value, state)
            patch.fresh_priced += 1

        play._priority_form = True
        acquire._priority_form = True
        self.play = play if price_fresh else self.original_play
        self.acquire = acquire if price_fresh else self.original_acquire
        tool_agent.priority_value = priority_value
        tool_agent.ProgressPace = PaceTracker
        if price_fresh:
            self.gate_class.acquire = acquire
            self.session_class.play = play
        os.environ.update(ENVIRONMENT)

    def snapshot(self):
        return {
            "patch": "dprime-priority-v1", "form": "dprime", "parameters": dict(DPRIME),
            "fade_fraction": FADE, "price_fresh": self.price_fresh, "priority_scale": SCALE,
            "environment": {key: os.environ.get(key) for key in ENVIRONMENT},
            "source_hashes": dict(self.source_hashes),
            "priority_calls": self.priority_calls, "fresh_priced": self.fresh_priced,
            "pace_instances": self.pace_instances, "pace_updates": self.pace_updates,
            "counter_semantics": "Best-effort CPython thread counters; execution evidence, not timing or score.",
            "active": (self.tool_agent.priority_value is priority_value
                       and self.tool_agent.ProgressPace is PaceTracker
                       and self.gate_class.acquire is self.acquire
                       and self.session_class.play is self.play
                       and all(os.environ.get(key) == value for key, value in ENVIRONMENT.items())),
            "new_model_requests": False, "new_tools": False, "prompt_modified": False,
        }

    def uninstall(self):
        global _INSTALLED
        if getattr(self.tool_agent, "_PRIORITY_GATE", None) is not None:
            raise ValueError("Do not uninstall while the process-global gate exists")
        pairs = ((self.tool_agent, "priority_value", priority_value, self.original_priority),
                 (self.tool_agent, "ProgressPace", PaceTracker, self.original_pace),
                 (self.gate_class, "acquire", self.acquire, self.original_acquire),
                 (self.session_class, "play", self.play, self.original_play))
        if any(getattr(owner, name) is not installed for owner, name, installed, _ in pairs):
            raise ValueError("Cannot undo D-prime after another component changed its targets")
        for owner, name, _, original in pairs:
            setattr(owner, name, original)
        for key, original in self.original_environment.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
        if _INSTALLED is self:
            _INSTALLED = None


def install_dprime_priority(*, price_fresh=False):
    global _INSTALLED
    if _INSTALLED is None:
        from inference.agent import tool_agent
        from inference.framework import solver
        _INSTALLED = DprimePriorityPatch(tool_agent, solver, price_fresh=price_fresh)
    elif not _INSTALLED.snapshot()["active"]:
        raise ValueError("Previously installed D-prime targets changed")
    elif _INSTALLED.price_fresh is not price_fresh:
        raise ValueError("D-prime is already installed with a different price_fresh option")
    return _INSTALLED
