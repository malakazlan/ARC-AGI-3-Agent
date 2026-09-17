"""World model: what each action did, as a transition graph over masked state keys.

Interface only (Phase 2). The graph explorer baseline (Phase 3) implements it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Transition:
    """One observed (state, action) -> state edge."""

    src_key: str
    action_id: int
    x: int | None
    y: int | None
    dst_key: str
    changed_cells: int
    game_over: bool
    level_up: bool


class TransitionGraph(Protocol):
    def record(self, transition: Transition) -> None: ...
    def untested_actions(self, state_key: str, legal: list[int]) -> list[int]: ...
    def neighbours(self, state_key: str) -> list[Transition]: ...
    def size(self) -> int: ...
