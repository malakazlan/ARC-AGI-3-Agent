"""Shortest key sequence over predicted avatar positions (unit cost, so BFS is A* with h=0)."""
from __future__ import annotations

from collections import deque
from typing import Callable

import numpy as np

from arc3.world_model import PassabilityModel, predict_move

Cells = frozenset[tuple[int, int]]
Goal = Callable[[Cells], bool]

MAX_POSITIONS = 4096


def unknown_ahead(grid: np.ndarray, cells: Cells, keys: dict[int, tuple[int, int]],
                  model: PassabilityModel, origin: Cells) -> bool:
    return any(predict_move(grid, cells, vec, model, origin) is None for vec in keys.values())


def plan_moves(grid: np.ndarray, start: Cells, keys: dict[int, tuple[int, int]], model: PassabilityModel,
               goal: Goal | None, max_positions: int = MAX_POSITIONS) -> list[int] | None:
    """Keys to press from `start` to reach `goal` (or, with goal=None, the nearest position
    from which some key's outcome is unknown). [] when already there, None when unreachable
    through known-passable cells."""
    origin = start

    def is_goal(cells: Cells) -> bool:
        if goal is not None:
            return goal(cells)
        return unknown_ahead(grid, cells, keys, model, origin)

    if is_goal(start):
        return []
    parent: dict[Cells, tuple[Cells, int] | None] = {start: None}
    queue: deque[Cells] = deque([start])
    while queue and len(parent) < max_positions:
        cells = queue.popleft()
        for key, vec in keys.items():
            pred = predict_move(grid, cells, vec, model, origin)
            if pred is None or pred[0] != "moved":
                continue
            nxt = pred[1]
            if nxt in parent:
                continue
            parent[nxt] = (cells, key)
            if is_goal(nxt):
                return _unwind(parent, nxt)
            queue.append(nxt)
    return None


def _unwind(parent: dict[Cells, tuple[Cells, int] | None], cells: Cells) -> list[int]:
    path: list[int] = []
    while parent[cells] is not None:
        cells, key = parent[cells]
        path.append(key)
    path.reverse()
    return path
