"""Ordered subgoal routes under an energy budget (design v2 section 6).

A route visits every stop (dials, then the exit last) and inserts refills where the energy
projected along the whole route would run dry. Greedy leg-by-leg decisions dither between
"refill" and "dial" (ls20 level 3); ordering the stops with the projection in hand does not.
Sizes are tiny (a few stops, a few refills), so the search is exhaustive.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import numpy as np

Pos = tuple[int, int]
Dist = Callable[[Pos, Pos], "int | None"]


@dataclass(frozen=True)
class Stop:
    name: str
    at: Pos
    presses: int = 1      # actions spent at the stop once there (each costs energy like a move)
    final: bool = False   # must come last (the exit)


def plan_route(start: Pos, stops: list[Stop], refills: list[Pos], moves_left: int, capacity: int,
               dist: Dist, margin: int = 1) -> list[Stop] | None:
    """Cheapest order of `stops` with refills (each usable once, restoring `capacity`) inserted
    so that the projected energy stays >= `margin` after every leg but the last, which may end
    at zero. Returns the ordered stops including the refills taken, or None when no order fits."""
    finals = [s for s in stops if s.final]
    if len(finals) > 1:
        return None
    final = finals[0] if finals else None
    middle = tuple(s for s in stops if not s.final)
    refill_stops = tuple(Stop("refill", r, presses=1) for r in refills)

    @lru_cache(maxsize=None)
    def best(pos: Pos, left: int, todo: frozenset, fuel: frozenset) -> tuple[int, tuple] | None:
        if not todo:
            if final is None:
                return (0, ())
            d = dist(pos, final.at)
            if d is None or left - d - final.presses < 0:
                candidates = []
            else:
                return (d + final.presses, (final,))
        else:
            candidates = []
        options = [(s, todo - {s}, fuel) for s in todo] + [(r, todo, fuel - {r}) for r in fuel]
        for stop, todo2, fuel2 in options:
            d = dist(pos, stop.at)
            if d is None:
                continue
            cost = d + stop.presses
            after = left - cost
            if after < margin:
                continue
            if stop.name == "refill":
                after = capacity
            rest = best(stop.at, after, todo2, fuel2)
            if rest is None:
                continue
            candidates.append((cost + rest[0], (stop,) + rest[1]))
        if not candidates:
            return None
        return min(candidates, key=lambda c: (c[0], len(c[1])))

    result = best(start, moves_left, frozenset(middle), frozenset(refill_stops))
    return None if result is None else list(result[1])


def cell_route_length(walkable: np.ndarray, start: Pos, goal: Pos, step: int) -> int | None:
    """Moves of `step` cells over walkable cells from `start` until `goal` lies within one move
    (Chebyshev distance <= step): the leg length to a stop that is then touched or entered.
    None when no such cell can be reached. Every cell swept by a move must be walkable."""
    h, w = walkable.shape
    step = max(1, int(step))

    def near(p: Pos) -> bool:
        return max(abs(p[0] - goal[0]), abs(p[1] - goal[1])) <= step

    if near(start):
        return 0
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        (y, x), d = queue.popleft()
        for dy, dx in ((-step, 0), (step, 0), (0, -step), (0, step)):
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w) or (ny, nx) in seen:
                continue
            sy, sx = (dy > 0) - (dy < 0), (dx > 0) - (dx < 0)
            if not all(walkable[y + sy * i, x + sx * i] for i in range(1, step + 1)):
                continue
            if near((ny, nx)):
                return d + 1
            seen.add((ny, nx))
            queue.append(((ny, nx), d + 1))
    return None
