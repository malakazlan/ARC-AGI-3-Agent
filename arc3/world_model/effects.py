"""Online action-effect prior: per action class, how often it changed the frame or killed.

An action class is what a player would generalise over: the key id for simple actions, and
(colour, size bucket) of the object under the cursor for clicks. Classes that never did
anything after a few tries, or that kill more often than not, are explored last.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from arc3.perception import GridObject, segment_objects
from arc3.types import COMPLEX_ACTION_ID, ActionKey

ActionClass = tuple
Signature = tuple  # (colour, shape key, size)

SIZE_BUCKETS = ((1, 4, "1-4"), (5, 16, "5-16"), (17, 64, "17-64"), (65, 256, "65-256"))
DEAD_AFTER_TRIES = 3
LETHAL_AFTER_DEATHS = 2
LETHAL_RATE = 0.5


def size_bucket(size: int) -> str:
    for lo, hi, name in SIZE_BUCKETS:
        if lo <= size <= hi:
            return name
    return "257+"


def click_class(color: int, size: int) -> ActionClass:
    return (COMPLEX_ACTION_ID, int(color), size_bucket(size))


def action_class(action: ActionKey, grid: np.ndarray) -> ActionClass:
    """Class of an action on a grid. Clicks segment the grid (slow); the explorer passes
    classes from its own segmentation instead of calling this per candidate."""
    action_id, x, y = action
    if action_id != COMPLEX_ACTION_ID or x is None or y is None:
        return (action_id,)
    for obj in segment_objects(grid, background=-1):
        if obj.bbox[0] <= y <= obj.bbox[2] and obj.bbox[1] <= x <= obj.bbox[3] and grid[y, x] == obj.color:
            return click_class(obj.color, obj.size)
    return click_class(int(grid[y, x]), 1)


@dataclass
class ClassStats:
    tries: int = 0
    changes: int = 0
    deaths: int = 0


@dataclass
class ActionPrior:
    stats: dict[ActionClass, ClassStats] = field(default_factory=dict)

    def record(self, cls: ActionClass, changed: bool, game_over: bool) -> None:
        s = self.stats.setdefault(cls, ClassStats())
        s.tries += 1
        s.changes += int(changed)
        s.deaths += int(game_over)

    def deferred(self, cls: ActionClass) -> bool:
        """True for classes worth trying only when nothing better is left."""
        s = self.stats.get(cls)
        if s is None:
            return False
        dead = s.tries >= DEAD_AFTER_TRIES and s.changes == 0 and s.deaths == 0
        lethal = s.deaths >= LETHAL_AFTER_DEATHS and s.deaths / s.tries >= LETHAL_RATE
        return dead or lethal

    def score(self, cls: ActionClass) -> float:
        """Higher is more promising. Fresh classes score 0.5."""
        s = self.stats.get(cls)
        if s is None:
            return 0.5
        return (s.changes + 1) / (s.tries + 2) - s.deaths / (s.tries + 1)


# -- click effects by object signature ------------------------------------------------------

def shape_key(obj: GridObject) -> str:
    """Position-free shape: bbox size plus the occupancy pattern (exact up to 64 cells)."""
    y0, x0, y1, x1 = obj.bbox
    h, w = y1 - y0 + 1, x1 - x0 + 1
    if obj.size > 64:
        return f"{h}x{w}"
    bits = ["0"] * (h * w)
    for y, x in obj.cells:
        bits[(y - y0) * w + (x - x0)] = "1"
    return f"{h}x{w}:{int(''.join(bits), 2):x}"


def object_signature(obj: GridObject) -> Signature:
    return (int(obj.color), shape_key(obj), int(obj.size))


RelativeDiff = tuple[tuple[int, int, int], ...]  # (dy, dx, new colour) relative to the click


@dataclass(frozen=True)
class Effect:
    changed: bool
    diff: RelativeDiff


def relative_diff(click: tuple[int, int], before: np.ndarray, after: np.ndarray) -> RelativeDiff:
    cy, cx = click
    ys, xs = np.nonzero(before != after)
    return tuple(sorted((int(y - cy), int(x - cx), int(after[y, x])) for y, x in zip(ys, xs)))


@dataclass
class ClickEffects:
    """Per object signature, the relative effect of clicking it. Consistent k times => global."""

    k: int = 3
    history: dict[Signature, list[RelativeDiff]] = field(default_factory=dict)

    def record(self, sig: Signature, click: tuple[int, int], before: np.ndarray, after: np.ndarray) -> None:
        diff = relative_diff(click, before, after)
        seen = self.history.setdefault(sig, [])
        seen.append(diff)
        del seen[:-max(self.k, 5)]

    def global_effect(self, sig: Signature) -> Effect | None:
        seen = self.history.get(sig, [])
        if len(seen) < self.k:
            return None
        recent = seen[-self.k:]
        if any(d != recent[0] for d in recent):
            return None
        return Effect(changed=bool(recent[0]), diff=recent[0])

    def predict(self, sig: Signature, click: tuple[int, int], grid: np.ndarray) -> np.ndarray | None:
        effect = self.global_effect(sig)
        if effect is None:
            return None
        out = grid.copy()
        cy, cx = click
        h, w = grid.shape
        for dy, dx, colour in effect.diff:
            y, x = cy + dy, cx + dx
            if 0 <= y < h and 0 <= x < w:
                out[y, x] = colour
        return out
