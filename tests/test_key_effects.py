"""Non-move key effects generalised by the avatar's appearance (a rotate key, a toggle key)."""
from __future__ import annotations

import numpy as np

from arc3.world_model import KeyEffects


def grid8():
    return np.zeros((8, 8), dtype=np.int8)


def L_shape(g, y, x, colour=1):
    g[y, x] = colour; g[y + 1, x] = colour; g[y + 2, x] = colour; g[y + 2, x + 1] = colour


def J_shape(g, y, x, colour=1):
    g[y, x + 1] = colour; g[y + 1, x + 1] = colour; g[y + 2, x + 1] = colour; g[y + 2, x] = colour


def test_rotate_effect_is_learned_per_avatar_appearance_and_predicts_elsewhere():
    fx = KeyEffects(k=3)
    for _ in range(3):
        before = grid8(); L_shape(before, 1, 1)
        after = grid8(); J_shape(after, 1, 1)
        fx.record(5, frozenset({(1, 1), (2, 1), (3, 1), (3, 2)}), before, after)
    before = grid8(); L_shape(before, 4, 5)
    cells = frozenset({(4, 5), (5, 5), (6, 5), (6, 6)})
    predicted = fx.predict(5, cells, before)
    expected = grid8(); J_shape(expected, 4, 5)
    assert predicted is not None and np.array_equal(predicted, expected)


def test_effect_depends_on_appearance_not_only_on_the_key():
    fx = KeyEffects(k=3)
    for _ in range(3):
        before = grid8(); L_shape(before, 1, 1)
        after = grid8(); J_shape(after, 1, 1)
        fx.record(5, frozenset({(1, 1), (2, 1), (3, 1), (3, 2)}), before, after)
    other = grid8(); J_shape(other, 1, 1)
    assert fx.predict(5, frozenset({(1, 2), (2, 2), (3, 2), (3, 1)}), other) is None


def test_inconsistent_effects_stay_unknown():
    fx = KeyEffects(k=3)
    cells = frozenset({(1, 1), (2, 1), (3, 1), (3, 2)})
    before = grid8(); L_shape(before, 1, 1)
    a1 = grid8(); J_shape(a1, 1, 1)
    a2 = grid8(); L_shape(a2, 1, 1, colour=2)
    fx.record(5, cells, before, a1); fx.record(5, cells, before, a2); fx.record(5, cells, before, a1)
    assert fx.predict(5, cells, before) is None


def test_no_op_key_becomes_a_known_no_op():
    fx = KeyEffects(k=3)
    cells = frozenset({(1, 1), (2, 1), (3, 1), (3, 2)})
    before = grid8(); L_shape(before, 1, 1)
    for _ in range(3):
        fx.record(7, cells, before, before)
    predicted = fx.predict(7, cells, before)
    assert predicted is not None and np.array_equal(predicted, before)
    assert fx.global_effect(7, cells, before) is not None and not fx.global_effect(7, cells, before).changed


def test_effects_without_an_avatar_are_keyed_by_the_whole_frame_change():
    """No avatar (click-only or unknown): a key's effect can still be global if the frame diff
    is identical each time, anchored at the grid origin."""
    fx = KeyEffects(k=3)
    before = grid8(); before[0, 0] = 3
    after = grid8(); after[0, 0] = 4
    for _ in range(3):
        fx.record(5, frozenset(), before, after)
    predicted = fx.predict(5, frozenset(), before)
    assert predicted is not None and np.array_equal(predicted, after)
