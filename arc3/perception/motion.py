"""Rigid translation between two frames: which cells moved, and by how much."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

WINDOW = 4  # maximum displacement searched, in cells


@dataclass(frozen=True)
class Translation:
    dy: int
    dx: int
    explained: float  # share of changed cells accounted for by the move
    cells: tuple[tuple[int, int], ...]  # source cells (in `before`) that moved


def find_translation(before: np.ndarray, after: np.ndarray, mask: np.ndarray | None = None,
                     window: int = WINDOW) -> Translation | None:
    """Best single displacement (dy, dx) explaining the difference between the frames.

    A cell counts as moved when its `before` content reappears displaced in `after` and the
    displaced target itself changed. Masked cells (an energy bar) are ignored. None when nothing
    changed outside the mask.
    """
    if before.shape != after.shape:
        return None
    diff = before != after
    if mask is not None:
        diff &= ~mask
    if not diff.any():
        return None
    total = int(diff.sum())
    h, w = before.shape
    ys, xs = np.nonzero(diff)
    best: Translation | None = None
    for dy in range(-window, window + 1):
        for dx in range(-window, window + 1):
            if (dy, dx) == (0, 0):
                continue
            moved: list[tuple[int, int]] = []
            landed = 0
            for y, x in zip(ys, xs):
                ty, tx = y + dy, x + dx
                if 0 <= ty < h and 0 <= tx < w and after[ty, tx] == before[y, x] and after[ty, tx] != before[ty, tx]:
                    moved.append((int(y), int(x)))
                    landed += int(diff[ty, tx])
            if not moved:
                continue
            explained = min(1.0, (len(moved) + landed) / total)
            if best is None or explained > best.explained:
                best = Translation(dy, dx, explained, tuple(moved))
    return best
