"""Toys for the reach and collect goal templates (design v2 T2, T3/T5).

12x12, background 0, walls colour 2. Avatar colour 1 (1 cell), keys 1-4 move one cell.
Target: a 3x3 frame of colour 6 open at the bottom (a doorway); stepping onto its centre wins.
`collect=n`: n dots of colour 9 that vanish when the avatar steps on them; the target only
accepts the avatar once every dot is gone (before that, the centre is just floor).
`decoys`: extra rare objects that do nothing (a colour-4 cell, a colour-7 cell), so the agent
must verify candidates instead of guessing.
`conveyor=(entry, exit)`: stepping onto the colour-8 entry cell lands the avatar on the exit
cell in the same step (ls20's white strips carry the avatar 20 cells for one press).
"""
from __future__ import annotations

import numpy as np

from arc3.agent import Observation

MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
TARGET_BOX = (1, 8, 3, 10)      # frame rows 1-3, cols 8-10; centre (2, 9)
START = (9, 2)
DOTS = ((9, 8), (3, 3), (6, 6))


class ReachToy:
    def __init__(self, collect: int = 0, decoys: bool = True, levels: int = 1,
                 conveyor: tuple[tuple[int, int], tuple[int, int]] | None = None) -> None:
        self.collect = collect
        self.decoys = decoys
        self.levels = levels
        # (entry cell, exit cell): stepping on the entry lands on the exit
        self.conveyor = (tuple(conveyor[0]), tuple(conveyor[1])) if conveyor is not None else None
        self.levels_completed = 0
        self.state = "NOT_PLAYED"
        self.steps = 0
        self.dots_left: set[tuple[int, int]] = set()
        self.grid = self._layout()

    def _layout(self) -> np.ndarray:
        g = np.zeros((12, 12), dtype=np.int8)
        g[5, 0:9] = 2                                 # a wall with a gap on the right
        if self.conveyor is not None:
            g[5, :] = 2                               # no gap: the conveyor is the only way across
        y0, x0, y1, x1 = TARGET_BOX
        g[y0:y1 + 1, x0:x1 + 1] = 6
        g[2, 9] = 0
        g[3, 9] = 0                                   # the frame is open at the bottom: a doorway
        if self.decoys:
            g[7, 10] = 4
            g[10, 5] = 7
        if self.conveyor is not None:
            g[self.conveyor[0]] = 8         # a colour-8 strip: the conveyor's entry
        self.dots_left = set(DOTS[:self.collect])
        for (y, x) in self.dots_left:
            g[y, x] = 9
        g[START] = 1
        return g

    def observe(self) -> Observation:
        grid = self.grid.copy() if self.state == "NOT_FINISHED" else None
        return Observation(self.state, self.levels_completed, self.levels, grid, [1, 2, 3, 4])

    def apply(self, action_id: int, x=None, y=None) -> Observation:
        self.steps += 1
        if action_id == 0:
            self.grid = self._layout()
            self.state = "NOT_FINISHED"
            return self.observe()
        if self.state != "NOT_FINISHED" or action_id not in MOVES:
            return self.observe()
        dy, dx = MOVES[action_id]
        py, px = map(int, np.argwhere(self.grid == 1)[0])
        ny, nx = py + dy, px + dx
        if not (0 <= ny < 12 and 0 <= nx < 12):
            return self.observe()
        cell = int(self.grid[ny, nx])
        if (ny, nx) == (2, 9):
            if not self.dots_left:
                self.levels_completed += 1
                self.state = "WIN" if self.levels_completed >= self.levels else "NOT_FINISHED"
                if self.state == "NOT_FINISHED":
                    self.grid = self._layout()
                return self.observe()
        elif cell == 9:
            self.dots_left.discard((ny, nx))
        elif self.conveyor is not None and (ny, nx) == self.conveyor[0]:
            self.grid[py, px] = 0
            self.grid[self.conveyor[1]] = 1             # carried to the exit, the strip stays
            return self.observe()
        elif cell not in (0,):
            return self.observe()                       # walls, frame, decoys block
        self.grid[py, px] = 0
        self.grid[ny, nx] = 1
        return self.observe()
