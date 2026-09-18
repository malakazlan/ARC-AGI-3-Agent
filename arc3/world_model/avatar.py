"""Which object do the keys move, and where does each key move it?

Learned once per game from the first explained moves: after every key action that changed the
frame, the translation test yields a displacement and the cells that moved. The avatar is the
template (relative colour pattern) of those cells; each key's vector is the dominant
displacement once it has enough votes. Contradictory evidence leaves a key unknown.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from arc3.perception import find_translation

MIN_VOTES = 3
MIN_SHARE = 0.6
MIN_EXPLAINED = 0.8
MIN_OVERLAP = 0.5  # a partial-appearance move must overlap the tracked avatar this much

Cells = frozenset[tuple[int, int]]


class AvatarModel:
    def __init__(self) -> None:
        self.votes: dict[int, Counter] = defaultdict(Counter)
        self.last_vector: dict[int, tuple[int, int]] = {}  # latest explained displacement per key
        self.blocked_votes = 0
        self.template: dict[tuple[int, int], int] | None = None  # relative (dy, dx) -> colour
        self.last_cells: Cells | None = None
        self.moves_seen = 0
        self.moves_explained = 0

    # -- learning ---------------------------------------------------------------------------

    def observe(self, before: np.ndarray, action: int, after: np.ndarray,
                mask: np.ndarray | None = None) -> str:
        """Learn from one key press. Returns "blocked", "moved" or "unexplained"."""
        diff = before != after
        if mask is not None:
            diff &= ~mask
        if not diff.any():
            self.blocked_votes += 1
            return "blocked"
        self.moves_seen += 1
        tr = find_translation(before, after, mask)
        tracked = None
        if self.last_cells and self.template and _matches(before, self.template, self.last_cells):
            tracked = self.last_cells
        if tr is None:
            if tracked is not None:
                self.blocked_votes += 1
                return "blocked"  # the avatar stayed; something else changed
            return "unexplained"
        moved = set(tr.cells)
        overlap = len(moved & tracked) / len(tracked) if tracked else 0.0
        if tr.explained < MIN_EXPLAINED and overlap < MIN_OVERLAP:
            if tracked is not None and not (moved & tracked):
                self.blocked_votes += 1
                return "blocked"  # something else moved, not the avatar
            return "unexplained"
        self.moves_explained += 1
        self.votes[action][(tr.dy, tr.dx)] += 1
        self.last_vector[action] = (tr.dy, tr.dx)
        source = tracked if (tracked is not None and overlap >= MIN_OVERLAP) else frozenset(tr.cells)
        h, w = after.shape
        shifted = frozenset((y + tr.dy, x + tr.dx) for (y, x) in source)
        if any(not (0 <= y < h and 0 <= x < w) for (y, x) in shifted):
            shifted = frozenset((y + tr.dy, x + tr.dx) for (y, x) in tr.cells)  # moved cells are in-bounds
        self.last_cells = shifted
        self.template = _template(after, self.last_cells)
        return "moved"

    # -- what we know -----------------------------------------------------------------------

    def vector(self, action: int) -> tuple[int, int] | None:
        votes = self.votes.get(action)
        if not votes:
            return None
        (vec, count), = votes.most_common(1)
        total = sum(votes.values())
        if count >= MIN_VOTES and count / total >= MIN_SHARE:
            return vec
        return None

    @property
    def confident(self) -> bool:
        return self.template is not None and any(self.vector(a) is not None for a in self.votes)

    def avatar_cells(self, grid: np.ndarray) -> Cells:
        """Cells occupied by the avatar in `grid`, by matching its template (nearest to the last
        known position first). Empty when the template is unknown or not found."""
        if self.template is None:
            return frozenset()
        if self.last_cells and _matches(grid, self.template, self.last_cells):
            return self.last_cells
        h, w = grid.shape
        offsets = list(self.template)
        dys = [d for d, _ in offsets]
        dxs = [d for _, d in offsets]
        anchor_y, anchor_x = _anchor(self.last_cells) if self.last_cells else (0, 0)
        candidates = []
        for y in range(-min(dys), h - max(dys)):
            for x in range(-min(dxs), w - max(dxs)):
                if all(grid[y + dy, x + dx] == c for (dy, dx), c in self.template.items()):
                    cells = frozenset((y + dy, x + dx) for (dy, dx) in offsets)
                    candidates.append((abs(y - anchor_y) + abs(x - anchor_x), cells))
        if not candidates:
            return frozenset()
        candidates.sort(key=lambda c: c[0])
        self.last_cells = candidates[0][1]
        return self.last_cells

    def predict_cells(self, cells: Cells, action: int) -> Cells | None:
        vec = self.vector(action)
        if vec is None:
            return None
        return frozenset((y + vec[0], x + vec[1]) for (y, x) in cells)


def _anchor(cells: Cells) -> tuple[int, int]:
    return min(cells)


def _template(grid: np.ndarray, cells: Cells) -> dict[tuple[int, int], int]:
    ay, ax = _anchor(cells)
    return {(y - ay, x - ax): int(grid[y, x]) for (y, x) in cells}


def _matches(grid: np.ndarray, template: dict[tuple[int, int], int], cells: Cells) -> bool:
    ay, ax = _anchor(cells)
    h, w = grid.shape
    for (dy, dx), c in template.items():
        y, x = ay + dy, ax + dx
        if not (0 <= y < h and 0 <= x < w) or grid[y, x] != c:
            return False
    return True
