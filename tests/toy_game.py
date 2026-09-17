"""A tiny deterministic grid game for exercising the explorer without the engine.

8x8 grid. Colors: 0 floor, 1 player, 2 wall, 3 trap (GAME_OVER), 4 goal (level up), 5 button.
ACTION1..4 move the player up/down/left/right; walls block (no-op). ACTION6 on a button
removes it; anywhere else it is a no-op. Two levels; level 2 has a different layout.
`extra_cells` paints extra cells onto every layout (also after resets).
"""
from __future__ import annotations

import numpy as np

from arc3.agent import Observation

MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def level_layout(index: int) -> np.ndarray:
    g = np.zeros((8, 8), dtype=np.int8)
    if index == 0:
        g[3, 0:6] = 2          # wall row with a gap at x=6,7
        g[1, 1] = 1            # player
        g[6, 6] = 4            # goal
        g[6, 1] = 3            # trap
    else:
        g[0:8, 4] = 2          # wall column
        g[2, 4] = 0            # gap
        g[7, 0] = 1            # player
        g[0, 7] = 4            # goal
        g[5, 6] = 3            # trap
    return g


class ToyGame:
    def __init__(self, available=(1, 2, 3, 4), levels: int = 2,
                 extra_cells: dict[tuple[int, int], int] | None = None,
                 budget: int | None = None) -> None:
        self.available = list(available)
        self.levels = levels
        self.extra_cells = dict(extra_cells or {})
        self.budget = budget          # actions per attempt before GAME_OVER; bar on row 7
        self.attempt_steps = 0
        self.level = 0
        self.levels_completed = 0
        self.state = "NOT_PLAYED"
        self.grid = self._layout()
        self.steps = 0
        self.game_overs = 0

    def _layout(self) -> np.ndarray:
        g = level_layout(self.level)
        for (y, x), color in self.extra_cells.items():
            g[y, x] = color
        if self.budget is not None:
            g[7, :] = 6                  # full energy bar
        self.attempt_steps = 0
        return g

    def _tick_budget(self) -> None:
        if self.budget is None or self.state != "NOT_FINISHED":
            return
        self.attempt_steps += 1
        drained = min(8, (8 * self.attempt_steps) // self.budget)
        self.grid[7, :drained] = 0
        if self.attempt_steps >= self.budget:
            self.state = "GAME_OVER"
            self.game_overs += 1

    def observe(self) -> Observation:
        grid = self.grid.copy() if self.state == "NOT_FINISHED" else None
        return Observation(self.state, self.levels_completed, self.levels, grid, list(self.available))

    def apply(self, action_id: int, x: int | None = None, y: int | None = None) -> Observation:
        self.steps += 1
        if action_id == 0:
            self.grid = self._layout()
            self.state = "NOT_FINISHED"
            return self.observe()
        if self.state != "NOT_FINISHED":
            return self.observe()
        if action_id in MOVES:
            self._move(*MOVES[action_id])
        elif action_id == 6 and x is not None and self.grid[y, x] == 5:
            self.grid[y, x] = 0
        self._tick_budget()
        return self.observe()

    def _move(self, dy: int, dx: int) -> None:
        py, px = map(int, np.argwhere(self.grid == 1)[0])
        ny, nx = py + dy, px + dx
        if not (0 <= ny < 8 and 0 <= nx < 8) or self.grid[ny, nx] == 2:
            return
        target = self.grid[ny, nx]
        self.grid[py, px] = 0
        if target == 3:
            self.state = "GAME_OVER"
            self.game_overs += 1
            return
        if target == 4:
            self.levels_completed += 1
            self.level += 1
            if self.level >= self.levels:
                self.state = "WIN"
            else:
                self.grid = self._layout()
            return
        self.grid[ny, nx] = 1
