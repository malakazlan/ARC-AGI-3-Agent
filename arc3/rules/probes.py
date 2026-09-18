"""Which unknown object to probe first (design v2 section 6, the delta list).

A probe is worth an action only if the avatar can touch the object: it must border the
walkable region the avatar stands in (HUD counters and legends sit outside the walls). Among
touchable objects, icons drawn in several colours come before plain marks (a player tries the
colourful thing first), then smaller ones, then nearer ones.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from arc3.perception import GridObject

Cells = frozenset[tuple[int, int]]


def reachable_region(walkable: np.ndarray, seeds: Cells) -> np.ndarray:
    """Cells connected to `seeds` through walkable cells (4-neighbourhood, unit steps)."""
    h, w = walkable.shape
    region = np.zeros_like(walkable, dtype=bool)
    queue = deque()
    for (y, x) in seeds:
        if 0 <= y < h and 0 <= x < w and not region[y, x]:
            region[y, x] = True
            queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and walkable[ny, nx] and not region[ny, nx]:
                region[ny, nx] = True
                queue.append((ny, nx))
    return region


def touchable(obj: GridObject, region: np.ndarray) -> bool:
    h, w = region.shape
    for (y, x) in obj.cells:
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1), (y, x)):
            if 0 <= ny < h and 0 <= nx < w and region[ny, nx]:
                return True
    return False


def rank_probes(objects: list[GridObject], walkable: np.ndarray, avatar: Cells,
                colours_of=None) -> list[GridObject]:
    """Touchable objects, most promising first. `colours_of(obj)` gives the number of colours
    an object is drawn in (compound icons are merged before ranking); default 1."""
    region = reachable_region(walkable, avatar)
    ay = sum(y for y, _ in avatar) / max(1, len(avatar))
    ax = sum(x for _, x in avatar) / max(1, len(avatar))
    out = [o for o in objects if touchable(o, region)]
    out.sort(key=lambda o: (-(colours_of(o) if colours_of else 1), o.size,
                            abs(o.centroid[0] - ay) + abs(o.centroid[1] - ax)))
    return out
