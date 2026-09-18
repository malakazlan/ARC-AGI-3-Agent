"""Events read from a frame diff: what happened, at object level (design v2, section 3).

moved(signature, vector) | prop_changed(prop, old, new, cells) | appeared(signature) |
disappeared(signature). Masked cells (energy bar) never produce events.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from arc3.perception import GridObject, find_translations, segment_objects, shape_key


@dataclass(frozen=True)
class Event:
    kind: str
    signature: tuple = ()
    vector: tuple[int, int] | None = None
    prop: str | None = None
    old: object = None
    new: object = None
    cells: tuple[tuple[int, int], ...] = field(default=())


def _sig(obj: GridObject) -> tuple:
    return (int(obj.color), shape_key(obj), int(obj.size))


def _bg(grid: np.ndarray) -> int:
    vals, counts = np.unique(grid, return_counts=True)
    return int(vals[int(np.argmax(counts))])


def extract_events(before: np.ndarray, after: np.ndarray, mask: np.ndarray | None = None) -> list[Event]:
    if before.shape != after.shape:
        return [Event("reshaped")]
    diff = before != after
    if mask is not None:
        diff &= ~mask
    if not diff.any():
        return []
    b, a = before, after
    if mask is not None and mask.any():
        fill = _bg(before[~mask]) if (~mask).any() else 0
        b = before.copy(); a = after.copy()
        b[mask] = fill; a[mask] = fill
    bg = _bg(b)
    objs_b = [o for o in segment_objects(b, background=bg) if _touches(o, diff)]
    objs_a = [o for o in segment_objects(a, background=bg) if _touches(o, diff)]
    events: list[Event] = []
    used_a: set[int] = set()
    used_b: set[int] = set()

    # 1. translations
    for g in find_translations(b, a, mask):
        moved_cells = set(g.cells)
        for i, ob in enumerate(objs_b):
            if i in used_b or not moved_cells.issuperset(ob.cells):
                continue
            used_b.add(i)
            for j, oa in enumerate(objs_a):
                if j not in used_a and _sig(oa) == _sig(ob) and oa.anchor == (ob.anchor[0] + g.dy, ob.anchor[1] + g.dx):
                    used_a.add(j)
                    break
            events.append(Event("moved", _sig(ob), (g.dy, g.dx), cells=ob.cells))

    # 2. in-place property changes: same bbox, different colour or shape
    for i, ob in enumerate(objs_b):
        if i in used_b:
            continue
        for j, oa in enumerate(objs_a):
            if j in used_a:
                continue
            if oa.bbox == ob.bbox and (oa.color != ob.color or shape_key(oa) != shape_key(ob)):
                used_b.add(i); used_a.add(j)
                if oa.color != ob.color and shape_key(oa) == shape_key(ob):
                    events.append(Event("prop_changed", _sig(ob), prop="colour", old=int(ob.color), new=int(oa.color), cells=ob.cells))
                else:
                    events.append(Event("prop_changed", _sig(ob), prop="shape", old=shape_key(ob), new=shape_key(oa), cells=ob.cells))
                break

    # 3. leftovers
    for i, ob in enumerate(objs_b):
        if i not in used_b:
            events.append(Event("disappeared", _sig(ob), cells=ob.cells))
    for j, oa in enumerate(objs_a):
        if j not in used_a:
            events.append(Event("appeared", _sig(oa), cells=oa.cells))
    return events


def _touches(obj: GridObject, diff: np.ndarray) -> bool:
    return any(diff[y, x] for (y, x) in obj.cells)
