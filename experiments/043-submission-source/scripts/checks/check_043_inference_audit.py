#!/usr/bin/env python3
"""CPU contract checks for the unchanged S9 H3v2.1 audit body.

The prompt builder is a deliberate substitute; runtime Frame/HistoryEntry and
action-name mapping are real. No model, GPU, game or score is involved.
"""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/arc3_research/inference_audit.py"
UPSTREAM = ROOT / "research/snapshots/2026-10-30-candidates/ondrewsha__arc-agi-3-stack-s9/source.ipynb"
BUNDLE = ROOT / "research/runtime-bundle/src/ARC3-Inference"
sys.path.insert(0, str(BUNDLE))
from inference.agent.runtime_state import Frame, HistoryEntry

spec = importlib.util.spec_from_file_location("inference_audit", MODULE)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)
BASE = "ORIGINAL USER PROMPT\n"
FRAME = Frame(((0, 1), (0, 1)), step=1, level=1)


class SubstituteAgent:
    def __init__(self):
        self._session_generated_tokens = 0
        self._tokens_at_level_start = 0
        self._history_messages = []

    def _build_user_prompt(self, action_num, *, valid_actions, current_frame=None,
                           history_entries=None, previous_step_summary=None):
        self._test_forwarded = (action_num, valid_actions, current_frame,
                                history_entries, previous_step_summary)
        return BASE


ORIGINAL_BUILDER = SubstituteAgent._build_user_prompt
audit.install_inference_audit(SubstituteAgent, log_limit=0)


def build(agent, tokens, summary=None, *, frame=FRAME, history=None):
    agent._session_generated_tokens = tokens
    return agent._build_user_prompt(
        7, valid_actions=["ACTION1", "ACTION2", "ACTION6", "ACTION7", "RESET"],
        current_frame=frame, history_entries=history or [], previous_step_summary=summary,
    )


def fresh_action():
    return {"executed_count": 1, "stale": False}


def main():
    checks = {}
    original_cell = "".join(json.loads(UPSTREAM.read_text())["cells"][20]["source"])
    body = original_cell.split('\nif __name__ == "__main__":', 1)[0]
    module = MODULE.read_text()
    checks["functional_body_byte_identical_to_s9_cell20"] = module.endswith(body)
    checks["module_addition_only_docstring"] = isinstance(ast.parse(module).body[0], ast.Expr)
    checks["defaults_unchanged"] = (
        audit.H3V2_LEVEL_TOKENS, audit.H3V2_STAGNATION_TOKENS,
        audit.H3V2_IMPOSSIBLE_COUNT, audit.H3V2_MIN_GAP_TOKENS,
        audit.H3V2_MAX_PER_LEVEL,
    ) == (30000, 20000, 3, 12000, 2)

    a = SubstituteAgent()
    checks["normal_prompt_unmodified"] = build(a, 0) == BASE
    checks["arguments_forwarded"] = a._test_forwarded[0] == 7 and a._test_forwarded[2] is FRAME
    checks["no_early_level_trigger"] = build(a, 29999, fresh_action()) == BASE
    first = build(a, 30000, fresh_action())
    checks["level_trigger_at_30k"] = first == BASE + audit.H3V2_TEXT and a._h3v2_level_audits == 1
    checks["second_level_trigger_not_early"] = build(a, 59999, fresh_action()) == BASE
    second = build(a, 60000, fresh_action())
    checks["second_level_trigger_at_60k"] = second == BASE + audit.H3V2_TEXT and a._h3v2_level_audits == 2
    checks["level_audits_capped_at_two"] = build(a, 90000, fresh_action()) == BASE and a._h3v2_audits == 2

    b = SubstituteAgent()
    build(b, 0)
    checks["stagnation_not_early"] = build(b, 19999) == BASE
    stagnant = build(b, 20000)
    checks["stagnation_at_20k_short_prompt"] = stagnant == BASE + audit.H3V2_STAGNATION_TEXT.format(tokens=20)
    checks["cooldown_blocks_other_trigger_before_12k"] = build(b, 31999) == BASE
    checks["other_trigger_allowed_at_12k_gap"] = build(b, 32000) == BASE + audit.H3V2_TEXT
    checks["stagnation_does_not_use_level_cap"] = b._h3v2_level_audits == 1
    checks["stagnation_episode_marked_once"] = b._h3v2_stagnation_fired is True

    c = SubstituteAgent()
    build(c, 0, fresh_action())
    stale = {"executed_count": 9, "stale": True}
    checks["stale_previous_action_does_not_reset_clock"] = (
        build(c, 20000, stale) == BASE + audit.H3V2_STAGNATION_TEXT.format(tokens=20)
        and c._h3v2_last_action_tokens == 0
    )
    build(c, 21000, fresh_action())
    checks["new_action_rearms_stagnation"] = not c._h3v2_stagnation_fired and c._h3v2_last_action_tokens == 21000
    # T1 is eligible here as well; stagnation has the upstream-defined priority.
    checks["stagnation_has_priority_over_level_trigger"] = (
        build(c, 41000, stale) == BASE + audit.H3V2_STAGNATION_TEXT.format(tokens=20)
    )

    d = SubstituteAgent()
    build(d, 0)
    d._history_messages = [{"role": "assistant", "content": f"Case {i} is impossible"} for i in range(3)]
    checks["three_new_impossible_messages_trigger"] = build(d, 1000, fresh_action()) == BASE + audit.H3V2_TEXT
    checks["same_history_not_counted_twice"] = build(d, 2000, fresh_action()) == BASE and d._h3v2_impossible == 0
    d._history_messages.extend({"role": "assistant", "content": f"New case {i} is unreachable"} for i in range(3))
    checks["impossible_trigger_respects_cooldown"] = build(d, 12999, fresh_action()) == BASE
    checks["impossible_trigger_at_gap_boundary"] = build(d, 13000, fresh_action()) == BASE + audit.H3V2_TEXT
    d._tokens_at_level_start = 20000
    checks["new_level_does_not_recount_old_impossible"] = build(d, 20000, fresh_action()) == BASE and d._h3v2_impossible == 0
    checks["level_cap_resets_on_new_level"] = d._h3v2_level_audits == 0
    checks["new_level_threshold_is_relative"] = build(d, 50000, fresh_action()) == BASE + audit.H3V2_TEXT

    e = SubstituteAgent()
    build(e, 0)
    e._history_messages = [{"role": "assistant", "content": "impossible"}] * 3
    checks["identical_message_text_deduplicated"] = build(e, 1000, fresh_action()) == BASE and e._h3v2_impossible == 1
    e._history_messages += [{"role": "user", "content": "unreachable impossible"}]
    checks["user_messages_not_counted"] = build(e, 2000, fresh_action()) == BASE and e._h3v2_impossible == 1

    os.environ["EXPOSE_UNDO"] = "on"  # Match the existing042 environment for the real mapper.
    entries = [
        HistoryEntry("RESET", Frame(((0, 1), (0, 1)), 0, 1)),
        HistoryEntry("UP", Frame(((0, 1), (0, 1)), 1, 1),
                     {"gameplay_changed": False, "animation": {"transient_pixels": 2}}),
        HistoryEntry("MOUSE(row=0, col=1)", Frame(((0, 1), (0, 1)), 2, 1), {"gameplay_changed": True}),
    ]
    lines = audit.coverage_lines(entries, 1, ["ACTION1", "ACTION2", "ACTION6", "ACTION7", "RESET"], FRAME)
    joined = "\n".join(lines)
    checks["coverage_engine_names_mapped"] = "never tried on this level: DOWN, UNDO" in joined and "ACTION" not in joined
    checks["coverage_reset_not_suggested"] = "RESET" not in joined
    checks["coverage_click_uses_visible_letter"] = "MOUSE on w cells" in joined
    checks["coverage_animation_classified"] = "1 animated" in joined
    checks["coverage_uses_pre_action_state"] = "1 states" in joined and "1 cells" in joined
    checks["coverage_bound_14_lines"] = len(lines) <= 14
    checks["new_level_omits_old_level_actions"] = audit.coverage_lines(entries, 2) == []
    f = SubstituteAgent()
    build(f, 0)
    actual = build(f, 30000, fresh_action(), history=entries)
    checks["coverage_appended_after_original_and_audit"] = actual == BASE + audit.H3V2_TEXT + joined + "\n"

    original_again = audit.install_inference_audit(SubstituteAgent, log_limit=0)
    checks["install_is_idempotent"] = original_again is ORIGINAL_BUILDER
    g = SubstituteAgent()
    build(g, 0)
    checks["reinstall_does_not_duplicate_audit"] = build(g, 30000, fresh_action()).count(audit.H3V2_MARKER) == 1
    untouched = SubstituteAgent()
    checks["other_agent_has_no_shared_trigger_state"] = build(untouched, 0) == BASE and not hasattr(untouched, "_h3v2_audits")

    def worker(_):
        agent = SubstituteAgent()
        build(agent, 0)
        text = build(agent, 30000, fresh_action())
        return text == BASE + audit.H3V2_TEXT and agent._h3v2_audits == 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        checks["32_parallel_instances_keep_independent_state"] = all(pool.map(worker, range(32)))

    broken = SubstituteAgent()
    broken._session_generated_tokens = object()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        fallback = broken._build_user_prompt(0, valid_actions=[])
    checks["audit_error_preserves_original_prompt"] = fallback == BASE and "audit skipped" in output.getvalue()

    runtime = (BUNDLE / "inference/agent/tool_agent.py").read_text()
    checks["real_call_site_supplies_required_keywords"] = all(
        fragment in runtime for fragment in (
            "valid_actions=valid_actions,\n            current_frame=current_frame,\n            history_entries=history_entries,\n            previous_step_summary=self._last_step_summary,",
            "self._session_generated_tokens += generated_token_count",
            "self._tokens_at_level_start = self._session_generated_tokens",
        )
    )
    setup = "".join(json.loads((ROOT / "notebooks/042-startup-ready/submission.ipynb").read_text())["cells"][4]["source"])
    checks["042_does_not_select_short_resume_prompt"] = "ARC3_YIELD_RESUME_PROMPT" not in setup

    result = {
        "passed": all(checks.values()), "checks_passed": sum(checks.values()), "checks": checks,
        "implementation_sha256": hashlib.sha256(MODULE.read_bytes()).hexdigest(),
        "upstream_cell20_sha256": hashlib.sha256(original_cell.encode()).hexdigest(),
        "functional_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "upstream_source": str(UPSTREAM.relative_to(ROOT)),
        "runtime_tool_agent_sha256": hashlib.sha256(runtime.encode()).hexdigest(),
        "example_coverage": lines,
        "thresholds": {"level": 30000, "stagnation": 20000, "impossible": 3, "minimum_gap": 12000, "max_per_level": 2},
        "limitations": [
            "CPU contract checks with a substitute original prompt builder; no model, GPU, real game action or score evidence.",
            "Frame, HistoryEntry and action-name mapping are imported from the actual runtime bundle.",
            "The32-instance threaded check uses different agent objects, matching the real solver's per-game analyzer allocation.",
            "T3 is a lexical heuristic and can count negative or hypothetical mentions; body intentionally unchanged.",
            "In-progress long planning can be interrupted by an audit; official benefit is unproven.",
            "Short/state_only resume modes would omit the modified full opener;042 retains the full default.",
        ],
    }
    out = ROOT / "experiments/043-preparation/inference-audit-cpu.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks_passed": result["checks_passed"],
                      "failed": [k for k, v in checks.items() if not v], "report": str(out)}, indent=2))
    assert result["passed"]


if __name__ == "__main__":
    main()
