"""Online action-effect prior: which action classes do nothing, which kill."""
from __future__ import annotations

import numpy as np

from arc3.world_model import ActionPrior, action_class


def test_simple_actions_are_classed_by_id_and_clicks_by_target_colour_and_size():
    grid = np.zeros((8, 8), dtype=np.int8)
    grid[2:4, 2:4] = 5           # a 2x2 object of colour 5
    assert action_class((1, None, None), grid) == (1,)
    assert action_class((6, 2, 2), grid) == (6, 5, "1-4")
    assert action_class((6, 0, 0), grid) == (6, 0, "17-64")   # the 60-cell background


def test_fresh_class_is_neither_dead_nor_lethal():
    prior = ActionPrior()
    assert not prior.deferred((1,))
    assert prior.score((1,)) == prior.score((6, 5, "1-4"))


def test_class_that_never_changed_anything_after_three_tries_is_dead():
    prior = ActionPrior()
    for _ in range(3):
        prior.record((6, 2, "17-64"), changed=False, game_over=False)
    assert prior.deferred((6, 2, "17-64"))
    prior.record((6, 2, "17-64"), changed=True, game_over=False)
    assert not prior.deferred((6, 2, "17-64"))


def test_class_that_kills_twice_is_lethal_until_it_proves_otherwise():
    prior = ActionPrior()
    prior.record((5,), changed=False, game_over=True)
    assert not prior.deferred((5,))
    prior.record((5,), changed=False, game_over=True)
    assert prior.deferred((5,))
    for _ in range(3):
        prior.record((5,), changed=True, game_over=False)
    assert not prior.deferred((5,))


def test_score_prefers_classes_that_change_things():
    prior = ActionPrior()
    prior.record((1,), changed=True, game_over=False)
    prior.record((2,), changed=False, game_over=False)
    assert prior.score((1,)) > prior.score((2,))
