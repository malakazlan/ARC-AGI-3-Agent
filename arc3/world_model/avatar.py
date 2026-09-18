"""Which object do the keys move, and where does each key move it?

Learned once per game. After every key press that changed the frame, the object-level
translation test yields the groups of objects that moved and by how much. An object is
controllable when its displacement depends on the key: different keys, different vectors
(staying put counts as the zero vector). An object that moves the same way whatever we press
is autonomous and is never the avatar. Each key's vector is the dominant displacement of the
avatar under that key once it has enough votes.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from arc3.perception import find_translations

MIN_VOTES = 2
MIN_SHARE = 0.6
MIN_EXPLAINED = 0.0  # every moved group counts: a small avatar next to a big drifter is normal (sp80)
MIN_OVERLAP = 0.5    # a partial-appearance move must overlap the tracked avatar this much

Cells = frozenset[tuple[int, int]]
Signature = tuple


class AvatarModel:
    def __init__(self) -> None:
        # signature -> key -> Counter of displacements (including (0, 0) for "did not move")
        self.moves: dict[Signature, dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
        self.signature: Signature | None = None  # the avatar's object signature
        self.last_vector: dict[int, tuple[int, int]] = {}
        self.blocked_votes = 0
        self.template: dict[tuple[int, int], int] | None = None
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
            for sig in list(self.moves):          # nothing moved: every known object stayed
                self.moves[sig][action][(0, 0)] += 1
            return "blocked"
        self.moves_seen += 1
        groups = [g for g in find_translations(before, after, mask) if g.explained >= MIN_EXPLAINED]
        tracked = None
        if self.last_cells and self.template and _matches(before, self.template, self.last_cells):
            tracked = self.last_cells
        moved_sigs = {sig for g in groups for sig in g.signatures}
        for g in groups:
            for sig in g.signatures:
                self.moves[sig][action][(g.dy, g.dx)] += 1
        for sig in list(self.moves):              # known objects that stayed put under this key
            if sig not in moved_sigs:
                self.moves[sig][action][(0, 0)] += 1
        self._elect()
        mine = self._my_group(groups, tracked)
        if mine is None:
            if tracked is not None:
                self.blocked_votes += 1
                return "blocked"  # something else moved, not the avatar
            return "unexplained"
        self.moves_explained += 1
        self.last_vector[action] = (mine.dy, mine.dx)
        moved = set(mine.cells)
        overlap = len(moved & tracked) / len(tracked) if tracked else 0.0
        source = tracked if (tracked is not None and overlap >= MIN_OVERLAP) else frozenset(mine.cells)
        h, w = after.shape
        shifted = frozenset((y + mine.dy, x + mine.dx) for (y, x) in source)
        if any(not (0 <= y < h and 0 <= x < w) for (y, x) in shifted):
            shifted = frozenset((y + mine.dy, x + mine.dx) for (y, x) in mine.cells)
        self.last_cells = shifted
        self.template = _template(after, self.last_cells)
        return "moved"

    def _elect(self) -> None:
        """Pick the avatar: the controllable signature with the most evidence."""
        best = None
        for sig in self.controllable:
            votes = sum(sum(c.values()) for c in self.moves[sig].values())
            if best is None or votes > best[0]:
                best = (votes, sig)
        self.signature = best[1] if best else None

    def _my_group(self, groups, tracked):
        if self.signature is None:
            return None
        for g in groups:
            if self.signature in g.signatures:
                return g
        if tracked is not None:  # appearance changed: follow by overlap instead
            for g in groups:
                if len(set(g.cells) & tracked) / len(tracked) >= MIN_OVERLAP:
                    return g
        return None

    # -- what we know -----------------------------------------------------------------------

    @property
    def controllable(self) -> list[Signature]:
        """Signatures whose dominant displacement differs between at least two keys."""
        out = []
        for sig, per_key in self.moves.items():
            dominant = {k: c.most_common(1)[0][0] for k, c in per_key.items() if c}
            if len(set(dominant.values())) >= 2:
                out.append(sig)
        return out

    def vector(self, action: int) -> tuple[int, int] | None:
        if self.signature is None:
            return None
        votes = self.moves[self.signature].get(action)
        if not votes:
            return None
        moving = Counter({d: n for d, n in votes.items() if d != (0, 0)})  # bumps are passability
        if not moving:
            return None
        (vec, count), = moving.most_common(1)
        total = sum(moving.values())
        if count >= MIN_VOTES and count / total >= MIN_SHARE:
            return vec
        return None

    @property
    def confident(self) -> bool:
        return (self.signature is not None and self.template is not None
                and any(self.vector(a) is not None for a in self.moves[self.signature]))

    def avatar_cells(self, grid: np.ndarray) -> Cells:
        """Cells occupied by the avatar in `grid`: the tracked cells if the template still
        matches there, else the nearest template match. Empty when unknown or not found."""
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
