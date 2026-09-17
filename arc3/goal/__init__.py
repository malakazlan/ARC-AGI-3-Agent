"""Goal inference: what changed right before a level was won, and progress signals.

Interface only (Phase 2). Phase 4 of the roadmap implements win-signal analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GoalHypothesis:
    """A guess at the win condition, with the evidence that produced it."""

    kind: str  # e.g. "object_reaches_region", "colors_match", "count_reached"
    confidence: float
    evidence: dict = field(default_factory=dict)
