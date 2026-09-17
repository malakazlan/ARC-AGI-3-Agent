"""Pure grid functions. Grids are 2D numpy int8 arrays of colors 0..15, indexed [y, x]."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

BBox = tuple[int, int, int, int]  # y0, x0, y1, x1 inclusive


@dataclass(frozen=True, eq=False)
class FrameDiff:
    mask: np.ndarray  # bool, shape of the first grid
    changed: int
    bbox: BBox | None


@dataclass(frozen=True)
class GridObject:
    color: int
    size: int
    bbox: BBox
    centroid: tuple[float, float]  # (y, x)
    anchor: tuple[int, int]  # (y, x) cell inside the object nearest its centroid


def frame_diff(a: np.ndarray, b: np.ndarray) -> FrameDiff:
    """Cells where b differs from a. A shape change counts as every cell changed."""
    if a.shape != b.shape:
        mask = np.ones(a.shape, dtype=bool)
    else:
        mask = a != b
    changed = int(mask.sum())
    return FrameDiff(mask=mask, changed=changed, bbox=_bbox_of(mask) if changed else None)


def segment_objects(
    grid: np.ndarray, background: int | None = None, connectivity: int = 4
) -> list[GridObject]:
    """Connected components of equal color, excluding the background color.

    background defaults to the most common color. Result is sorted largest first, then by
    top-left position, so it is deterministic for a given grid.
    """
    if background is None:
        background = _most_common_color(grid)
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    steps = _NEIGHBOURS_8 if connectivity == 8 else _NEIGHBOURS_4
    objects: list[GridObject] = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0, x0] or grid[y0, x0] == background:
                continue
            cells = _flood_fill(grid, seen, y0, x0, steps)
            objects.append(_object_from_cells(int(grid[y0, x0]), cells))
    objects.sort(key=lambda o: (-o.size, o.bbox[0], o.bbox[1]))
    return objects


def volatility_mask(frames: list[np.ndarray]) -> np.ndarray:
    """Cells that differ between any two frames of the sequence (same shape as frames[0]).

    Feed it frames observed without a state-changing action (timers, animations) so the mask
    can be excluded from state keys. Frames of another shape are ignored.
    """
    first = frames[0]
    mask = np.zeros(first.shape, dtype=bool)
    for frame in frames[1:]:
        if frame.shape == first.shape:
            mask |= frame != first
    return mask


class AttemptSignature:
    """Per-attempt record of cells that changed exactly once: cell -> (step offset, new value).

    Built incrementally from consecutive frames so no frame buffer is needed. Cells that
    change more than once are dropped (None) and never revived.
    """

    def __init__(self) -> None:
        self.length = 0
        self.shape: tuple[int, int] | None = None
        self.actions: list[object] = []  # actions[o] produced frame o; actions[0] is None
        self._prev: np.ndarray | None = None
        self._cells: dict[tuple[int, int], tuple[int, int] | None] = {}

    def push(self, frame: np.ndarray, action: object = None) -> None:
        if self._prev is not None and frame.shape == self._prev.shape:
            offset = self.length
            for y, x in zip(*np.nonzero(frame != self._prev)):
                cell = (int(y), int(x))
                self._cells[cell] = None if cell in self._cells else (offset, int(frame[y, x]))
        self.shape = (int(frame.shape[0]), int(frame.shape[1]))
        self.actions.append(None if self._prev is None else action)
        self._prev = frame
        self.length += 1

    @property
    def once(self) -> dict[tuple[int, int], tuple[int, int]]:
        return {c: s for c, s in self._cells.items() if s is not None}

    def changed(self, cell: tuple[int, int]) -> bool:
        return cell in self._cells


def countdown_mask_from_signatures(signatures: list[AttemptSignature], shape: tuple[int, int],
                                   min_attempts: int = 2) -> np.ndarray:
    """Cells that behave like an energy or countdown bar across attempts of the same level.

    A bar cell changes exactly once per attempt, at the same step offset and to the same value,
    in every attempt that lasted long enough to reach that offset, and in at least two attempts.
    The change must be independent of what the agent did: among the supporting attempts, the
    actions taken at that offset must differ (an identical replay would make the player's own
    trail look like a bar; unknown actions, None, are treated as differing). Isolated cells are
    ignored (the start cell the player always leaves at step 1 would otherwise qualify): bar
    cells come in connected groups with staggered offsets.
    """
    shape = (int(shape[0]), int(shape[1]))
    mask = np.zeros(shape, dtype=bool)
    signatures = [s for s in signatures if s.length >= 2 and s.shape == shape]
    if len(signatures) < min_attempts:
        return mask
    onces = [s.once for s in signatures]
    consistent: dict[tuple[int, int], tuple[int, int]] = {}
    seen: set[tuple[int, int]] = set()
    for once in onces:
        for cell, (offset, value) in once.items():
            if cell in seen:
                continue
            seen.add(cell)
            support = 0
            ok = True
            actions_seen: set[object] = set()
            unknown = False
            for sig, other in zip(signatures, onces):
                if sig.length <= offset:
                    if sig.changed(cell):
                        ok = False
                        break
                    continue
                if other.get(cell) != (offset, value):
                    ok = False
                    break
                support += 1
                action = sig.actions[offset] if offset < len(sig.actions) else None
                if action is None:
                    unknown = True
                actions_seen.add(action)
            independent = unknown or len(actions_seen) >= 2
            if ok and support >= min_attempts and independent:
                consistent[cell] = (offset, value)
    if not consistent:
        return mask
    candidates = np.zeros(shape, dtype=np.int8)
    for (y, x) in consistent:
        candidates[y, x] = 1
    for group in segment_objects(candidates, background=0):
        cells = [c for c in consistent if group.bbox[0] <= c[0] <= group.bbox[2]
                 and group.bbox[1] <= c[1] <= group.bbox[3]]
        if group.size >= 2 and len({consistent[c][0] for c in cells}) >= 2:
            for y, x in cells:
                mask[y, x] = True
    return mask


def countdown_mask(attempts: list[list[np.ndarray]],
                   actions: list[list[object]] | None = None) -> np.ndarray:
    """Batch convenience wrapper over `countdown_mask_from_signatures` for frame lists.

    `actions[i][o-1]` is the action that produced frame `o` of attempt `i`. Without actions the
    independence test is skipped (only sensible for synthetic data).
    """
    keep = [k for k, a in enumerate(attempts) if len(a) >= 2]
    if not keep:
        return np.zeros((0, 0), dtype=bool)
    signatures = []
    for k in keep:
        sig = AttemptSignature()
        acts = actions[k] if actions is not None else None
        for o, frame in enumerate(attempts[k]):
            sig.push(frame, None if (acts is None or o == 0) else acts[o - 1])
        signatures.append(sig)
    return countdown_mask_from_signatures(signatures, attempts[keep[0]][0].shape)


def state_hash(grid: np.ndarray, mask: np.ndarray | None = None) -> str:
    """Stable key for a grid. Masked cells are replaced by a sentinel so they never matter."""
    keyed = grid.astype(np.int8, copy=True)
    if mask is not None:
        keyed[mask] = -1
    digest = hashlib.blake2b(digest_size=16)
    digest.update(np.asarray(keyed.shape, dtype=np.int32).tobytes())
    digest.update(keyed.tobytes())
    return digest.hexdigest()


_NEIGHBOURS_4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_NEIGHBOURS_8 = _NEIGHBOURS_4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _flood_fill(
    grid: np.ndarray, seen: np.ndarray, y0: int, x0: int, steps: tuple[tuple[int, int], ...]
) -> list[tuple[int, int]]:
    color = grid[y0, x0]
    h, w = grid.shape
    stack = [(y0, x0)]
    seen[y0, x0] = True
    cells: list[tuple[int, int]] = []
    while stack:
        y, x = stack.pop()
        cells.append((y, x))
        for dy, dx in steps:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and grid[ny, nx] == color:
                seen[ny, nx] = True
                stack.append((ny, nx))
    return cells


def _object_from_cells(color: int, cells: list[tuple[int, int]]) -> GridObject:
    ys = [y for y, _ in cells]
    xs = [x for _, x in cells]
    cy, cx = sum(ys) / len(cells), sum(xs) / len(cells)
    anchor = min(cells, key=lambda c: ((c[0] - cy) ** 2 + (c[1] - cx) ** 2, c))
    return GridObject(
        color=color,
        size=len(cells),
        bbox=(min(ys), min(xs), max(ys), max(xs)),
        centroid=(cy, cx),
        anchor=anchor,
    )


def _bbox_of(mask: np.ndarray) -> BBox:
    ys, xs = np.nonzero(mask)
    return int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())


def _most_common_color(grid: np.ndarray) -> int:
    values, counts = np.unique(grid, return_counts=True)
    return int(values[int(np.argmax(counts))])
