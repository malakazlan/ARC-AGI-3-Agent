"""Passability learned per target-cell colour, and move prediction from it."""
from __future__ import annotations

import numpy as np

from arc3.world_model import PassabilityModel, predict_move


def test_three_blocks_make_a_colour_impassable():
    m = PassabilityModel()
    for _ in range(3):
        m.vote(2, "blocks")
    assert m.passable(2) is False
    assert m.known(2)


def test_three_passes_make_a_colour_passable():
    m = PassabilityModel()
    for _ in range(3):
        m.vote(0, "passes")
    assert m.passable(0) is True


def test_fewer_than_three_votes_is_unknown():
    m = PassabilityModel()
    m.vote(5, "blocks"); m.vote(5, "blocks")
    assert m.passable(5) is None
    assert not m.known(5)


def test_contradiction_resets_a_colour_to_unknown():
    m = PassabilityModel()
    for _ in range(3):
        m.vote(2, "blocks")
    m.contradict(2)
    assert m.passable(2) is None


def test_kills_are_tracked_separately():
    m = PassabilityModel()
    for _ in range(3):
        m.vote(3, "kills")
    assert m.lethal(3) is True
    assert m.passable(3) is False


def test_predict_move_moved_blocked_unknown():
    g = np.zeros((8, 8), dtype=np.int8)
    g[2, 5] = 2                       # wall to the right of the avatar at (2, 4)
    g[3, 4] = 7                       # unknown colour below
    m = PassabilityModel()
    for _ in range(3):
        m.vote(0, "passes"); m.vote(2, "blocks")
    avatar = frozenset({(2, 4)})
    assert predict_move(g, avatar, (0, -1), m) == ("moved", frozenset({(2, 3)}))
    assert predict_move(g, avatar, (0, 1), m) == ("blocked", avatar)
    assert predict_move(g, avatar, (1, 0), m) is None
    assert predict_move(g, avatar, (-3, 0), m) == ("blocked", avatar)   # off the grid blocks


def test_predict_move_treats_cells_under_the_avatar_as_passable():
    g = np.zeros((8, 8), dtype=np.int8)
    g[2:4, 2:4] = 9                   # a 2x2 avatar of colour 9 (never voted on)
    m = PassabilityModel()
    for _ in range(3):
        m.vote(0, "passes")
    avatar = frozenset({(2, 2), (2, 3), (3, 2), (3, 3)})
    assert predict_move(g, avatar, (0, 1), m) == ("moved", frozenset({(2, 3), (2, 4), (3, 3), (3, 4)}))
