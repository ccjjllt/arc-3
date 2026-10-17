"""CONTRACT: Domain data types and core structures for the ARC-AGI-3 Hybrid Agent (Rules 02, 04).

All data types defined here are pure, immutable where appropriate, and decoupled
from any LLM or external runtime state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Iterator

Grid2D = list[list[int]]
PlanningObjectId = str
PlanningAlias = str


# =============================================================================
# 1. Spatial and Geometry Types
# =============================================================================

@dataclass(frozen=True)
class BoundingBox:
    """Bounding box defined by inclusive row and column coordinates."""

    min_row: int
    min_col: int
    max_row: int
    max_col: int

    @property
    def height(self) -> int:
        return self.max_row - self.min_row + 1

    @property
    def width(self) -> int:
        return self.max_col - self.min_col + 1

    @property
    def area(self) -> int:
        return self.height * self.width

    def to_dict(self) -> dict[str, int]:
        return {
            "min_row": self.min_row,
            "min_col": self.min_col,
            "max_row": self.max_row,
            "max_col": self.max_col,
            "height": self.height,
            "width": self.width,
        }


@dataclass(frozen=True)
class Centroid:
    """Centroid of an object or region in row/column coordinates."""

    row: float
    col: float

    def to_dict(self) -> dict[str, float]:
        return {"row": round(self.row, 2), "col": round(self.col, 2)}


@dataclass(frozen=True)
class CoordinateCandidate:
    """A spatial point candidate grounded on the PlanningSet."""

    candidate_id: str
    x: int  # column index (0-indexed)
    y: int  # row index (0-indexed)
    source_type: str  # e.g., "centroid", "corner_tl", "corner_br", "grid_center"
    object_id: str | None = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "x": self.x,
            "y": self.y,
            "source_type": self.source_type,
            "object_id": self.object_id,
            "label": self.label,
        }


# =============================================================================
# 2. Action Declarations and Categories (Rule 04, Section 2)
# =============================================================================

class ActionCategory(str, Enum):
    """Category of action emission for telemetry and budget accounting."""

    MANUAL = "manual"
    PROBE = "probe"
    EXPLORE = "explore"
    EXEC_OK = "exec_ok"
    EXEC_FAILED = "exec_failed"
    RESET = "reset"
    UNDO = "undo"
    FALLBACK = "fallback"
    EVIDENCE_PROBE = "evidence_probe"
    RECOVER = "recover"
    DETERMINISM = "determinism"


@dataclass(frozen=True)
class ActionDeclaration:
    """Declaration of an intended environment action."""

    action_id: str  # "ACTION1" .. "ACTION7", "RESET", or Duck name "UP", "DOWN", ...
    data: dict[str, Any] = field(default_factory=dict)
    reasoning: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.action_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.action_id,
            "action_id": self.action_id,
            "data": dict(self.data),
            "reasoning": dict(self.reasoning),
        }


# =============================================================================
# 3. Brusentsov Ternary Logic Verdicts and Claim Statuses (Rules 02 & 04)
# =============================================================================

class Verdict(str, Enum):
    """Ternary Brusentsov logic verdict: (+, -, 0)."""

    FOLLOW = "+"
    CONTRADICT = "-"
    IDLE = "idle"  # Replaces legacy OMIT; indicates vacuous truth / lack of stimulus
    ABSTAIN = "abstain"
    UNKNOWN = "unknown"


class ClaimStatus(str, Enum):
    """Epistemic status of a claim in the ClaimGraph (Rule 04, Section 6)."""

    VERIFIED = "verified"
    HYPOTHESIZED = "hypothesized"
    EXCLUDED = "excluded"
    IDLE = "idle"


# =============================================================================
# 4. Atomic Propositions and Proposition Sets
# =============================================================================

REGISTERED_PROPOSITION_FAMILIES = frozenset({
    "object_identity",
    "attribute_delta",
    "metric_sign",
    "relation_existence",
    "action_surface",
    "terminal_metadata",
    "affordance_flag",
    "spatial_position",
    "area_conservation",
    "cumulative_motion",
    "shape_stability",
})

PropositionFamily = str


@dataclass(frozen=True)
class AtomicProposition:
    """An atomic proposition grounded on discrete planning identifiers.

    Raw grid pixels are never propositions. Only registered families are valid.
    """

    family: PropositionFamily
    subject_id: str
    predicate: str
    value: Any = None
    secondary_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.value, (dict, list, set)):
            object.__setattr__(self, "value", str(self.value))
        if self.family not in REGISTERED_PROPOSITION_FAMILIES:
            raise ValueError(
                f"Unknown proposition family {self.family!r}. Must be one of {REGISTERED_PROPOSITION_FAMILIES}"
            )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "family": self.family,
            "subject_id": self.subject_id,
            "predicate": self.predicate,
        }
        if self.value is not None:
            out["value"] = self.value
        if self.secondary_id is not None:
            out["secondary_id"] = self.secondary_id
        return out


@dataclass(frozen=True)
class PropositionSet:
    """An immutable set of AtomicPropositions."""

    propositions: frozenset[AtomicProposition] = field(default_factory=frozenset)

    @classmethod
    def empty(cls) -> PropositionSet:
        return cls(frozenset())

    @classmethod
    def from_iterable(cls, items: Iterable[AtomicProposition]) -> PropositionSet:
        return cls(frozenset(items))

    def union(self, other: PropositionSet) -> PropositionSet:
        return PropositionSet(self.propositions | other.propositions)

    def intersection(self, other: PropositionSet) -> PropositionSet:
        return PropositionSet(self.propositions & other.propositions)

    def difference(self, other: PropositionSet) -> PropositionSet:
        return PropositionSet(self.propositions - other.propositions)

    def filter_family(self, family: str) -> PropositionSet:
        return PropositionSet(frozenset(p for p in self.propositions if p.family == family))

    def __contains__(self, item: AtomicProposition) -> bool:
        return item in self.propositions

    def __len__(self) -> int:
        return len(self.propositions)

    def __iter__(self) -> Iterator[AtomicProposition]:
        return iter(self.propositions)

    def to_list(self) -> list[dict[str, Any]]:
        return [
            p.to_dict()
            for p in sorted(
                self.propositions, key=lambda p: (p.family, p.subject_id, p.predicate)
            )
        ]


# =============================================================================
# 5. Transition and Frame DTOs
# =============================================================================

@dataclass(frozen=True)
class FrameDTO:
    """Snapshot of a single frame from the environment."""

    grid: Grid2D
    level: int = 0
    step: int = 0
    score: int = 0

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable transition record observed between environment steps."""

    index: int
    level: int
    before_grid: Grid2D
    action: ActionDeclaration
    after_grid: Grid2D
    result_flags: dict[str, Any] = field(default_factory=dict)
    category: str = ActionCategory.MANUAL.value
