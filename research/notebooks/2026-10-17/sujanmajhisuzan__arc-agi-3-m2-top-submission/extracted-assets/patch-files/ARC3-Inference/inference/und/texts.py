"""CONTRACT: Single source of truth for prompt blocks, system templates, and diagnostics (Rules 04, 05).

All static text strings and LLM-facing templates are defined here to guarantee
deterministic formatting and strict compliance with token budgets.
"""
from __future__ import annotations

UND_SYSTEM_PROMPT_BLOCK: str = (
    "World Model Tools (`wm` in Python sandbox):\n"
    "- `wm.digest()`, `wm.card()`, `wm.status()`, `wm.claim(...)`, `wm.goal(...)`, `wm.plan(...)`\n"
    "- `wm.run(actions)`: step-by-step execution. Stops immediately on NULL verdict (without resetting) returning counterexample.\n"
    "Formulate physics & goals as code predicates:\n"
    "def law_movement(before, action, after) -> bool | None:\n"
    "    # return True if transitions conform, False if contradicts (NULL), None if unobserved\n"
    "    ...\n"
    "def goal_exit(objs) -> bool:\n"
    "    # return True when objective condition holds on detected objects\n"
    "    ...\n"
    "Use `wm` tools to avoid fatal trial-and-error, plan routes, and conserve action budgets."
)

# Critical warnings
CRITICAL_TIME_PRESSURE_WARNING: str = (
    "[CRITICAL TIME PRESSURE]: Only {steps_remaining} action(s) remain before timeout/loss! "
    "Cease exploratory probing immediately and proceed along the verified direct goal path."
)

NULL_CONVERGENCE_WARNING: str = (
    "[MODEL DIVERGENCE]: The current hypothesis model failed to explain {null_count} recent "
    "transitions. Propose a refined rule or switch to alternative candidate features."
)

CIRCUIT_BREAKER_TRIPPED_WARNING: str = (
    "[CIRCUIT BREAKER TRIPPED]: {breaker_name} limit reached ({current}/{limit}). "
    "World model tools disabled on level {level}. Proceed with standard gameplay."
)

# Knowledge Card and Digest formatting templates
CARD_HEADER_TEMPLATE: str = (
    "=== ARC-AGI-3 KNOWLEDGE CARD (Level {level}) ===\n"
    "Confirmed Laws: {confirmed_count} | Active Hypotheses: {hypo_count} | Refuted: {refuted_count}\n"
)

DIGEST_HEADER_TEMPLATE: str = (
    "=== MECHANICS DIGEST (Level {level}, Step {step}) ===\n"
    "Action Budget Remaining: {steps_remaining} | Timer Present: {has_timer}\n"
)

DIAGNOSTIC_COUNTEREXAMPLE_TEMPLATE: str = (
    "Claim {claim_id} ({predicate}) contradicted at transition #{transition_idx}:\n"
    "  Expected: {expected}\n"
    "  Observed: {observed}\n"
)

RETENTION_REJECTION_MESSAGE_TEMPLATE: str = (
    "Function '{function_name}' was not retained: it references external or forbidden symbol '{symbol}'. "
    "All helper functions must be completely self-contained with standard library imports."
)
