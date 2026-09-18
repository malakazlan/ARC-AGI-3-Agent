"""T1 match_display: a changeable display resembles a static one (design v2, section 5).

A display is a hollow object: a frame or box whose bounding box contains other cells. When
something inside a frame changed under our actions, every other hollow frame is a candidate
target, scored by frame colour, box size and inner colour. Progress compares the inner glyphs
by colour and by scale-free shape, because targets are often drawn smaller than the panel.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from arc3.perception import GridObject, segment_objects

BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class DisplayPair:
    changeable_box: BBox
    static_box: BBox
    score: float


def normalized_shape(cells: frozenset) -> tuple[str, ...]:
    """Occupancy pattern of a cell set, reduced by its integer scale (an L drawn at 2x and 1x
    give the same pattern). Rows are strings of 0/1."""
    if not cells:
        return ()
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    y0, x0 = min(ys), min(xs)
    h, w = max(ys) - y0 + 1, max(xs) - x0 + 1
    occ = np.zeros((h, w), dtype=bool)
    for y, x in cells:
        occ[y - y0, x - x0] = True
    for s in range(min(h, w), 1, -1):
        if h % s or w % s:
            continue
        blocks = occ.reshape(h // s, s, w // s, s)
        uniform = np.all(blocks == blocks[:, :1, :, :1], axis=(1, 3))
        if uniform.all():
            occ = blocks[:, 0, :, 0]
            break
    return tuple("".join("1" if v else "0" for v in row) for row in occ)


def _frames(grid: np.ndarray, bg: int) -> list[GridObject]:
    """Objects whose bounding box has holes: candidate frames or panels."""
    out = []
    for obj in segment_objects(grid, background=bg):
        y0, x0, y1, x1 = obj.bbox
        area = (y1 - y0 + 1) * (x1 - x0 + 1)
        if area > obj.size and area >= 4:
            out.append(obj)
    return out


def _inner_objects(grid: np.ndarray, box: BBox, frame_colour: int) -> list[GridObject]:
    """Glyph objects inside a frame: everything that is neither the frame nor the interior's
    floor colour. A single-colour interior is itself the glyph."""
    y0, x0, y1, x1 = box
    inner = grid[y0:y1 + 1, x0:x1 + 1].copy()
    inner[inner == frame_colour] = -1
    interior = inner[inner != -1]
    if interior.size == 0:
        return []
    vals, counts = np.unique(interior, return_counts=True)
    bg = -1 if len(vals) == 1 else int(vals[int(np.argmax(counts))])
    objs = [o for o in segment_objects(inner, background=bg) if o.color != -1]
    objs.sort(key=lambda o: -o.size)
    return objs


def _contains(box: BBox, cells: frozenset) -> bool:
    y0, x0, y1, x1 = box
    return any(y0 <= y <= y1 and x0 <= x <= x1 for (y, x) in cells)


def display_pairs(grid: np.ndarray, changed_cells: frozenset) -> list[DisplayPair]:
    """Pairs (changeable frame containing the change, static frame that resembles it), best first."""
    vals, counts = np.unique(grid, return_counts=True)
    bg = int(vals[int(np.argmax(counts))])
    frames = _frames(grid, bg)
    changeable = [f for f in frames if _contains(f.bbox, changed_cells)]
    pairs: list[DisplayPair] = []
    for c in changeable:
        c_inner = _inner_objects(grid, c.bbox, int(c.color))
        if not c_inner:
            continue
        cy0, cx0, cy1, cx1 = c.bbox
        for s in frames:
            if s.bbox == c.bbox or _contains(s.bbox, changed_cells):
                continue
            s_inner = _inner_objects(grid, s.bbox, int(s.color))
            if not s_inner:
                continue
            sy0, sx0, sy1, sx1 = s.bbox
            score = 0.0
            score += 1.0 if s.color == c.color else 0.0
            score += 1.0 if (cy1 - cy0, cx1 - cx0) == (sy1 - sy0, sx1 - sx0) else 0.5
            score += 0.5 if s_inner[0].color == c_inner[0].color else 0.0
            if score >= 1.5:
                pairs.append(DisplayPair(c.bbox, s.bbox, score))
    pairs.sort(key=lambda p: -p.score)
    return pairs


def match_progress(grid: np.ndarray, pair: DisplayPair) -> float:
    """Share of inner-glyph properties (colour, scale-free shape) that already match."""
    c_colour = int(grid[pair.changeable_box[0], pair.changeable_box[1]])
    s_colour = int(grid[pair.static_box[0], pair.static_box[1]])
    c_inner = _inner_objects(grid, pair.changeable_box, c_colour)
    s_inner = _inner_objects(grid, pair.static_box, s_colour)
    if not c_inner or not s_inner:
        return 0.0
    a, b = c_inner[0], s_inner[0]
    matched = 0
    matched += int(a.color == b.color)
    matched += int(normalized_shape(frozenset(a.cells)) == normalized_shape(frozenset(b.cells)))
    return matched / 2.0
