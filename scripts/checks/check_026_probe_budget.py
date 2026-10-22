#!/usr/bin/env python3
"""026 CPU unit verification for ProbeBudget (no engine, no model, no GPU).

Covers the handoff contract: pre-dispatch interception, exact quota,
graceful stop dicts (no exceptions), boundary precedence, K=0 pure
recompute, and the stdout/def handoff contract shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from arc3_research.probe_budget import ProbeBudget, run_probe_batch

failures = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + (f" :: {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def fake_dispatch(results):
    it = iter(results)
    calls = []

    def dispatch(action):
        calls.append(action)
        return next(it)

    return dispatch, calls


# 1. K=3 over a 12-action plan: exactly 3 dispatches, graceful stop, no raise.
b = ProbeBudget(3)
plan = [f"move{i}" for i in range(12)]
d, calls = fake_dispatch([{"executed": True} for _ in range(12)])
out = run_probe_batch(plan, b, d, level=2)
check("quota-3-of-12 dispatches", len(calls) == 3, str(len(calls)))
check("quota-3-of-12 stop reason", out["stop"]["stop_reason"] == "probe_budget_reached")
check("quota-3-of-12 skipped", out["stop"]["skipped_actions"] == plan[3:])
check("quota-3-of-12 flags", out["stop"]["executed"] is False and out["stop"]["stopped_early"] is True)

# 2. K=0 pure recompute: zero dispatches.
b = ProbeBudget(0)
d, calls = fake_dispatch([{"executed": True}])
out = run_probe_batch(["a", "b"], b, d)
check("K=0 dispatches none", calls == [] and out["executed_results"] == [])
check("K=0 stop", out["stop"]["stop_reason"] == "probe_budget_reached"
      and out["stop"]["skipped_actions"] == ["a", "b"])

# 3. level_completed on 2nd of 5: boundary wins, rest skipped.
b = ProbeBudget(3)
d, calls = fake_dispatch([{"executed": True}, {"executed": True, "level_completed": True},
                          {"executed": True}])
out = run_probe_batch(["a", "b", "c", "d", "e"], b, d, level=1)
check("boundary stops early", len(calls) == 2, str(len(calls)))
check("boundary reason", out["stop"]["stop_reason"] == "boundary_level_completed")
check("boundary skipped", out["stop"]["skipped_actions"] == ["c", "d", "e"])

# 4. game_over on 1st: stops immediately.
b = ProbeBudget(3)
d, calls = fake_dispatch([{"executed": True, "game_over": True}, {"executed": True}])
out = run_probe_batch(["a", "b"], b, d)
check("game_over stops", len(calls) == 1 and out["stop"]["stop_reason"] == "boundary_game_over")

# 5. under-quota full plan: no stop payload.
b = ProbeBudget(5)
d, calls = fake_dispatch([{"executed": True}, {"executed": True}])
out = run_probe_batch(["a", "b"], b, d)
check("under-quota no stop", out["stop"] is None and len(calls) == 2)

# 6. invalid quota rejected at construction (fail fast, before any run).
try:
    ProbeBudget(-1)
    check("negative quota rejected", False)
except ValueError:
    check("negative quota rejected", True)

# 7. handoff contract shape: stop payload carries counts for the stdout line,
#    and repair text goes through stdout / top-level def (keys present).
b = ProbeBudget(1)
d, calls = fake_dispatch([{"executed": True, "gameplay_changed": False}])
out = run_probe_batch(["probe1", "probe2"], b, d, level=3)
s = out["stop"]
check("contract keys", all(k in s for k in
      ("stop_reason", "skipped_actions", "probe_used", "probe_quota",
       "executed_count", "stopped_early")))
line = (f"probe stop={s['stop_reason']} used={s['probe_used']}/{s['probe_quota']} "
        f"skipped={s['skipped_actions']}")
check("stdout line renders", "probe_budget_reached" in line and "1/1" in line, line)

print(f"\n{len(failures)} failures")
sys.exit(1 if failures else 0)
