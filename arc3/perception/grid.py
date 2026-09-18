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
    cells: tuple[tuple[int, int], ...] = ()  # every (y, x) of the object, sorted


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
    """Per-attempt record of how each cell changed: cell -> ((offset, new value), ...).

    Built incrementally from consecutive frames so no frame buffer is needed. Cells that change
    more than MAX_CHANGES times are dropped (None) and never revived.
    """

    MAX_CHANGES = 8

    def __init__(self) -> None:
        self.length = 0
        self.shape: tuple[int, int] | None = None
        self.actions: list[object] = []  # actions[o] produced frame o; actions[0] is None
        self._prev: np.ndarray | None = None
        self._cells: dict[tuple[int, int], list[tuple[int, int]] | None] = {}

    def push(self, frame: np.ndarray, action: object = None) -> None:
        if self._prev is not None and frame.shape == self._prev.shape:
            offset = self.length
            for y, x in zip(*np.nonzero(frame != self._prev)):
                cell = (int(y), int(x))
                seq = self._cells.get(cell, [])
                if seq is None:
                    continue
                if len(seq) >= self.MAX_CHANGES:
                    self._cells[cell] = None
                    continue
                seq.append((offset, int(frame[y, x])))
                self._cells[cell] = seq
        self.shape = (int(frame.shape[0]), int(frame.shape[1]))
        self.actions.append(None if self._prev is None else action)
        self._prev = frame
        self.length += 1

    @property
    def sequences(self) -> dict[tuple[int, int], tuple[tuple[int, int], ...]]:
        return {c: tuple(s) for c, s in self._cells.items() if s}

    @property
    def once(self) -> dict[tuple[int, int], tuple[int, int]]:
        return {c: s[0] for c, s in self._cells.items() if s and len(s) == 1}

    def changed(self, cell: tuple[int, int]) -> bool:
        return cell in self._cells


def countdown_mask_from_signatures(signatures: list[AttemptSignature], shape: tuple[int, int],
                                   min_attempts: int = 2, require_independence: bool = True) -> np.ndarray:
    """Cells that behave like an energy or countdown bar across attempts of the same level.

    A bar cell's first change (offset and value) is the same in every attempt, up to a small
    tolerance, as far as the shorter attempt lets us compare, and it changed in at least two
    attempts. The change must be independent of what the agent did: the actions that led up
    to it differ between supporting attempts (an identical replay would make the player's own
    trail look like a bar; unknown actions, None, count as differing). Isolated cells are
    ignored: bar cells come in connected groups whose first offsets are staggered and sweep
    monotonically along the bar.
    """
    shape = (int(shape[0]), int(shape[1]))
    mask = np.zeros(shape, dtype=bool)
    signatures = [s for s in signatures if s.length >= 2 and s.shape == shape]
    if len(signatures) < min_attempts:
        return mask
    seqs = [s.sequences for s in signatures]
    consistent: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {}
    seen: set[tuple[int, int]] = set()
    for i, seq_map in enumerate(seqs):
        for cell, seq in seq_map.items():
            if cell in seen:
                continue
            seen.add(cell)
            support = []
            ok = True
            for j, sig in enumerate(signatures):
                other = seqs[j].get(cell, ())
                if sig.changed(cell) and not other:
                    ok = False  # changed too often there
                    break
                for k, sig_k in enumerate(signatures):
                    if k <= j:
                        continue
                    window = min(sig.length, sig_k.length)
                    a = tuple(p for p in other if p[0] < window)
                    b = tuple(p for p in seqs[k].get(cell, ()) if p[0] < window)
                    if not _same_drain(a, b, sig.length, sig_k.length):
                        ok = False
                        break
                if not ok:
                    break
                if other:
                    support.append(j)
            if not ok or len(support) < min_attempts:
                continue
            # independence is judged at the change we compared (each attempt's first change):
            # the action histories that led there must differ, an identical replay proves nothing
            histories = set()
            unknown = False
            for j in support:
                sig = signatures[j]
                first = seqs[j][cell][0][0]
                prefix = tuple(sig.actions[1:first + 1])
                if len(prefix) < first or None in prefix:
                    unknown = True
                histories.add(prefix)
            if not require_independence or unknown or len(histories) >= 2:
                consistent[cell] = seq
    if not consistent:
        return mask
    candidates = np.zeros(shape, dtype=np.int8)
    for (y, x) in consistent:
        candidates[y, x] = 1
    for group in segment_objects(candidates, background=0):
        cells = [c for c in consistent if group.bbox[0] <= c[0] <= group.bbox[2]
                 and group.bbox[1] <= c[1] <= group.bbox[3]]
        firsts = {c: consistent[c][0][0] for c in cells}
        if group.size >= 2 and len(set(firsts.values())) >= 2 and _drain_front_in_order(firsts):
            for y, x in cells:
                mask[y, x] = True
    return mask


def _drain_front_in_order(firsts: dict[tuple[int, int], int]) -> bool:
    """A bar drains as a front that sweeps along its long axis: within every row (of a wide
    group) or column (of a tall group) the first-change offsets are monotone. A player's trail
    changes its cells in walking order, which is not monotone along either axis."""
    ys = [y for y, _ in firsts]; xs = [x for _, x in firsts]
    wide = (max(xs) - min(xs)) >= (max(ys) - min(ys))
    lines: dict[int, list[tuple[int, int]]] = {}
    for (y, x), o in firsts.items():
        along, across = (x, y) if wide else (y, x)
        lines.setdefault(across, []).append((along, o))
    for pts in lines.values():
        pts.sort()
        offsets = [o for _, o in pts]
        inc = all(a <= b for a, b in zip(offsets, offsets[1:]))
        dec = all(a >= b for a, b in zip(offsets, offsets[1:]))
        if not (inc or dec):
            return False
    return True


DRAIN_TOLERANCE = 2  # actions; a free move (conveyor) shifts a bar by one or two


def _same_drain(a: tuple, b: tuple, len_a: int, len_b: int) -> bool:
    """Two change sequences of one cell (cut to the shorter attempt's window) agree when their
    first change happens at about the same offset with the same value. Later changes (refills)
    may drift by a free action or two. When only one attempt shows a change inside the window,
    the other must have ended before it could have shown it too."""
    if not a and not b:
        return True
    if not a or not b:
        first = (a or b)[0][0]
        silent_length = len_b if a else len_a
        return silent_length - first <= DRAIN_TOLERANCE  # the silent attempt ended right there
    return abs(a[0][0] - b[0][0]) <= DRAIN_TOLERANCE and a[0][1] == b[0][1]


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
        cells=tuple(sorted(cells)),
    )


def _bbox_of(mask: np.ndarray) -> BBox:
    ys, xs = np.nonzero(mask)
    return int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())


def _most_common_color(grid: np.ndarray) -> int:
    values, counts = np.unique(grid, return_counts=True)
    return int(values[int(np.argmax(counts))])
