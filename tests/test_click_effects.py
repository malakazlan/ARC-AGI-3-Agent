"""Click effects generalised by object signature (colour + shape + size)."""
from __future__ import annotations

import numpy as np

from arc3.perception import segment_objects
from arc3.world_model import ClickEffects, object_signature


def grid8():
    return np.zeros((8, 8), dtype=np.int8)


def test_signature_has_colour_shape_and_size_and_ignores_position():
    g = grid8()
    g[1, 1:4] = 5          # a 1x3 bar at the top
    g[6, 3:6] = 5          # the same bar lower right
    a, b = segment_objects(g, background=0)
    assert object_signature(a) == object_signature(b)
    assert object_signature(a)[0] == 5 and object_signature(a)[2] == 3


def test_different_shapes_of_same_colour_and_size_differ():
    g = grid8()
    g[1, 1:4] = 5          # horizontal bar
    g[4:7, 6] = 5          # vertical bar
    a, b = segment_objects(g, background=0)
    assert object_signature(a) != object_signature(b)


def test_effect_becomes_global_after_three_consistent_observations():
    fx = ClickEffects(k=3)
    sig = (5, "h3", 3)
    before = grid8(); before[1, 1:4] = 5
    after = before.copy(); after[1, 1:4] = 7        # the bar turns colour 7
    for _ in range(2):
        fx.record(sig, (1, 2), before, after)
        assert fx.global_effect(sig) is None
    fx.record(sig, (1, 2), before, after)
    effect = fx.global_effect(sig)
    assert effect is not None and effect.changed


def test_inconsistent_effects_never_become_global():
    fx = ClickEffects(k=3)
    sig = (5, "h3", 3)
    before = grid8(); before[1, 1:4] = 5
    after1 = before.copy(); after1[1, 1:4] = 7
    after2 = before.copy(); after2[1, 1:4] = 9
    fx.record(sig, (1, 2), before, after1)
    fx.record(sig, (1, 2), before, after2)
    fx.record(sig, (1, 2), before, after1)
    assert fx.global_effect(sig) is None


def test_global_effect_predicts_the_next_grid_relative_to_the_click():
    fx = ClickEffects(k=3)
    sig = (5, "h3", 3)
    before = grid8(); before[1, 1:4] = 5
    after = before.copy(); after[1, 1:4] = 7
    for _ in range(3):
        fx.record(sig, (1, 2), before, after)
    elsewhere = grid8(); elsewhere[6, 3:6] = 5
    predicted = fx.predict(sig, (6, 4), elsewhere)
    expected = elsewhere.copy(); expected[6, 3:6] = 7
    assert predicted is not None and np.array_equal(predicted, expected)


def test_consistent_no_op_is_a_global_no_op():
    fx = ClickEffects(k=3)
    sig = (2, "h6", 6)
    g = grid8(); g[3, 0:6] = 2
    for _ in range(3):
        fx.record(sig, (3, 2), g, g)
    effect = fx.global_effect(sig)
    assert effect is not None and not effect.changed
