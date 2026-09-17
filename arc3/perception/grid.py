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
    return GridObject(
        color=color,
        size=len(cells),
        bbox=(min(ys), min(xs), max(ys), max(xs)),
        centroid=(sum(ys) / len(cells), sum(xs) / len(cells)),
    )


def _bbox_of(mask: np.ndarray) -> BBox:
    ys, xs = np.nonzero(mask)
    return int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())


def _most_common_color(grid: np.ndarray) -> int:
    values, counts = np.unique(grid, return_counts=True)
    return int(values[int(np.argmax(counts))])
