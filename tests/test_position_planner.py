"""A* over predicted avatar positions."""
from __future__ import annotations

import numpy as np

from arc3.plan import plan_moves
from arc3.world_model import PassabilityModel

KEYS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def known_floor_and_walls():
    m = PassabilityModel()
    for _ in range(3):
        m.vote(0, "passes"); m.vote(2, "blocks")
    return m


def test_plans_around_a_wall_to_a_target_cell():
    g = np.zeros((8, 8), dtype=np.int8)
    g[3, 0:6] = 2                      # wall with a gap at x=6,7
    m = known_floor_and_walls()
    path = plan_moves(g, frozenset({(1, 1)}), KEYS, m, goal=lambda cells: (6, 1) in cells)
    assert path is not None
    # must go right past the gap, down, then back left: at least 5 right + 5 down + 5 left
    assert len(path) >= 15
    assert path[0] in (2, 4)


def test_unreachable_target_gives_none():
    g = np.zeros((8, 8), dtype=np.int8)
    g[3, :] = 2                        # full wall
    m = known_floor_and_walls()
    assert plan_moves(g, frozenset({(1, 1)}), KEYS, m, goal=lambda cells: (6, 1) in cells) is None


def test_plan_to_nearest_unknown_colour():
    g = np.zeros((8, 8), dtype=np.int8)
    g[1, 6] = 7                        # unknown colour far right
    g[6, 1] = 8                        # unknown colour far down
    m = known_floor_and_walls()
    path = plan_moves(g, frozenset({(1, 1)}), KEYS, m, goal=None)  # None = nearest unknown-ahead position
    assert path is not None
    assert 4 <= len(path) <= 5         # (1,1) -> (1,5) is 4 moves, then 7 is ahead; or down to (5,1)


def test_moves_use_the_learned_vectors_not_unit_steps():
    g = np.zeros((16, 16), dtype=np.int8)
    m = known_floor_and_walls()
    big = {1: (-4, 0), 2: (4, 0), 3: (0, -4), 4: (0, 4)}
    path = plan_moves(g, frozenset({(0, 0)}), big, m, goal=lambda cells: (0, 12) in cells)
    assert path == [4, 4, 4]


def test_empty_path_when_already_at_goal():
    g = np.zeros((8, 8), dtype=np.int8)
    m = known_floor_and_walls()
    assert plan_moves(g, frozenset({(1, 1)}), KEYS, m, goal=lambda cells: (1, 1) in cells) == []
