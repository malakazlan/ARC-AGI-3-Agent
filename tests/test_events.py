"""Events read from a frame diff, on synthetic 8x8 grids (design v2 section 3)."""
from __future__ import annotations

import numpy as np

from arc3.rules import extract_events


def grid8():
    return np.zeros((8, 8), dtype=np.int8)


def kinds(events):
    return sorted(e.kind for e in events)


def test_no_change_gives_no_events():
    g = grid8(); g[2, 2] = 5
    assert extract_events(g, g.copy()) == []


def test_translation_is_a_moved_event_with_vector_and_signature():
    a, b = grid8(), grid8()
    a[2, 2:4] = 5
    b[2, 3:5] = 5
    (e,) = extract_events(a, b)
    assert e.kind == "moved" and e.vector == (0, 1) and e.signature[0] == 5


def test_colour_change_in_place_is_a_prop_changed_event():
    a, b = grid8(), grid8()
    a[4:6, 4:6] = 3
    b[4:6, 4:6] = 7
    (e,) = extract_events(a, b)
    assert e.kind == "prop_changed" and e.prop == "colour" and (e.old, e.new) == (3, 7)
    assert e.cells == tuple(sorted((y, x) for y in (4, 5) for x in (4, 5)))


def test_shape_change_in_place_is_a_prop_changed_shape_event():
    a, b = grid8(), grid8()
    a[1, 1] = 4; a[2, 1] = 4; a[3, 1] = 4; a[3, 2] = 4          # an L
    b[1, 2] = 4; b[2, 2] = 4; b[3, 2] = 4; b[3, 1] = 4          # a J, same box
    (e,) = extract_events(a, b)
    assert e.kind == "prop_changed" and e.prop == "shape"


def test_appear_and_disappear():
    a, b = grid8(), grid8()
    a[0, 0] = 9
    b[7, 7] = 2
    assert kinds(extract_events(a, b)) == ["appeared", "disappeared"]


def test_masked_cells_never_produce_events():
    a, b = grid8(), grid8()
    a[7, :] = 6; b[7, :] = 6; b[7, 0] = 0
    mask = np.zeros((8, 8), dtype=bool); mask[7, :] = True
    assert extract_events(a, b, mask) == []


def test_two_independent_changes_give_two_events():
    a, b = grid8(), grid8()
    a[1, 1] = 5; b[1, 2] = 5                 # a dot moved right
    a[6, 6] = 3; b[6, 6] = 8                 # a dot recoloured
    assert kinds(extract_events(a, b)) == ["moved", "prop_changed"]
