"""CONTRACT: Shadow Verification of Carried Claims Across Level Boundaries (Phase 3, P3.2).

Performs passive shadow verification of game-scoped laws on the early turns of a new level:
- Carried hypotheses from prior levels (scope="game") are tested against empirical transitions.
- Non-blocking: never halts or interrupts agent execution, evaluates entirely in the background.
- Divergence detection: immediately flags when a prior law is contradicted on the new level,
  enabling context splitting or graceful demotion.
- Telemetry: streams shadow_verified and shadow_contradiction events line-by-line in JSONL.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inference.und.brusentsov_logic import CheckResult
from inference.und.claim_graph import (
    KINDS,
    Claim,
    ClaimGraph,
    ClaimStatus,
    Evidence,
    TransitionRecord as ClaimTransitionRecord,
    check_claim,
    split_by_context,
)
from inference.und.config.thresholds import DIAG_MAX_LINES, SHADOW_WINDOW_STEPS
from inference.und.telemetry import UndTelemetry


@dataclass
class ShadowClaimState:
    """State tracking for a single carried claim undergoing shadow verification."""

    claim_id: str
    kind: str
    subject: tuple[Any, ...]
    predicate: dict[str, Any]
    initial_status: ClaimStatus
    tested_count: int = 0
    holds_count: int = 0
    violated_count: int = 0
    verified: bool = False
    diverged: bool = False
    divergence_step: int | None = None
    divergence_details: str = ""


class ShadowVerifier:
    """Coordinates shadow testing of cross-level hypotheses during initial level turns."""

    def __init__(self, window_steps: int = SHADOW_WINDOW_STEPS) -> None:
        self.window_steps = max(1, int(window_steps))
        self.current_level: int = 0
        self.step_count: int = 0
        self.active: bool = False
        self.tracked_claims: dict[str, ShadowClaimState] = {}
        self.divergences: list[ShadowClaimState] = []

    def on_level_start(self, level: int, carried_claims: list[Claim]) -> None:
        """Initialize shadow verification for a newly entered level."""
        self.current_level = level
        self.step_count = 0
        self.divergences = []
        self.tracked_claims = {}

        # Shadow verification activates on new levels when carried claims exist
        if level > 0 and carried_claims:
            self.active = True
            for c in carried_claims:
                self.tracked_claims[c.id] = ShadowClaimState(
                    claim_id=c.id,
                    kind=c.kind,
                    subject=c.subject,
                    predicate=dict(c.predicate),
                    initial_status=c.status,
                )
        else:
            self.active = False

    def observe_transition(
        self,
        tr: ClaimTransitionRecord,
        graph: ClaimGraph,
        telemetry: UndTelemetry | None = None,
    ) -> list[dict[str, Any]]:
        """Passively shadow-test carried claims against an observed transition."""
        if not self.active:
            return []

        self.step_count += 1
        results: list[dict[str, Any]] = []

        for cid, state in list(self.tracked_claims.items()):
            c = graph.get(cid)
            if c is None:
                continue
            kind = KINDS.get(c.kind)
            if kind is None:
                continue

            r = check_claim(kind, c, tr)
            if r in (CheckResult.NA, CheckResult.UNOBSERVABLE):
                continue

            state.tested_count += 1

            if r is CheckResult.HOLDS_DIRECT:
                state.holds_count += 1
                state.verified = True
                ev = Evidence(tid=tr.tid, level=tr.level, result=CheckResult.HOLDS_DIRECT)
                c.support.append(ev)
                ev_res = {
                    "event": "shadow_verified",
                    "claim_id": c.id,
                    "kind": c.kind,
                    "level": tr.level,
                    "tid": tr.tid,
                }
                results.append(ev_res)
                if telemetry is not None:
                    telemetry.log_event("shadow_verified", ev_res, level=tr.level, step_index=tr.tid)

            elif r is CheckResult.VIOLATED:
                state.violated_count += 1
                state.diverged = True
                state.divergence_step = tr.tid
                state.divergence_details = (
                    f"Carried law {c.id} ({c.kind}) violated on Level {tr.level} at Step {tr.tid}"
                )
                if state not in self.divergences:
                    self.divergences.append(state)

                ev = Evidence(tid=tr.tid, level=tr.level, result=CheckResult.VIOLATED)
                c.counter.append(ev)

                # Attempt context split if context features distinguish this level
                direct = [e for e in c.support if e.result is CheckResult.HOLDS_DIRECT and not e.is_origin]
                if direct and c.counter:
                    split_by_context(c, graph, graph.cfg)

                ev_res = {
                    "event": "shadow_contradiction",
                    "claim_id": c.id,
                    "kind": c.kind,
                    "level": tr.level,
                    "tid": tr.tid,
                    "details": state.divergence_details,
                }
                results.append(ev_res)
                if telemetry is not None:
                    telemetry.log_event("shadow_contradiction", ev_res, level=tr.level, step_index=tr.tid)

        # Deactivate shadow window once initial step threshold is reached
        if self.step_count >= self.window_steps:
            self.active = False
            if telemetry is not None:
                telemetry.log_event(
                    "shadow_window_concluded",
                    {
                        "level": self.current_level,
                        "steps": self.step_count,
                        "verified_claims": len(self.get_verified()),
                        "diverged_claims": len(self.divergences),
                    },
                    level=self.current_level,
                    step_index=tr.tid,
                )

        return results

    def get_divergences(self) -> list[ShadowClaimState]:
        """Return carried claims that diverged during shadow verification."""
        return list(self.divergences)

    def get_verified(self) -> list[ShadowClaimState]:
        """Return carried claims verified on this level."""
        return [s for s in self.tracked_claims.values() if s.verified and not s.diverged]

    def get_summary(self) -> dict[str, Any]:
        """Structured summary of current shadow verification progress."""
        return {
            "active": self.active,
            "level": self.current_level,
            "step": self.step_count,
            "window_steps": self.window_steps,
            "tracked_count": len(self.tracked_claims),
            "verified_count": len(self.get_verified()),
            "diverged_count": len(self.divergences),
        }

    def format_diagnostic(self, max_lines: int = DIAG_MAX_LINES) -> str:
        """Format bounded diagnostic report on cross-level law divergences."""
        if not self.divergences:
            return ""
        lines: list[str] = [
            f"[SHADOW VERIFICATION ALERTS on Level {self.current_level}]:",
        ]
        for div in self.divergences:
            lines.append(
                f"  ! Claim {div.claim_id} ({div.kind}) contradicted at Step {div.divergence_step}: {div.predicate}"
            )
            if len(lines) >= max_lines:
                break
        return "\n".join(lines[:max_lines])
