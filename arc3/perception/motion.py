"""Rigid translations between two frames, read at object level.

Both frames are segmented (bar cells excluded); objects are matched by colour, shape and size,
nearest first. Matched objects that moved are grouped by displacement: each group is one
Translation. This is how a player sees it: "that thing moved one cell right", never "the
vacated column reappeared four cells to the right", which a cell-level rule cannot tell apart
for uniform blocks.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from arc3.perception.grid import GridObject, segment_objects, shape_key

WINDOW = 8  # maximum displacement accepted, in cells (ls20 moves 5 per key)


@dataclass(frozen=True)
class Translation:
    dy: int
    dx: int
    explained: float  # share of changed cells covered by this group's objects
    cells: tuple[tuple[int, int], ...]  # cells of the moved objects in `before`
    signatures: tuple[tuple, ...] = ()  # (colour, shape key, size) of each moved object


def find_translations(before: np.ndarray, after: np.ndarray, mask: np.ndarray | None = None,
                      window: int = WINDOW) -> list[Translation]:
    """All displacement groups between the frames, most explanatory first. [] when nothing moved."""
    if before.shape != after.shape:
        return []
    diff = before != after
    if mask is not None:
        diff &= ~mask
    if not diff.any():
        return []
    b, a = before, after
    if mask is not None and mask.any():
        fill = _most_common(before[~mask]) if (~mask).any() else 0
        b = before.copy(); a = after.copy()
        b[mask] = fill; a[mask] = fill
    bg = _most_common(b)
    pairs = _match(segment_objects(b, background=bg), segment_objects(a, background=bg))
    by_d: dict[tuple[int, int], list] = defaultdict(list)
    for ob, oa, d in pairs:
        if d != (0, 0) and max(abs(d[0]), abs(d[1])) <= window:
            by_d[d].append((ob, oa))
    total = float(diff.sum())
    groups: list[Translation] = []
    for d, chosen in by_d.items():
        covered = np.zeros(before.shape, dtype=bool)
        cells: list[tuple[int, int]] = []
        sigs = []
        for ob, oa in chosen:
            for y, x in ob.cells:
                covered[y, x] = True
                cells.append((int(y), int(x)))
            for y, x in oa.cells:
                covered[y, x] = True
            sigs.append((int(ob.color), shape_key(ob), int(ob.size)))
        explained = float((diff & covered).sum() / total)
        groups.append(Translation(int(d[0]), int(d[1]), explained, tuple(sorted(cells)), tuple(sigs)))
    groups.sort(key=lambda g: -g.explained)
    return groups


def find_translation(before: np.ndarray, after: np.ndarray, mask: np.ndarray | None = None,
                     window: int = WINDOW) -> Translation | None:
    """The single most explanatory displacement group, or None."""
    groups = find_translations(before, after, mask, window)
    return groups[0] if groups else None


def _match(objs_b: list[GridObject], objs_a: list[GridObject]) -> list[tuple[GridObject, GridObject, tuple[int, int]]]:
    """Pair objects with the same (colour, shape, size), nearest anchors first."""
    by_sig_b: dict[tuple, list[GridObject]] = defaultdict(list)
    by_sig_a: dict[tuple, list[GridObject]] = defaultdict(list)
    for o in objs_b:
        by_sig_b[(o.color, shape_key(o), o.size)].append(o)
    for o in objs_a:
        by_sig_a[(o.color, shape_key(o), o.size)].append(o)
    pairs = []
    for sig, lb in by_sig_b.items():
        la = list(by_sig_a.get(sig, []))
        if not la:
            continue
        candidates = sorted(
            ((abs(ob.anchor[0] - oa.anchor[0]) + abs(ob.anchor[1] - oa.anchor[1]), i, j)
             for i, ob in enumerate(lb) for j, oa in enumerate(la)))
        used_b: set[int] = set(); used_a: set[int] = set()
        for _, i, j in candidates:
            if i in used_b or j in used_a:
                continue
            used_b.add(i); used_a.add(j)
            ob, oa = lb[i], la[j]
            d = (oa.anchor[0] - ob.anchor[0], oa.anchor[1] - ob.anchor[1])
            pairs.append((ob, oa, d))
    return pairs


def _most_common(values: np.ndarray) -> int:
    vals, counts = np.unique(values, return_counts=True)
    return int(vals[int(np.argmax(counts))])
