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


def test_swept_cells_cover_the_whole_stroke_of_a_multi_cell_step():
    from arc3.world_model.passability import swept_cells

    avatar = frozenset({(5, 0)})
    assert swept_cells(avatar, (0, 3)) == frozenset({(5, 1), (5, 2), (5, 3)})
    block = frozenset({(0, 0), (0, 1), (1, 0), (1, 1)})
    assert swept_cells(block, (2, 0)) == frozenset({(2, 0), (2, 1), (3, 0), (3, 1)})


def test_a_wall_between_origin_and_landing_blocks_a_multi_cell_step():
    """tu93: six-cell steps over three-cell passages. A known wall one cell ahead blocks the
    press even though the landing cells are known floor; an unknown colour in between makes
    the prediction unknown, not 'moved'."""
    import numpy as np

    from arc3.world_model import PassabilityModel, predict_move

    g = np.zeros((3, 8), dtype=np.int8)
    g[1, 0] = 9                # avatar
    g[1, 1] = 7                # wall colour
    g[1, 2:4] = 0              # floor
    model = PassabilityModel()
    for _ in range(3):
        model.vote(0, "passes"); model.vote(7, "blocks")
    assert predict_move(g, frozenset({(1, 0)}), (0, 3), model)[0] == "blocked"
    g[1, 1] = 4                # unknown colour in between
    assert predict_move(g, frozenset({(1, 0)}), (0, 3), model) is None
    g[1, 1] = 0
    assert predict_move(g, frozenset({(1, 0)}), (0, 3), model)[0] == "moved"


def test_a_blocked_press_blames_the_first_unknown_footprint_on_the_path():
    """A press stops at the first obstacle. With two unknown colours on the sweep, the nearer
    one takes the block vote; the farther one stays unknown."""
    import numpy as np

    from arc3.world_model import PassabilityModel
    from arc3.world_model.passability import first_obstacle_colours

    g = np.zeros((3, 8), dtype=np.int8)
    g[1, 0] = 9
    g[1, 1] = 7
    g[1, 2] = 8
    model = PassabilityModel()
    assert first_obstacle_colours(g, frozenset({(1, 0)}), (0, 3), model) == {7}
    for _ in range(3):
        model.vote(7, "passes")
    assert first_obstacle_colours(g, frozenset({(1, 0)}), (0, 3), model) == {8}


def test_a_contradiction_weakens_strong_evidence_instead_of_erasing_it():
    """One misread (a conveyor ride reported as blocked) must not erase a floor colour that
    carried the avatar a thousand times; weak evidence is still dropped."""
    from arc3.world_model import PassabilityModel

    m = PassabilityModel()
    for _ in range(200):
        m.vote(3, "passes")
    m.contradict(3)
    assert m.passable(3) is True
    m2 = PassabilityModel()
    for _ in range(3):
        m2.vote(7, "passes")
    m2.contradict(7)
    assert m2.passable(7) is None
