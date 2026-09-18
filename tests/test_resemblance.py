"""T1 resemblance: a changeable panel that looks like a static panel (design v2 section 5)."""
from __future__ import annotations

import numpy as np

from arc3.perception import segment_objects
from arc3.rules import display_pairs, match_progress


def scene():
    """Target box top-right: a 3x3 frame of colour 5 around a 1x1 of colour 2 (the target
    shape+colour). Panel bottom-left: same frame around a 1x1 of colour 9 (changeable). Also a
    decoration elsewhere: a 1x1 of colour 9 with no frame, and a big wall."""
    g = np.zeros((12, 12), dtype=np.int8)
    g[0:3, 9:12] = 5; g[1, 10] = 2         # static target: framed 2
    g[9:12, 0:3] = 5; g[10, 1] = 9         # panel: framed 9
    g[5, 5] = 9                            # loose decoration
    g[6, 0:12] = 3                         # a wall
    return g


def test_framed_panel_pairs_with_framed_target_not_with_loose_decoration():
    g = scene()
    changed = frozenset({(10, 1)})         # the panel's inner cell changed after an action
    pairs = display_pairs(g, changed)
    assert pairs, "expected a resemblance pair"
    best = pairs[0]
    assert best.changeable_box == (9, 0, 11, 2)
    assert best.static_box == (0, 9, 2, 11)
    assert best.score > 0


def test_progress_is_the_share_of_matching_properties():
    g = scene()
    changed = frozenset({(10, 1)})
    pair = display_pairs(g, changed)[0]
    assert match_progress(g, pair) < 1.0
    g2 = g.copy(); g2[10, 1] = 2           # panel recoloured to the target colour
    assert match_progress(g2, pair) == 1.0


def test_no_pair_when_nothing_static_resembles_the_changed_object():
    g = np.zeros((12, 12), dtype=np.int8)
    g[9:12, 0:3] = 5; g[10, 1] = 9
    g[3, 3:6] = 4                          # a bar, different shape family
    assert display_pairs(g, frozenset({(10, 1)})) == []


def ls20_like():
    """Panel bottom-left: 10x10 grey frame with a 2x-scaled L glyph of colour 9. Target top-right:
    7x7 grey frame with the same L at 1x, rotated. Both hollow, same frame colour, different size."""
    g = np.zeros((20, 20), dtype=np.int8)
    g[10:20, 0:10] = 5                              # panel box
    g[12:18, 2:8] = 0                               # hollow inside
    g[12:16, 2:4] = 9; g[14:16, 2:6] = 9            # L at 2x: 4 tall, 2 wide + foot
    g[0:7, 13:20] = 5                               # target box
    g[1:6, 14:19] = 0
    g[1, 14:16] = 9; g[1:3, 15] = 9                 # a rotated L at 1x (different orientation)
    return g


def test_frames_of_different_size_but_same_colour_and_hollow_pair_up():
    g = ls20_like()
    pairs = display_pairs(g, frozenset({(13, 2)}))
    assert pairs
    assert pairs[0].changeable_box == (10, 0, 19, 9)
    assert pairs[0].static_box == (0, 13, 6, 19)


def test_progress_compares_inner_glyphs_by_colour_and_scale_free_shape():
    from arc3.rules import normalized_shape

    g = ls20_like()
    pair = display_pairs(g, frozenset({(13, 2)}))[0]
    assert 0.0 < match_progress(g, pair) < 1.0      # colour matches, orientation does not
    # same L at 1x and 2x have the same normalized shape
    big = frozenset((y, x) for y in range(12, 16) for x in range(2, 4)) | frozenset((y, x) for y in range(14, 16) for x in range(2, 6))
    small = frozenset({(0, 0), (1, 0), (1, 1)})
    assert normalized_shape(big) == normalized_shape(small)
    assert normalized_shape(big) != normalized_shape(frozenset({(0, 0), (1, 0), (1, 1), (0, 1)}))
