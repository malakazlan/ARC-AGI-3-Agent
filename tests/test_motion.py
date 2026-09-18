"""Translation detection and the avatar model on synthetic 8x8 grids."""
from __future__ import annotations

import numpy as np

from arc3.perception import find_translation
from arc3.world_model import AvatarModel


def grid8():
    return np.zeros((8, 8), dtype=np.int8)


def blob(g, y, x):
    """A two-colour 2x2 avatar with its top-left at (y, x)."""
    g[y, x] = 1
    g[y, x + 1] = 2
    g[y + 1, x] = 2
    g[y + 1, x + 1] = 1


# --- find_translation --------------------------------------------------------------

def test_single_blob_moving_right_is_found_with_its_cells():
    a, b = grid8(), grid8()
    blob(a, 3, 3)
    blob(b, 3, 4)
    tr = find_translation(a, b)
    assert tr is not None
    assert (tr.dy, tr.dx) == (0, 1)
    assert tr.explained >= 0.99
    assert set(tr.cells) == {(3, 3), (3, 4), (4, 3), (4, 4)}


def test_no_change_gives_none():
    a = grid8()
    blob(a, 3, 3)
    assert find_translation(a, a.copy()) is None


def test_masked_bar_cells_do_not_count():
    a, b = grid8(), grid8()
    blob(a, 3, 3)
    blob(b, 3, 4)
    a[7, :] = 6
    b[7, :] = 6
    b[7, 0] = 0                      # the bar drained one cell
    mask = np.zeros((8, 8), dtype=bool)
    mask[7, :] = True
    tr = find_translation(a, b, mask)
    assert tr is not None and (tr.dy, tr.dx) == (0, 1) and tr.explained >= 0.99


def test_unrelated_change_is_not_a_translation():
    a, b = grid8(), grid8()
    b[0, 0] = 9
    b[5, 5] = 4
    tr = find_translation(a, b)
    assert tr is None or tr.explained < 0.5


def test_blob_moving_onto_a_different_background_colour():
    a, b = grid8(), grid8()
    a[:, 4:] = 3                     # right half is colour 3
    b[:, 4:] = 3
    blob(a, 2, 2)
    b[2:4, 2:4] = 0                  # vacated cells revert to the left background
    blob(b, 2, 3)
    b[2, 3] = 1; b[2, 4] = 2; b[3, 3] = 2; b[3, 4] = 1
    tr = find_translation(a, b)
    assert tr is not None and (tr.dy, tr.dx) == (0, 1)


# --- AvatarModel ---------------------------------------------------------------------

def sequence(moves):
    """Frames for a list of (action, dy, dx) moves of a blob starting at (3, 3)."""
    frames, actions = [], []
    y, x = 3, 3
    g = grid8(); blob(g, y, x); frames.append(g)
    for action, dy, dx in moves:
        y, x = y + dy, x + dx
        g = grid8(); blob(g, y, x)
        frames.append(g); actions.append(action)
    return frames, actions


def test_avatar_and_key_vectors_are_learned_after_three_votes():
    frames, actions = sequence([(4, 0, 1), (4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0), (2, 1, 0)])
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    assert model.vector(4) == (0, 1)
    assert model.vector(2) == (1, 0)
    assert model.vector(1) is None                 # never seen
    assert model.confident
    assert len(model.avatar_cells(frames[-1])) == 4


def test_no_op_moves_do_not_vote_and_do_not_break_the_model():
    frames, actions = sequence([(4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0)])
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    model.observe(frames[-1], 1, frames[-1])       # blocked: nothing changed
    assert model.vector(4) == (0, 1)
    assert model.vector(1) is None
    assert model.blocked_votes == 1


def test_contradicting_vectors_leave_the_key_unknown():
    frames, actions = sequence([(4, 0, 1), (4, 1, 0), (4, 0, 1), (4, 1, 0)])
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    assert model.vector(4) is None


def test_predicted_position_after_a_known_move():
    frames, actions = sequence([(4, 0, 1), (4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0), (2, 1, 0)])
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    cells = model.avatar_cells(frames[-1])
    moved = model.predict_cells(cells, 4)
    assert moved == {(y, x + 1) for (y, x) in cells}


def test_uniform_block_moving_one_cell_is_not_confused_with_its_own_width():
    a, b = grid8(), grid8()
    a[3, 1:5] = 5                    # a 1x4 bar of one colour
    b[3, 2:6] = 5                    # moved right by one
    tr = find_translation(a, b)
    assert tr is not None and (tr.dy, tr.dx) == (0, 1)
    assert set(tr.cells) == {(3, 1), (3, 2), (3, 3), (3, 4)}


def test_two_colour_avatar_is_one_translation_even_when_segmented_as_two_objects():
    a, b = grid8(), grid8()
    a[2, 2] = 1; a[2, 3] = 2; a[3, 2] = 2; a[3, 3] = 1
    b[3, 2] = 1; b[3, 3] = 2; b[4, 2] = 2; b[4, 3] = 1
    tr = find_translation(a, b)
    assert tr is not None and (tr.dy, tr.dx) == (1, 0) and len(tr.cells) == 4


def test_static_objects_elsewhere_do_not_disturb_the_translation():
    a, b = grid8(), grid8()
    a[0, 0:3] = 7; b[0, 0:3] = 7     # a static wall
    a[6, 6] = 9; b[6, 6] = 9         # a static dot
    a[3, 1:5] = 5; b[3, 2:6] = 5
    tr = find_translation(a, b)
    assert tr is not None and (tr.dy, tr.dx) == (0, 1) and tr.explained >= 0.99


def ring(g, y, x, eye):
    """A 3x3 avatar: colour-1 ring with an 'eye' of colour `eye` in the middle, top-left (y, x)."""
    g[y:y + 3, x:x + 3] = 1
    g[y + 1, x + 1] = eye


def test_avatar_that_changes_appearance_is_still_tracked_by_continuity():
    """A facing sprite: the eye changes colour when the avatar moves. Tracking must follow it."""
    frames = []
    for k in range(4):
        g = grid8(); ring(g, 2, k, 2); frames.append(g)
    down = grid8(); ring(down, 3, 3, 2)
    model = AvatarModel()
    for k in range(3):
        model.observe(frames[k], 4, frames[k + 1])
    model.observe(frames[3], 2, down)             # a second key, so control is established
    model.observe(down, 1, frames[3])
    model.observe(frames[3], 2, down)
    model.observe(down, 1, frames[3])
    before = frames[-1]
    cells = model.avatar_cells(before)
    assert len(cells) == 9
    after = grid8(); ring(after, 2, 4, 3)       # moved right by one, eye now colour 3
    assert model.observe(before, 4, after) == "moved"
    assert model.last_cells == {(y, x + 1) for (y, x) in cells}
    assert model.avatar_cells(after) == model.last_cells


def test_blocked_move_keeps_the_avatar_where_it_was_even_if_the_frame_changed_elsewhere():
    frames, actions = sequence([(4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0), (4, 0, 1), (2, 1, 0)])
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    before = frames[-1]
    cells = model.avatar_cells(before)
    after = before.copy()
    after[0, 0] = 9                            # something unrelated changed
    outcome = model.observe(before, 4, after)
    assert outcome == "blocked"
    assert model.avatar_cells(after) == cells


def test_object_that_drifts_regardless_of_the_key_is_not_the_avatar():
    """A bar slides down every step whatever we press; a small blob obeys keys 3 and 4."""
    frames, actions = [], []
    bar_y, x = 0, 3
    for k, (action, dx) in enumerate([(4, 1), (3, -1), (4, 1), (3, -1), (4, 1), (3, -1), (4, 1)]):
        g = grid8()
        g[bar_y, 0:8] = 7             # the drifting bar (moves before we act)
        g[6, x] = 1                   # the controllable blob
        frames.append(g)
        if k < 6:
            actions.append(action)
        bar_y = (bar_y + 1) % 6
        x += dx
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    assert model.vector(4) == (0, 1)
    assert model.vector(3) == (0, -1)
    assert len(model.avatar_cells(frames[-1])) == 1
    assert (7,) not in {tuple(sig[:1]) for sig in model.controllable}


def test_one_key_alone_cannot_establish_control():
    frames, actions = sequence([(4, 0, 1)] * 3)
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    assert not model.confident
