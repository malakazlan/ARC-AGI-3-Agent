"""Cross-level and cross-game memory: what to keep when a level or game changes.

Interface only (Phase 2). Phase 4 of the roadmap fills it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from arc3.goal import GoalHypothesis


@dataclass
class LevelMemory:
    """What a finished level taught us, reusable on the next one."""

    level_index: int
    winning_path: list[tuple[int, int | None, int | None]] = field(default_factory=list)
    goal: GoalHypothesis | None = None
    action_effects: dict[int, str] = field(default_factory=dict)
