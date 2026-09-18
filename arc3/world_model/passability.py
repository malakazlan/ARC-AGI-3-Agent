"""What the avatar can walk into, learned per target-cell colour and generalised by colour.

Votes come from executed key presses once the avatar and the key's vector are known:
the avatar moved => the colours it entered pass; it stayed => the colours ahead block; it
died (not by expiry) => the colours ahead kill. A contradiction (prediction failed) resets
the colour to unknown so moving walls and opening doors get re-learned.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DECIDING_VOTES = 3
KILL_VOTES = 1  # one death is enough for a player

Cells = frozenset[tuple[int, int]]
Prediction = tuple[str, Cells]  # ("moved", new cells) or ("blocked", same cells)


@dataclass
class ColourVotes:
    passes: int = 0
    blocks: int = 0
    kills: int = 0


@dataclass
class PassabilityModel:
    votes: dict[int, ColourVotes] = field(default_factory=dict)

    def vote(self, colour: int, kind: str) -> None:
        v = self.votes.setdefault(int(colour), ColourVotes())
        setattr(v, kind, getattr(v, kind) + 1)

    def contradict(self, colour: int) -> None:
        self.votes.pop(int(colour), None)

    def lethal(self, colour: int) -> bool | None:
        v = self.votes.get(int(colour))
        if v is None or (v.kills == 0 and v.passes + v.blocks < DECIDING_VOTES):
            return None
        return v.kills >= KILL_VOTES and v.kills >= v.passes

    def passable(self, colour: int) -> bool | None:
        v = self.votes.get(int(colour))
        if v is None:
            return None
        if v.kills >= KILL_VOTES and v.kills >= v.passes:
            return False
        total = v.passes + v.blocks
        if total < DECIDING_VOTES:
            return None
        if v.passes >= 2 * v.blocks:
            return True
        if v.blocks >= 2 * v.passes:
            return False
        return None  # mixed evidence: unknown

    def known(self, colour: int) -> bool:
        return self.passable(colour) is not None


def cells_ahead(cells: Cells, vector: tuple[int, int]) -> Cells:
    moved = frozenset((y + vector[0], x + vector[1]) for (y, x) in cells)
    return moved - cells


def predict_move(grid: np.ndarray, cells: Cells, vector: tuple[int, int], model: PassabilityModel,
                 origin: Cells = frozenset()) -> Prediction | None:
    """Predict a key press: moved, blocked, or None when a colour ahead is still unknown.

    `origin` cells (where the avatar stood when the grid was observed) count as passable:
    the colour underneath is unknown but we were standing there.
    """
    h, w = grid.shape
    ahead = cells_ahead(cells, vector)
    if any(not (0 <= y < h and 0 <= x < w) for (y, x) in ahead):
        return ("blocked", cells)
    verdicts = []
    for (y, x) in ahead:
        if (y, x) in origin:
            verdicts.append(True)
            continue
        verdicts.append(model.passable(int(grid[y, x])))
    if any(v is False for v in verdicts):
        return ("blocked", cells)
    if any(v is None for v in verdicts):
        return None
    return ("moved", frozenset((y + vector[0], x + vector[1]) for (y, x) in cells))
