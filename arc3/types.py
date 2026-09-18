"""Plain value types shared by every module. No engine imports."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RESET_ID = 0
COMPLEX_ACTION_ID = 6

# (action_id, x, y); x and y are None for simple actions.
ActionKey = tuple[int, int | None, int | None]


@dataclass(frozen=True, eq=False)
class Observation:
    state: str  # GameState name: NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER
    levels_completed: int
    win_levels: int
    grid: np.ndarray | None  # last frame, int8 [y, x]; None before the first frame
    available_actions: list[int]
    flash: bool = False  # an intermediate frame of this response was (almost) one solid colour


@dataclass(frozen=True)
class ActionChoice:
    action_id: int
    x: int | None
    y: int | None
    reason: str

    @property
    def key(self) -> ActionKey:
        return (self.action_id, self.x, self.y)
