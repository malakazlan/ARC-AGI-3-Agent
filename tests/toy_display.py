"""A toy of the ls20 level-1 structure (owner's play notes, docs/HUMAN_PLAY.md).

12x12, background 0. Avatar colour 1 (1 cell), moved by ACTION1-4 one cell; walls colour 2 block.
Rotator: a colour-7 cell; walking into it does not move the avatar but cycles the panel's
inner colour through (9, 3, 5). Panel: 3x3 frame of colour 6 at bottom-left with an inner cell.
Target: same frame at top-right with a static inner colour (5). Exit: colour 4 cell; walking
into it wins the level only if panel inner == target inner, otherwise it is a wall.
"""
from __future__ import annotations

import numpy as np

from arc3.agent import Observation

MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
CYCLE = (9, 3, 5)


class DisplayToy:
    def __init__(self, target: int = 5, start_inner: int = 9, exit_in_target: bool = False,
                 rotator_walkable: bool = False) -> None:
        """`exit_in_target`: no separate exit; stepping onto the target frame wins when matched
        (ls20's real layout). `rotator_walkable`: the avatar moves onto the rotator when it
        touches it, hiding it (ls20's real rotator)."""
        self.target = target
        self.start_inner = start_inner
        self.exit_in_target = exit_in_target
        self.rotator_walkable = rotator_walkable
        self.under_avatar = 0
        self.levels = 1
        self.levels_completed = 0
        self.state = "NOT_PLAYED"
        self.steps = 0
        self.game_overs = 0
        self.touches = 0
        self.grid = self._layout()

    def _layout(self) -> np.ndarray:
        g = np.zeros((12, 12), dtype=np.int8)
        g[5, 2:10] = 2                          # a wall with gaps at the sides
        g[9:12, 0:3] = 6; g[10, 1] = self.start_inner   # panel (changeable)
        g[0:3, 9:12] = 6; g[1, 10] = self.target        # target (static)
        g[2, 2] = 7                             # rotator
        if not self.exit_in_target:
            g[10, 10] = 4                       # exit
        g[7, 6] = 1                             # avatar
        return g

    def observe(self) -> Observation:
        grid = self.grid.copy() if self.state == "NOT_FINISHED" else None
        return Observation(self.state, self.levels_completed, self.levels, grid, [1, 2, 3, 4])

    @property
    def inner(self) -> int:
        return int(self.grid[10, 1])

    def apply(self, action_id: int, x=None, y=None) -> Observation:
        self.steps += 1
        if action_id == 0:
            self.grid = self._layout()
            self.under_avatar = 0
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
        if cell == 7:                            # rotator: touch (and step onto it if walkable)
            self.touches += 1
            self.grid[10, 1] = CYCLE[(CYCLE.index(self.inner) + 1) % 3]
            if not self.rotator_walkable:
                return self.observe()
        elif cell == 4 or (self.exit_in_target and cell in (6, self.target) and ny <= 2 and nx >= 9):
            if self.inner == self.target:       # exit (or the target frame itself)
                self.levels_completed = 1
                self.state = "WIN"
            return self.observe()
        elif cell != 0:                          # walls, panels, target: blocked
            return self.observe()
        self.grid[py, px] = self.under_avatar
        self.under_avatar = cell if cell == 7 else 0
        self.grid[ny, nx] = 1
        return self.observe()
