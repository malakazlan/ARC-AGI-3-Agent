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


# --- countdown_mask -------------------------------------------------------------

def attempt_with_bar(player_path: list[tuple[int, int]]) -> list[np.ndarray]:
    """Frames of one attempt: bottom row drains one cell per step; a player cell moves."""
    frames = []
    for t, (py, px) in enumerate(player_path):
        g = grid8()
        g[7, :] = 3
        g[7, :t] = 0             # countdown: cell x switches off at step x
        g[py, px] = 1
        frames.append(g)
    return frames


def test_countdown_mask_finds_cells_that_change_at_the_same_offsets_every_attempt():
    from arc3.perception import countdown_mask

    a1 = attempt_with_bar([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4)])
    a2 = attempt_with_bar([(1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (4, 3)])
    mask = countdown_mask([a1, a2])
    assert mask[7, :5].all()            # bar cells that drained in both attempts
    assert not mask[:7].any()           # the player never counts


def test_countdown_mask_tolerates_attempts_of_different_length():
    from arc3.perception import countdown_mask

    a1 = attempt_with_bar([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4), (3, 5)])
    a2 = attempt_with_bar([(1, 1), (2, 1), (3, 1)])
    mask = countdown_mask([a1, a2])
    assert mask[7, :2].all()
    assert not mask[:7].any()


def test_countdown_mask_needs_two_attempts():
    from arc3.perception import countdown_mask

    a1 = attempt_with_bar([(1, 1), (1, 2), (1, 3)])
    assert not countdown_mask([a1]).any()
    assert not countdown_mask([]).any()


def test_countdown_mask_ignores_cells_that_change_at_different_offsets():
    from arc3.perception import countdown_mask

    def attempt(offsets):
        frames = []
        for t in range(6):
            g = grid8()
            if t in offsets:
                g[0, 0] = 5
            frames.append(g)
        return frames

    assert not countdown_mask([attempt({1, 2}), attempt({3, 4})]).any()


def test_countdown_mask_uses_long_attempts_even_when_one_attempt_is_short():
    """A short attempt must not hide bar cells that only drain later in long attempts."""
    from arc3.perception import countdown_mask

    long_a = attempt_with_bar([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4), (3, 5)])
    long_b = attempt_with_bar([(1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (4, 3), (4, 4)])
    short = attempt_with_bar([(1, 1), (2, 1)])
    mask = countdown_mask([long_a, short, long_b])
    assert mask[7, :6].all()
    assert not mask[:7].any()


def test_incremental_attempt_signature_matches_batch():
    from arc3.perception import AttemptSignature, countdown_mask, countdown_mask_from_signatures

    a1 = attempt_with_bar([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4)])
    a2 = attempt_with_bar([(1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (4, 3)])
    sigs = []
    for frames in (a1, a2):
        sig = AttemptSignature()
        for frame in frames:
            sig.push(frame)
        sigs.append(sig)
    assert np.array_equal(countdown_mask_from_signatures(sigs, (8, 8)), countdown_mask([a1, a2]))
    assert sigs[0].length == 6


def test_countdown_mask_ignores_cells_replayed_with_identical_actions():
    """Same actions every attempt make the player trail look like a bar. No evidence, no mask."""
    from arc3.perception import countdown_mask

    path = [(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4)]
    a1 = attempt_with_bar(path)
    a2 = attempt_with_bar(path)
    actions = [[4, 4, 2, 2, 4]] * 2
    assert not countdown_mask([a1, a2], actions).any()


def test_countdown_mask_requires_differing_actions_at_each_offset():
    """Bar cells are masked only from the first offset where attempts took different actions."""
    from arc3.perception import countdown_mask

    a1 = attempt_with_bar([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4)])
    a2 = attempt_with_bar([(1, 1), (1, 2), (2, 2), (3, 2), (3, 3), (4, 3)])
    actions = [[4, 4, 2, 2, 4], [4, 2, 3, 4, 2]]   # first action identical, then different
    mask = countdown_mask([a1, a2], actions)
    assert not mask[7, 0]              # offset 1: both attempts pressed 4, no evidence
    assert mask[7, 1:5].all()          # offsets 2..5: actions differed, bar still drained
    assert not mask[:7].any()          # the two trails differ, nothing else masked


def test_countdown_mask_finds_a_bar_that_drains_and_refills():
    """ls20-style: a 4-cell bar drains one cell per step, refills at step 5, drains again. The
    sequence is identical in every attempt whatever the player did; the player differs."""
    from arc3.perception import countdown_mask

    def attempt(path):
        frames = []
        for t, (py, px) in enumerate(path):
            g = grid8()
            phase = t % 5                        # 0: full, 1..4: drained by phase cells
            g[7, 0:4] = 3
            g[7, 0:phase] = 0
            g[py, px] = 1
            frames.append(g)
        return frames

    a1 = attempt([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4), (4, 4), (5, 4), (5, 5), (5, 6), (6, 6)])
    a2 = attempt([(1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (4, 3), (4, 2), (4, 1), (5, 1), (6, 1), (6, 2)])
    actions = [[4, 4, 2, 2, 4, 2, 2, 4, 4, 2], [2, 2, 4, 4, 2, 3, 3, 2, 2, 4]]
    mask = countdown_mask([a1, a2], actions)
    assert mask[7, 0:4].all()
    assert not mask[:7].any()


def test_countdown_mask_ignores_a_trail_cell_entered_by_the_same_key_in_every_attempt():
    """A cell the player enters (and later leaves) at about the same step in two attempts by the
    same key press is the player's trail, not a bar, even if the attempts diverge afterwards."""
    from arc3.perception import countdown_mask

    def attempt(path):
        frames = []
        for (py, px) in path:
            g = grid8()
            g[py, px] = 1
            frames.append(g)
        return frames

    # both attempts step right into (1, 2) at offset 1 with key 4, then part ways; (1, 2) and
    # (1, 3) each change twice (entered, then left) at nearly the same offsets in both attempts
    a1 = attempt([(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 4), (4, 4)])
    a2 = attempt([(1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (2, 5), (3, 5)])
    actions = [[4, 4, 2, 2, 4, 2], [4, 4, 4, 2, 4, 2]]
    assert not countdown_mask([a1, a2], actions).any()


def test_countdown_mask_rejects_a_change_the_longer_attempt_never_made():
    """Cells that changed in the last steps of a short attempt and only much later in a longer
    one are not a bar: the longer attempt had every chance to show the change then and did not."""
    from arc3.perception import countdown_mask

    def attempt(n, drain_at):
        frames = []
        for t in range(n):
            g = grid8()
            if drain_at is not None:
                for k, (y, x) in enumerate([(7, 0), (7, 1), (7, 2)]):
                    if t >= drain_at + (k + 1) // 2:
                        g[y, x] = 3
            g[1, 1 + (t % 3)] = 1
            frames.append(g)
        return frames

    short = attempt(8, drain_at=6)        # (7,0) at offset 6, (7,1) and (7,2) at 7: its last steps
    long = attempt(30, drain_at=20)       # lived far longer and changed those cells much later
    actions = [[4, 2, 3, 1, 4, 2, 3], [2, 4, 1, 3, 2, 4] * 4 + [2, 4, 1, 3, 2]]
    assert not countdown_mask([short, long], actions)[7].any()


def test_countdown_mask_requires_a_drain_front_that_sweeps_along_the_bar():
    """Bar cells drain in order along the bar's long axis. A player's early trail (an L of cells
    first changed at steps 3, 1, 7 and 2 in every attempt) has no such order and is not masked."""
    from arc3.perception import countdown_mask

    def attempt(keys):
        # cells first change at fixed offsets whatever the key pressed; two cells then flip back
        first = {(1, 0): 3, (1, 1): 1, (1, 2): 7, (2, 0): 2}
        frames = []
        for t in range(12):
            g = grid8()
            for cell, o in first.items():
                if t >= o:
                    g[cell] = 1
            if t >= 4:
                g[1, 0] = 0
            if t >= 8:
                g[1, 2] = 0
            frames.append(g)
        return frames

    a1 = attempt(None); a2 = attempt(None)
    actions = [[1, 3, 1, 4, 2, 3, 4, 1, 2, 3, 4], [2, 2, 2, 1, 4, 4, 2, 3, 1, 1, 3]]
    assert not countdown_mask([a1, a2], actions).any()
