"""ClaimGraph: 3-Valued Brusentsov Logic Engine for ARC-AGI-3 World Laws.

Implements the formal relationship of necessary consequence (x => y):
  - HOLDS_DIRECT (xy)      : Direct independent confirmation.
  - VIOLATED (xy'_0)       : Physical contradiction / excluded member.
  - HOLDS_CONTRA (x'y')    : Contrapositive confirmation; closes existence condition y',
                             but does NOT count as independent direct evidence.
  - NA (x'y)               : Omission / irrelevant member; no status change.
  - UNOBSERVABLE           : Epistemic lack of visibility; no status change.

Maintains four truth statuses:
  - PLUS (+)      : Certified necessary law of the environment.
  - MINUS (-)     : Empirically refuted law.
  - UNDECIDED (?) : Active working hypothesis.
  - ZERO (0)      : Closed parent claim superseded by contextual child claims.
"""

from __future__ import annotations

import copy
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, Sequence

from inference.und.brusentsov_logic import CheckResult
from inference.und.features import (
    extract_transition_features,
    find_separating_features,
    generate_splitting_hints,
    select_best_splitting_feature,
)

logger = logging.getLogger(__name__)


class ClaimStatus(str, Enum):
    """Status of an empirical claim in the cognitive loop."""
    PLUS = "+"          # Verified true law (proven by direct evidence & contrast)
    MINUS = "-"        # Refuted law (refuted by persistent counterexamples)
    ZERO = "0"          # Closed / superseded by context-split children
    UNDECIDED = "?"     # Working hypothesis (pending evidence or contrast)


@dataclass(frozen=True)
class Evidence:
    """An empirical witness record certifying or challenging a claim."""
    tid: int
    level: int
    result: CheckResult
    is_origin: bool = False           # True if transition induced the claim


@dataclass(frozen=True)
class GraphEvent:
    """An event signaling an epistemic status change in the claim graph."""
    event_type: str                   # "PLUS" | "MINUS" | "SPLIT" | "UNEXPLAINED"
    claim_id: str
    tid: int
    detail: str = ""


def _freeze(obj: Any) -> Any:
    """Recursively freeze dicts and lists into hashable tuples."""
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, (list, tuple, set)):
        return tuple(_freeze(x) for x in obj)
    return obj


@dataclass
class TransitionRecord:
    """Comprehensive factual snapshot of a single environment transition."""
    tid: int
    level: int
    action_id: str
    action_data: dict[str, Any] = field(default_factory=dict)
    before_grid: list[list[int]] = field(default_factory=list)
    after_grid: list[list[int]] = field(default_factory=list)
    terminal: str | None = None       # "WIN" | "GAME_OVER" | None
    zero_delta: bool = False
    displacements: list[dict[str, Any]] = field(default_factory=list)
    context_features: dict[str, Any] = field(default_factory=dict)
    actor_sig: tuple[int, int] | None = None   # (color, shape_hash)
    touched_sigs: set[tuple[int, int]] = field(default_factory=set)


@dataclass
class Claim:
    """An empirical rule object expressing an invariant law of the environment."""
    id: str
    kind: str                         # "action_effect" | "controlled" | "passability" | "lethal" | "collectible"
    subject: tuple                    # Structural key (e.g. ("ACTION1",), (color, shape_hash))
    predicate: dict[str, Any]         # Predicate payload (e.g. {"dy": -1, "dx": 0})
    condition: dict[str, Any] | None = None  # Context condition (e.g. {"adjacent_sig": ...})
    scope: str = "game"               # "game" | "level"
    status: ClaimStatus = ClaimStatus.UNDECIDED
    support: list[Evidence] = field(default_factory=list)
    counter: list[Evidence] = field(default_factory=list)
    parent: str | None = None
    origin: str = "induced"           # "induced" | "proposed_llm" | "refined" | "carried"
    unexplained: bool = False
    awaiting_contrast: bool = False

    def key(self) -> tuple:
        """Deterministic deduplication key."""
        return (self.kind, self.subject, _freeze(self.predicate), _freeze(self.condition))

    def derive(
        self,
        condition: dict[str, Any],
        origin: str = "refined",
        evidence_tids: Sequence[int] = (),
    ) -> Claim:
        """Create a contextualized child claim inheriting core properties."""
        cond_repr = hashlib.sha256(repr(_freeze(condition)).encode("utf-8")).hexdigest()[:6]
        child_id = f"{self.id}.{len(self.support) + len(self.counter)}_{cond_repr}_{origin[:3]}"
        merged_condition = dict(self.condition or {})
        merged_condition.update(condition)
        inherited_support = [e for e in self.support if e.tid in evidence_tids]
        inherited_counter = [e for e in self.counter if e.tid in evidence_tids]
        return Claim(
            id=child_id,
            kind=self.kind,
            subject=self.subject,
            predicate=copy.deepcopy(self.predicate),
            condition=merged_condition,
            scope=self.scope,
            status=ClaimStatus.UNDECIDED,
            support=inherited_support,
            counter=inherited_counter,
            parent=self.id,
            origin=origin,
        )


class ClaimKind(Protocol):
    """Protocol defining how an empirical claim type evaluates conditions and induces hypotheses."""
    name: str

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        """Return True if condition x holds, False if absent, None if unobservable."""
        ...

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        """Return True if consequence y holds, False if absent, None if unobservable."""
        ...

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        """Return True if at least one observation with y' exists across all history."""
        ...

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        """Induce new working hypothesis claims from an observed transition."""
        ...


def check_claim(kind: ClaimKind, c: Claim, tr: TransitionRecord) -> CheckResult:
    """Pure universal evaluation of necessary consequence: x => y."""
    # Check context condition first if present
    if c.condition:
        for k, v in c.condition.items():
            if k == "not" and isinstance(v, dict):
                for nk, nv in v.items():
                    if tr.context_features.get(nk) == nv:
                        return CheckResult.NA
            elif tr.context_features.get(k) != v:
                return CheckResult.NA

    x = kind.x_holds(c, tr)
    y = kind.y_holds(c, tr)

    if x is None:
        return CheckResult.UNOBSERVABLE
    if x:
        if y is None:
            return CheckResult.UNOBSERVABLE
        return CheckResult.HOLDS_DIRECT if y else CheckResult.VIOLATED

    # Condition x is absent (x')
    if y is None:
        return CheckResult.UNOBSERVABLE
    return CheckResult.NA if y else CheckResult.HOLDS_CONTRA


try:
    from inference.und.config.thresholds import DEFAULT_N_DIRECT, DEFAULT_N_LEVELS, DEFAULT_N_MINUS
except ImportError:
    DEFAULT_N_DIRECT = {
        "action_effect": 2, "controlled": 2, "passability": 2,
        "lethal": 1, "collectible": 1, "trigger": 2, "click_effect": 2, "undo_exact": 2,
    }
    DEFAULT_N_LEVELS = {
        "action_effect": 1, "controlled": 1, "passability": 1,
        "lethal": 1, "collectible": 1, "trigger": 1, "click_effect": 1, "undo_exact": 1,
    }
    DEFAULT_N_MINUS = 2


@dataclass
class ClaimConfig:
    """Thresholds for claim status graduation (reads defaults from config.thresholds)."""
    n_direct: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_N_DIRECT))
    n_levels: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_N_LEVELS))
    n_minus: int = DEFAULT_N_MINUS


# =============================================================================
# Specific Claim Kinds
# =============================================================================

class ActionEffectKind:
    """Evaluates whether an action produces a consistent translation vector (dy, dx)."""
    name = "action_effect"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_act = c.subject[0] if c.subject else ""
        return str(tr.action_id).upper() == str(target_act).upper()

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        if tr.zero_delta:
            return False
        exp_dy = int(c.predicate.get("dy", 0))
        exp_dx = int(c.predicate.get("dx", 0))
        for d in tr.displacements:
            if isinstance(d, dict):
                dy = int(d.get("dy", 0))
                dx = int(d.get("dx", 0))
                if dy == exp_dy and dx == exp_dx:
                    return True
        return False

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        # A contrast witness for translation is any transition where the consequence did not occur
        for tr in g.history:
            if not self.y_holds(c, tr):
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        if tr.zero_delta or not tr.displacements:
            return []
        claims = []
        act = str(tr.action_id).upper()
        for idx, d in enumerate(tr.displacements):
            if isinstance(d, dict) and ("dy" in d or "dx" in d):
                dy = int(d.get("dy", 0))
                dx = int(d.get("dx", 0))
                cid = f"claim_eff_{act}_{dy}_{dx}"
                claims.append(
                    Claim(
                        id=cid,
                        kind=self.name,
                        subject=(act,),
                        predicate={"dy": dy, "dx": dx},
                        scope="game",
                    )
                )
        return claims


class ControlledKind:
    """Evaluates whether a directed command moves the specific actor entity."""
    name = "controlled"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_act = c.subject[0] if c.subject else ""
        return str(tr.action_id).upper() == str(target_act).upper()

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        if tr.zero_delta:
            return False
        target_sig = c.predicate.get("sig")
        return tr.actor_sig == target_sig

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        target_sig = c.predicate.get("sig")
        for tr in g.history:
            if tr.actor_sig is not None and tr.actor_sig != target_sig:
                return True
            if tr.zero_delta:
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        if tr.zero_delta or tr.actor_sig is None:
            return []
        act = str(tr.action_id).upper()
        cid = f"claim_ctrl_{act}_{tr.actor_sig[0]}_{tr.actor_sig[1]}"
        return [
            Claim(
                id=cid,
                kind=self.name,
                subject=(act,),
                predicate={"sig": tr.actor_sig},
                scope="game",
            )
        ]


class PassabilityKind:
    """Evaluates whether an entity signature blocks movement or is passable."""
    name = "passability"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_sig = c.subject[0] if c.subject else None
        return target_sig in tr.touched_sigs

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        blocks = bool(c.predicate.get("blocks", True))
        # If blocks=True, motion is stopped (zero delta)
        return tr.zero_delta if blocks else (not tr.zero_delta)

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        blocks = bool(c.predicate.get("blocks", True))
        for tr in g.history:
            if blocks and not tr.zero_delta:
                return True
            if not blocks and tr.zero_delta:
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        claims = []
        for sig in tr.touched_sigs:
            cid = f"claim_pass_{sig[0]}_{sig[1]}_{tr.zero_delta}"
            claims.append(
                Claim(
                    id=cid,
                    kind=self.name,
                    subject=(sig,),
                    predicate={"blocks": tr.zero_delta},
                    scope="game",
                )
            )
        return claims


class LethalKind:
    """Evaluates whether contact with an entity signature causes GAME_OVER."""
    name = "lethal"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_sig = c.subject[0] if c.subject else None
        return target_sig in tr.touched_sigs

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        is_lethal = bool(c.predicate.get("lethal", True))
        is_terminal_death = (tr.terminal == "GAME_OVER")
        return is_terminal_death if is_lethal else (not is_terminal_death)

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        # A contrast witness for lethal is having at least one non-fatal contact or fatal contact
        is_lethal = bool(c.predicate.get("lethal", True))
        for tr in g.history:
            if is_lethal and tr.terminal != "GAME_OVER":
                return True
            if not is_lethal and tr.terminal == "GAME_OVER":
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        claims = []
        is_death = (tr.terminal == "GAME_OVER")
        for sig in tr.touched_sigs:
            cid = f"claim_lethal_{sig[0]}_{sig[1]}_{is_death}"
            claims.append(
                Claim(
                    id=cid,
                    kind=self.name,
                    subject=(sig,),
                    predicate={"lethal": is_death},
                    scope="game",
                )
            )
        return claims


class CollectibleKind:
    """Evaluates whether an entity signature is collected (disappears upon contact)."""
    name = "collectible"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_sig = c.subject[0] if c.subject else None
        return target_sig in tr.touched_sigs

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        # Check if any object of this signature disappeared in after_grid
        target_sig = c.subject[0] if c.subject else None
        target_col = target_sig[0] if target_sig else None
        if target_col is None:
            return None
        before_cnt = sum(row.count(target_col) for row in tr.before_grid)
        after_cnt = sum(row.count(target_col) for row in tr.after_grid)
        disappeared = (after_cnt < before_cnt)
        is_collectible = bool(c.predicate.get("collectible", True))
        return disappeared if is_collectible else (not disappeared)

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        for tr in g.history:
            if not tr.zero_delta:
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        claims = []
        for sig in tr.touched_sigs:
            target_col = sig[0]
            before_cnt = sum(row.count(target_col) for row in tr.before_grid)
            after_cnt = sum(row.count(target_col) for row in tr.after_grid)
            if after_cnt < before_cnt:
                cid = f"claim_collect_{sig[0]}_{sig[1]}"
                claims.append(
                    Claim(
                        id=cid,
                        kind=self.name,
                        subject=(sig,),
                        predicate={"collectible": True},
                        scope="game",
                    )
                )
        return claims


class TriggerKind:
    """Evaluates whether contact between two entities triggers a state mutation."""
    name = "trigger"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        target_pair = c.subject
        if len(target_pair) >= 2:
            return target_pair[0] in tr.touched_sigs and target_pair[1] in tr.touched_sigs
        return None

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        mutates = bool(c.predicate.get("mutates", True))
        return (not tr.zero_delta) if mutates else tr.zero_delta

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        mutates = bool(c.predicate.get("mutates", True))
        for tr in g.history:
            if mutates and tr.zero_delta:
                return True
            if not mutates and not tr.zero_delta:
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        return []


class ClickEffectKind:
    """Evaluates whether ACTION6 / clicking mutates state."""
    name = "click_effect"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        return str(tr.action_id).upper() in ("ACTION6", "CLICK")

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        mutates = bool(c.predicate.get("mutates", True))
        return (not tr.zero_delta) if mutates else tr.zero_delta

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        for tr in g.history:
            if not self.y_holds(c, tr):
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        if str(tr.action_id).upper() in ("ACTION6", "CLICK"):
            return [
                Claim(
                    id=f"claim_click_mutate_{not tr.zero_delta}",
                    kind=self.name,
                    subject=("ACTION6",),
                    predicate={"mutates": not tr.zero_delta},
                    scope="game",
                )
            ]
        return []


class UndoExactKind:
    """Evaluates whether ACTION7 / undo exactly restores state."""
    name = "undo_exact"

    def x_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        return str(tr.action_id).upper() in ("ACTION7", "UNDO")

    def y_holds(self, c: Claim, tr: TransitionRecord) -> bool | None:
        restores = bool(c.predicate.get("restores", True))
        is_exact = bool(tr.context_features.get("undo_exact", True))
        return is_exact if restores else (not is_exact)

    def contrast_exists(self, c: Claim, g: ClaimGraph) -> bool:
        for tr in g.history:
            if str(tr.action_id).upper() not in ("ACTION7", "UNDO"):
                return True
        return False

    def induce(self, tr: TransitionRecord, g: ClaimGraph) -> list[Claim]:
        if str(tr.action_id).upper() in ("ACTION7", "UNDO"):
            return [
                Claim(
                    id="claim_undo_exact",
                    kind=self.name,
                    subject=("ACTION7",),
                    predicate={"restores": True},
                    scope="game",
                )
            ]
        return []


KINDS: dict[str, ClaimKind] = {
    "action_effect": ActionEffectKind(),
    "controlled": ControlledKind(),
    "passability": PassabilityKind(),
    "lethal": LethalKind(),
    "collectible": CollectibleKind(),
    "trigger": TriggerKind(),
    "click_effect": ClickEffectKind(),
    "undo_exact": UndoExactKind(),
}


# =============================================================================
# Claim Status Evaluator and Context Splitter
# =============================================================================

def split_by_context(c: Claim, g: ClaimGraph, cfg: ClaimConfig) -> list[GraphEvent]:
    """Deterministically partition a contested claim into two contextual child claims."""
    S = [e.tid for e in c.support if e.result is CheckResult.HOLDS_DIRECT]
    C = [e.tid for e in c.counter]
    fs = [g.context(t) for t in S]
    fc = [g.context(t) for t in C]

    cands = find_separating_features(fs, fc)
    best = select_best_splitting_feature(cands)
    if best is None:
        c.status = ClaimStatus.UNDECIDED
        c.unexplained = True
        hints = generate_splitting_hints(c.id, c.kind, [], unexplained=True)
        detail = hints[0] if hints else "No separating feature found"
        return [GraphEvent("UNEXPLAINED", c.id, C[-1] if C else -1, detail)]

    f, v = best
    child_s = c.derive(condition={f: v}, origin="refined", evidence_tids=S)
    child_c = c.derive(condition={"not": {f: v}}, origin="refined", evidence_tids=C)

    c.status = ClaimStatus.ZERO  # Superseded parent
    hints = generate_splitting_hints(c.id, c.kind, cands, unexplained=False)
    detail = hints[0] if hints else f"Split on {f}=={v}"
    events = [GraphEvent("SPLIT", c.id, C[-1] if C else -1, detail)]
    events.extend(g.add(child_s))
    events.extend(g.add(child_c))

    if meets_plus(child_s, g, cfg):
        child_s.status = ClaimStatus.PLUS
        events.append(GraphEvent("PLUS", child_s.id, C[-1] if C else -1, "Graduated child after context split"))

    return events


def has_origin(c: Claim) -> bool:
    """True if condition x was observed (via origin evidence or induced/refined/carried status)."""
    return any(e.is_origin for e in c.support) or c.origin in ("induced", "refined", "carried", "proposed_llm")


def meets_plus(c: Claim, g: ClaimGraph, cfg: ClaimConfig) -> bool:
    """Validate all criteria for PLUS status under Brusentsov logic."""
    kind = KINDS.get(c.kind)
    if kind is None:
        return False

    direct = [e for e in c.support if e.result is CheckResult.HOLDS_DIRECT and not e.is_origin]
    # Criterion 1: Excluded member xy'_0 was never observed
    if c.counter:
        return False
    # Criterion 2: Condition x was observed
    if not has_origin(c):
        return False
    # Criterion 3: Threshold of independent direct evidence
    min_direct = cfg.n_direct.get(c.kind, 2)
    min_levels = cfg.n_levels.get(c.kind, 1)
    if len(direct) < min_direct:
        return False
    if len({e.level for e in direct}) < min_levels:
        return False
    # Criterion 4: Contrast witness must exist (y' was observed somewhere in the game)
    if not kind.contrast_exists(c, g):
        c.awaiting_contrast = True
        return False

    c.awaiting_contrast = False
    return True


def judge_update(c: Claim, tr: TransitionRecord, g: ClaimGraph, cfg: ClaimConfig) -> list[GraphEvent]:
    """Update claim status on a single observed transition."""
    if c.status is ClaimStatus.ZERO:
        return []

    kind = KINDS.get(c.kind)
    if kind is None:
        return []

    r = check_claim(kind, c, tr)
    if r in (CheckResult.NA, CheckResult.UNOBSERVABLE):
        return []  # x'y and unobservable transitions do not alter belief

    ev = Evidence(tid=tr.tid, level=tr.level, result=r)
    if r is CheckResult.VIOLATED:
        c.counter.append(ev)
    else:
        c.support.append(ev)

    direct = [e for e in c.support if e.result is CheckResult.HOLDS_DIRECT and not e.is_origin]

    # Contradiction when prior support exists -> split by context
    if direct and c.counter:
        return split_by_context(c, g, cfg)

    # Graduation to PLUS
    if r is not CheckResult.VIOLATED and c.status is ClaimStatus.UNDECIDED and meets_plus(c, g, cfg):
        c.status = ClaimStatus.PLUS
        return [GraphEvent("PLUS", c.id, tr.tid)]

    # Demotion to MINUS (pure counterexamples without direct support)
    if r is CheckResult.VIOLATED and not direct and len(c.counter) >= cfg.n_minus:
        c.status = ClaimStatus.MINUS
        return [GraphEvent("MINUS", c.id, tr.tid)]

    return []


def create_transition_record(
    tid: int,
    level: int,
    action_id: str,
    action_data: dict[str, Any] | None = None,
    before_grid: list[list[int]] | None = None,
    after_grid: list[list[int]] | None = None,
    terminal: str | None = None,
    zero_delta: bool | None = None,
    displacements: list[dict[str, Any]] | None = None,
    context_features: dict[str, Any] | None = None,
    actor_sig: tuple[int, int] | None = None,
    touched_sigs: set[tuple[int, int]] | None = None,
) -> TransitionRecord:
    """Convenience factory to construct a factual TransitionRecord."""
    b_grid = [list(r) for r in before_grid] if before_grid else []
    a_grid = [list(r) for r in after_grid] if after_grid else []

    if zero_delta is None:
        zero_delta = (b_grid == a_grid) if (b_grid and a_grid) else False

    disp_list = list(displacements or [])
    if not disp_list and b_grid and a_grid and not zero_delta:
        H = min(len(b_grid), len(a_grid))
        W = min(len(b_grid[0]), len(a_grid[0])) if H > 0 else 0
        diff_colors = set()
        for r in range(H):
            for c in range(W):
                if b_grid[r][c] != a_grid[r][c]:
                    diff_colors.add(b_grid[r][c])
                    diff_colors.add(a_grid[r][c])
        diff_colors.discard(0)
        for col in sorted(diff_colors):
            b_pixels = [(r, c) for r in range(H) for c in range(W) if b_grid[r][c] == col]
            a_pixels = [(r, c) for r in range(H) for c in range(W) if a_grid[r][c] == col]
            if b_pixels and a_pixels and len(b_pixels) == len(a_pixels):
                dy = a_pixels[0][0] - b_pixels[0][0]
                dx = a_pixels[0][1] - b_pixels[0][1]
                if all((r + dy, c + dx) in a_pixels for r, c in b_pixels):
                    disp_list.append({"dy": dy, "dx": dx, "color": col})
                    if actor_sig is None:
                        actor_sig = (col, 0)

    if actor_sig is None and disp_list:
        actor_sig = (disp_list[0].get("color", 0), 0)

    t_sigs = set(touched_sigs or set())
    ctx = dict(context_features or {})
    if b_grid and not all(k in ctx for k in ("target_color", "dy", "dx")):
        act_col = actor_sig[0] if actor_sig else None
        extracted = extract_transition_features(
            before_grid=b_grid,
            action=action_id,
            after_grid=a_grid,
            step_index=tid,
            actor_color=act_col,
            result_flags=ctx,
        )
        extracted.update(ctx)
        ctx = extracted
    elif "blocked" not in ctx:
        ctx["blocked"] = zero_delta

    return TransitionRecord(
        tid=tid,
        level=level,
        action_id=action_id,
        action_data=dict(action_data or {}),
        before_grid=b_grid,
        after_grid=a_grid,
        terminal=terminal,
        zero_delta=zero_delta,
        displacements=disp_list,
        context_features=ctx,
        actor_sig=actor_sig,
        touched_sigs=t_sigs,
    )


# =============================================================================
# ClaimGraph Master Collection
# =============================================================================

class ClaimGraph:
    """Manages the full network of empirical world laws across game levels."""

    def __init__(self, cfg: ClaimConfig | None = None) -> None:
        self.cfg = cfg or ClaimConfig()
        self.claims: dict[str, Claim] = {}
        self._by_key: dict[tuple, str] = {}
        self.history: list[TransitionRecord] = []
        self._contexts: dict[int, dict[str, Any]] = {}

    def add(self, *claims: Claim) -> list[GraphEvent]:
        """Add one or more claims with deduplication by key."""
        events: list[GraphEvent] = []
        for c in claims:
            k = c.key()
            if k in self._by_key:
                existing = self.claims[self._by_key[k]]
                # Merge evidence
                existing.support.extend(c.support)
                existing.counter.extend(c.counter)
                continue
            self.claims[c.id] = c
            self._by_key[k] = c.id
        return events

    def get(self, claim_id: str) -> Claim | None:
        return self.claims.get(claim_id)

    def context(self, tid: int) -> dict[str, Any]:
        """Retrieve recorded context features for a transition."""
        return self._contexts.get(tid, {})

    def active_claims(self) -> list[Claim]:
        """Claims currently usable by planner (PLUS or viable UNDECIDED)."""
        return [
            c for c in self.claims.values()
            if c.status in (ClaimStatus.PLUS, ClaimStatus.UNDECIDED) and not c.counter
        ]

    def confirmed_claims(self) -> list[Claim]:
        """Claims strictly verified as necessary laws (PLUS)."""
        return [c for c in self.claims.values() if c.status is ClaimStatus.PLUS]

    def judge_transition(self, tr: TransitionRecord) -> list[GraphEvent]:
        """Execute 3-valued judgment across all claims and induce new ones if unexplained."""
        self.history.append(tr)
        self._contexts[tr.tid] = dict(tr.context_features)
        events: list[GraphEvent] = []

        explained = False
        for c in list(self.claims.values()):
            evs = judge_update(c, tr, self, self.cfg)
            events.extend(evs)
            kind = KINDS.get(c.kind)
            if kind and kind.x_holds(c, tr) and kind.y_holds(c, tr):
                explained = True

        # If transition had an observable effect not explained by any existing claim, induce
        if not tr.zero_delta and not explained:
            for kind in KINDS.values():
                induced = kind.induce(tr, self)
                for inc in induced:
                    inc.support.append(Evidence(tid=tr.tid, level=tr.level, result=CheckResult.HOLDS_DIRECT, is_origin=True))
                    self.add(inc)

        return events

    def carry_to_new_level(self) -> list[Claim]:
        """Carry forward verified game-scoped laws to the new level."""
        carried = [
            c for c in self.claims.values()
            if c.scope == "game"
            and c.status in (ClaimStatus.PLUS, ClaimStatus.UNDECIDED)
            and not c.counter
        ]
        self.claims = {c.id: c for c in carried}
        self._by_key = {c.key(): c.id for c in carried}
        return carried

    def project_entity_roles(self) -> dict[int, str]:
        """Project confirmed and active claims into entity roles (Contract 01, item 3).

        Roles are strictly derived from confirmed (PLUS) and active (UNDECIDED without counter) claims:
        - lethal with kills=True -> hazard
        - collectible with goal=True or kind == target -> target
        - collectible with goal=False -> collectible
        - passability with blocks=True -> obstacle
        - controlled -> actor
        - trigger -> portal
        """
        roles: dict[int, str] = {}
        for c in self.active_claims():
            color = None
            if isinstance(c.subject, tuple) and len(c.subject) >= 1:
                first = c.subject[0]
                if isinstance(first, int):
                    color = first
            if color is None or color < 0 or color > 15:
                continue

            if c.kind == "lethal" and c.predicate.get("kills", True):
                roles[color] = "hazard"
            elif c.kind in ("target", "victory"):
                roles[color] = "target"
            elif c.kind == "collectible":
                if c.predicate.get("goal", False) or c.predicate.get("is_victory", False):
                    roles[color] = "target"
                else:
                    roles[color] = "collectible"
            elif c.kind == "passability" and c.predicate.get("blocks", True):
                if color not in roles or roles[color] not in ("hazard", "target", "actor"):
                    roles[color] = "obstacle"
            elif c.kind == "controlled":
                roles[color] = "actor"
            elif c.kind == "trigger":
                if c.predicate.get("portal", False) or c.predicate.get("teleport", False):
                    roles[color] = "portal"
        return roles
