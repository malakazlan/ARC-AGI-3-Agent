"""Ranking of unknown objects worth a probe (design v2: the delta list)."""
from __future__ import annotations

import numpy as np

from arc3.perception import GridObject, segment_objects
from arc3.rules.probes import rank_probes


def test_probes_prefer_touchable_multicolour_icons_and_drop_hud_objects():
    """Floor 3 inside walls 4, HUD colour 5 outside. A 2x2 HUD square (rare, small) is not
    touchable from the avatar; a plain strip in the wall next to the floor is touchable; a
    three-colour icon on the floor comes first."""
    g = np.full((20, 20), 5, dtype=np.int8)
    g[2:18, 2:18] = 4                     # walls
    g[3:17, 3:17] = 3                     # floor
    g[10:12, 10:12] = 1                   # the avatar (colour 1)
    g[0:2, 18:20] = 8                     # HUD square, outside the walls
    g[2, 6:9] = 7                         # a strip in the top wall, touching the floor
    g[14, 5] = 9; g[14, 6] = 10; g[15, 5] = 11; g[15, 6] = 9   # a small three-colour icon on the floor
    walk = (g == 3) | (g == 1)
    avatar = frozenset({(10, 10), (10, 11), (11, 10), (11, 11)})
    pieces = [o for o in segment_objects(g) if int(o.color) in (9, 10, 11)]
    cells = tuple(sorted(c for o in pieces for c in o.cells))
    icon = GridObject(color=9, size=len(cells), bbox=(14, 5, 15, 6), centroid=(14.5, 5.5),
                      anchor=(14, 5), cells=cells)                 # merged as the policy merges icons
    others = [o for o in segment_objects(g) if int(o.color) in (7, 8)]
    colours = lambda o: len({int(g[y, x]) for (y, x) in o.cells})
    ranked = rank_probes(others + [icon], walk, avatar, colours_of=colours)
    assert [int(o.color) for o in ranked] == [9, 7]              # icon (4 cells, 3 colours) before the strip (3 cells)
