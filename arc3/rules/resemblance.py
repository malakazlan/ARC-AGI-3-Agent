"""T1 match_display: a changeable object resembles a static one (design v2, section 5).

A "display" is a framed region: an object whose bounding box contains other cells. When
something inside a frame changed under our actions, every other frame of the same shape family
and size is a candidate target; the pair scores by frame match, inner-size match and colour
family. Progress is the share of inner properties (colour, shape) that already match.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from arc3.perception import GridObject, segment_objects, shape_key

BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class DisplayPair:
    changeable_box: BBox
    static_box: BBox
    score: float


def _frames(grid: np.ndarray, bg: int) -> list[GridObject]:
    """Objects whose bounding box has holes: candidate frames/panels."""
    out = []
    for obj in segment_objects(grid, background=bg):
        y0, x0, y1, x1 = obj.bbox
        area = (y1 - y0 + 1) * (x1 - x0 + 1)
        if area > obj.size and area >= 4:
            out.append(obj)
    return out


def _inner(grid: np.ndarray, box: BBox, frame_colour: int) -> np.ndarray:
    y0, x0, y1, x1 = box
    inner = grid[y0:y1 + 1, x0:x1 + 1].copy()
    inner[inner == frame_colour] = -1
    return inner


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
        cy0, cx0, cy1, cx1 = c.bbox
        for s in frames:
            if s.bbox == c.bbox or _contains(s.bbox, changed_cells):
                continue
            sy0, sx0, sy1, sx1 = s.bbox
            same_box = (cy1 - cy0, cx1 - cx0) == (sy1 - sy0, sx1 - sx0)
            same_frame_shape = shape_key(s) == shape_key(c)
            if not same_box:
                continue
            score = 1.0 + (1.0 if same_frame_shape else 0.0) + (0.5 if s.color == c.color else 0.0)
            pairs.append(DisplayPair(c.bbox, s.bbox, score))
    pairs.sort(key=lambda p: -p.score)
    return pairs


def match_progress(grid: np.ndarray, pair: DisplayPair) -> float:
    """Share of inner cells of the changeable frame that equal the static frame's inner cells."""
    frame_colour = int(grid[pair.static_box[0], pair.static_box[1]])
    a = _inner(grid, pair.changeable_box, frame_colour)
    b = _inner(grid, pair.static_box, frame_colour)
    if a.shape != b.shape:
        return 0.0
    considered = (a != -1) | (b != -1)
    if not considered.any():
        return 1.0
    return float(((a == b) & considered).sum() / considered.sum())
