"""Perception on synthetic 8x8 grids. No game engine."""
from __future__ import annotations

import numpy as np
import pytest

from arc3.perception import frame_diff, segment_objects, state_hash, volatility_mask


def grid8(fill: int = 0) -> np.ndarray:
    return np.full((8, 8), fill, dtype=np.int8)


# --- frame_diff -----------------------------------------------------------------

def test_frame_diff_identical_grids_reports_no_change():
    a = grid8()
    diff = frame_diff(a, a.copy())
    assert diff.changed == 0
    assert not diff.mask.any()
    assert diff.bbox is None


def test_frame_diff_reports_changed_cells_and_bbox():
    a = grid8()
    b = a.copy()
    b[2, 3] = 5
    b[5, 6] = 7
    diff = frame_diff(a, b)
    assert diff.changed == 2
    assert diff.mask[2, 3] and diff.mask[5, 6]
    assert diff.bbox == (2, 3, 5, 6)  # y0, x0, y1, x1 inclusive


def test_frame_diff_shape_mismatch_counts_every_cell():
    a = grid8()
    b = np.zeros((6, 6), dtype=np.int8)
    diff = frame_diff(a, b)
    assert diff.changed == 64
    assert diff.mask.shape == (8, 8)


# --- segment_objects ------------------------------------------------------------

def test_segment_objects_finds_two_blobs_over_background():
    g = grid8()
    g[1:3, 1:3] = 4          # 2x2 block, color 4
    g[5, 2:6] = 9            # 1x4 line, color 9
    objs = segment_objects(g, background=0)
    assert len(objs) == 2
    by_color = {o.color: o for o in objs}
    assert by_color[4].size == 4 and by_color[4].bbox == (1, 1, 2, 2)
    assert by_color[9].size == 4 and by_color[9].bbox == (5, 2, 5, 5)


def test_segment_objects_separates_same_color_when_not_connected():
    g = grid8()
    g[0, 0] = 3
    g[7, 7] = 3
    objs = segment_objects(g, background=0)
    assert len(objs) == 2
    assert all(o.color == 3 and o.size == 1 for o in objs)


def test_segment_objects_diagonal_cells_are_separate_with_4_connectivity():
    g = grid8()
    g[3, 3] = 2
    g[4, 4] = 2
    assert len(segment_objects(g, background=0, connectivity=4)) == 2
    assert len(segment_objects(g, background=0, connectivity=8)) == 1


def test_segment_objects_default_background_is_most_common_color():
    g = grid8(fill=7)
    g[2, 2] = 1
    objs = segment_objects(g)
    assert len(objs) == 1 and objs[0].color == 1


def test_segment_objects_are_sorted_largest_first_then_position():
    g = grid8()
    g[6, 6] = 1
    g[0:2, 0:3] = 2
    objs = segment_objects(g, background=0)
    assert [o.size for o in objs] == [6, 1]
    assert objs[0].centroid == pytest.approx((0.5, 1.0))


# --- volatility_mask ------------------------------------------------------------

def test_volatility_mask_marks_cells_that_change_across_frames():
    frames = [grid8() for _ in range(4)]
    for t, f in enumerate(frames):
        f[0, 0] = t % 3          # blinking cell
        f[7, 7] = 5              # constant non-background cell
    mask = volatility_mask(frames)
    assert mask.shape == (8, 8)
    assert mask[0, 0]
    assert not mask[7, 7]
    assert mask.sum() == 1


def test_volatility_mask_of_single_frame_is_all_false():
    assert not volatility_mask([grid8()]).any()


def test_volatility_mask_ignores_frames_of_other_shapes():
    frames = [grid8(), np.zeros((4, 4), dtype=np.int8), grid8()]
    assert not volatility_mask(frames).any()


# --- state_hash -----------------------------------------------------------------

def test_state_hash_is_stable_for_equal_grids():
    a = grid8()
    a[1, 1] = 3
    assert state_hash(a) == state_hash(a.copy())


def test_state_hash_changes_when_an_unmasked_cell_changes():
    a = grid8()
    b = a.copy()
    b[4, 4] = 9
    assert state_hash(a) != state_hash(b)


def test_state_hash_ignores_masked_cells():
    a = grid8()
    b = a.copy()
    b[0, 0] = 9
    mask = np.zeros((8, 8), dtype=bool)
    mask[0, 0] = True
    assert state_hash(a, mask) == state_hash(b, mask)
    assert state_hash(a, mask) != state_hash(a)   # masking changes the key space on purpose


def test_state_hash_depends_on_shape():
    assert state_hash(np.zeros((8, 8), dtype=np.int8)) != state_hash(np.zeros((4, 16), dtype=np.int8))


def test_segment_objects_anchor_is_a_cell_inside_the_object():
    g = grid8()
    g[0, 0:5] = 6            # L shape whose centroid is outside the object
    g[1:5, 0] = 6
    (obj,) = segment_objects(g, background=0)
    ay, ax = obj.anchor
    assert g[ay, ax] == 6
    assert obj.centroid != obj.anchor
