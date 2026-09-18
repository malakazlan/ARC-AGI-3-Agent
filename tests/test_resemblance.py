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
