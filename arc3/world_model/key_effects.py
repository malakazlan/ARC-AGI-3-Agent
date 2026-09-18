"""Effects of non-move keys, generalised by the avatar's appearance.

A rotate key turns an L into a J wherever the L is; a toggle flips a colour. The effect is
stored as a relative diff anchored at the avatar (or at the grid origin when there is no
avatar), keyed by (key, avatar template). Consistent k times => global, and then the next
frame can be predicted instead of executed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from arc3.world_model.effects import Effect, RelativeDiff

Cells = frozenset[tuple[int, int]]
Template = tuple[tuple[int, int, int], ...]  # ((dy, dx, colour), ...) relative to the anchor


def _anchor(cells: Cells) -> tuple[int, int]:
    return min(cells) if cells else (0, 0)


def _template(cells: Cells, grid: np.ndarray) -> Template:
    ay, ax = _anchor(cells)
    return tuple(sorted((y - ay, x - ax, int(grid[y, x])) for (y, x) in cells))


@dataclass
class KeyEffects:
    """Per (key, avatar template): the relative effect of pressing the key."""

    k: int = 3
    history: dict[tuple, list[RelativeDiff]] = field(default_factory=dict)

    def _key(self, key: int, cells: Cells, grid: np.ndarray) -> tuple:
        return (int(key), _template(cells, grid))

    def record(self, key: int, cells: Cells, before: np.ndarray, after: np.ndarray) -> None:
        if before.shape != after.shape:
            return
        ay, ax = _anchor(cells)
        ys, xs = np.nonzero(before != after)
        diff: RelativeDiff = tuple(sorted((int(y - ay), int(x - ax), int(after[y, x])) for y, x in zip(ys, xs)))
        seen = self.history.setdefault(self._key(key, cells, before), [])
        seen.append(diff)
        del seen[:-max(self.k, 5)]

    def global_effect(self, key: int, cells: Cells, grid: np.ndarray) -> Effect | None:
        seen = self.history.get(self._key(key, cells, grid), [])
        if len(seen) < self.k:
            return None
        recent = seen[-self.k:]
        if any(d != recent[0] for d in recent):
            return None
        return Effect(changed=bool(recent[0]), diff=recent[0])

    def predict(self, key: int, cells: Cells, grid: np.ndarray) -> np.ndarray | None:
        effect = self.global_effect(key, cells, grid)
        if effect is None:
            return None
        out = grid.copy()
        ay, ax = _anchor(cells)
        h, w = grid.shape
        for dy, dx, colour in effect.diff:
            y, x = ay + dy, ax + dx
            if 0 <= y < h and 0 <= x < w:
                out[y, x] = colour
        return out
