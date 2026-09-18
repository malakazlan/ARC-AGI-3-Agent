

def test_the_floor_tile_revealed_behind_the_avatar_is_not_the_avatar():
    """tu93: the avatar lands on a floor tile and reveals one where it stood; the tile 'moves'
    by the opposite vector. The election must pick the avatar (colour 9, +2 per key 4), not the
    vacated tile with inverted vectors."""
    import numpy as np

    from arc3.world_model import AvatarModel

    def frame(avatar_col: int, tile_col: int, facing: str) -> np.ndarray:
        # a 3x3 floor tile (colour 0), a 3-wide passage (colour 2) between the two tile slots,
        # and the avatar: a 3x3 ring of 9 with a 4 in the middle and a gap on the side it
        # faces, exactly tu93's look (the gap moves, so the exact shape key changes each step)
        g = np.full((9, 14), 5, dtype=np.int8)
        g[2:5, 5:8] = 2
        g[6:9, 8:11] = 0                             # another floor tile elsewhere, static
        g[2:5, tile_col:tile_col + 3] = 0
        g[2:5, avatar_col:avatar_col + 3] = 9
        g[3, avatar_col + 1] = 4
        g[3, avatar_col + (2 if facing == "right" else 0)] = 0
        return g

    model = AvatarModel()
    for _ in range(2):
        model.observe(frame(2, 8, "left"), 4, frame(8, 2, "right"))   # key 4: right by 6, tile shows behind
        model.observe(frame(8, 2, "right"), 3, frame(2, 8, "left"))   # key 3: back left
    assert model.confident
    assert model.signature[0] == 9
    assert model.vector(4) == (0, 6)
    assert model.vector(3) == (0, -6)


def test_a_tracked_avatar_carried_far_away_is_a_move_not_a_block():
    """ls20 conveyor: the avatar leaves its cells and reappears 25 cells away. The model must
    report a move with that vector, not a block (a block wipes the floor's passability)."""
    import numpy as np

    from arc3.world_model import AvatarModel

    def frame(row: int, col: int) -> np.ndarray:
        g = np.full((30, 50), 3, dtype=np.int8)
        g[row:row + 5, col:col + 5] = 9
        return g

    model = AvatarModel()
    pos = (0, 2)
    for key, (dy, dx) in ((4, (0, 5)), (2, (5, 0)), (4, (0, 5)), (2, (5, 0)), (4, (0, 5))):
        nxt = (pos[0] + dy, pos[1] + dx)
        model.observe(frame(*pos), key, frame(*nxt))
        pos = nxt
    assert model.confident
    outcome = model.observe(frame(*pos), 4, frame(pos[0], pos[1] + 25))
    assert outcome == "moved"
    assert model.last_vector[4] == (0, 25)
