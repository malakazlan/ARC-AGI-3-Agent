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
    frames, actions = sequence([(4, 0, 1), (4, 0, 1), (4, 0, 1)])
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
    frames, actions = sequence([(4, 0, 1)] * 3)
    model = AvatarModel()
    for k, action in enumerate(actions):
        model.observe(frames[k], action, frames[k + 1])
    cells = model.avatar_cells(frames[-1])
    moved = model.predict_cells(cells, 4)
    assert moved == {(y, x + 1) for (y, x) in cells}
