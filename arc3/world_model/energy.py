"""Energy as a resource: how much of the bar is left, how fast an action drains it.

The bar's cells come from the countdown mask; a cell is "full" when it shows the value it had
at the level start and "drained" when it shows its end-of-attempt value. Drops between
consecutive frames give the per-action rate (ls20 level 1 drains one cell per action, level 2
about two). A rise is a refill.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

Cell = tuple[int, int]


class EnergyModel:
    HISTORY = 20

    def __init__(self, full: dict[Cell, int], drained: dict[Cell, int]) -> None:
        self.full = dict(full)
        self.drained = dict(drained)
        self.readings: list[int] = []   # remaining per observed action, since the last rise
        self.last: int | None = None
        self.refills = 0
        self._rate: float | None = None

    @property
    def capacity(self) -> int:
        return len(self.full)

    @property
    def full_colour(self) -> int | None:
        """The bar's colour when full: what a refill object is most likely drawn in."""
        if not self.full:
            return None
        return Counter(self.full.values()).most_common(1)[0][0]

    def remaining(self, grid: np.ndarray) -> int:
        h, w = grid.shape
        return sum(1 for (y, x), v in self.full.items() if y < h and x < w and int(grid[y, x]) == v)

    def observe(self, grid: np.ndarray) -> None:
        now = self.remaining(grid)
        if self.last is not None and now > self.last:
            self.refills += 1
            self.readings = []
        if self.last is not None or not self.readings:
            self.readings = (self.readings + [now])[-self.HISTORY:]
        stretch = self.readings
        while len(stretch) >= 2 and stretch[-1] == 0 and stretch[-2] == 0:
            stretch = stretch[:-1]            # an empty bar stays empty: not a measurement
        if len(stretch) >= 3 and stretch[0] > stretch[-1]:
            self._rate = (stretch[0] - stretch[-1]) / (len(stretch) - 1)
        self.last = now

    def forget_last(self) -> None:
        """After a restart the next reading starts a new stretch."""
        self.last = None
        self.readings = []

    @property
    def rate(self) -> float:
        """Bar cells lost per action (1 until measured)."""
        return self._rate if self._rate else 1.0

    def actions_left(self, grid: np.ndarray) -> float:
        return self.remaining(grid) / max(self.rate, 1e-6)

    def affordable(self, actions: int, grid: np.ndarray, margin: int = 1) -> bool:
        return (actions + margin) * self.rate <= self.remaining(grid)
