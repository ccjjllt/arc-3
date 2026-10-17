"""ARC-AGI-3 Hybrid Agent Package (UND).

Blends Duck runtime execution harness with LCLD Brusentsov formal world model logic.
"""
from __future__ import annotations

from inference.und.types import (
    ActionCategory,
    ActionDeclaration,
    AtomicProposition,
    BoundingBox,
    Centroid,
    ClaimStatus,
    CoordinateCandidate,
    FrameDTO,
    Grid2D,
    PropositionSet,
    TransitionRecord,
    Verdict,
)

__version__ = "0.1.0"

__all__ = [
    "ActionCategory",
    "ActionDeclaration",
    "AtomicProposition",
    "BoundingBox",
    "Centroid",
    "ClaimStatus",
    "CoordinateCandidate",
    "FrameDTO",
    "Grid2D",
    "PropositionSet",
    "TransitionRecord",
    "Verdict",
    "__version__",
]
