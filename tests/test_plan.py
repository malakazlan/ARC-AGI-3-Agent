

def test_planner_never_repeats_a_press_that_killed_us():
    """tu93 level 2: the shortest route to unknown terrain runs into a pursuer and the level
    ends; the same route was replanned every reset. A (position, key) that ended the game is
    forbidden, so the planner routes around it."""
    import numpy as np

    from arc3.plan import plan_moves
    from arc3.world_model import PassabilityModel

    g = np.zeros((5, 5), dtype=np.int8)
    model = PassabilityModel()
    for _ in range(3):
        model.vote(0, "passes")
    start = frozenset({(2, 0)})
    keys = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
    goal = lambda c: (2, 2) in c
    assert plan_moves(g, start, keys, model, goal) == [4, 4]
    forbidden = {(frozenset({(2, 1)}), 4)}          # stepping right from (2,1) killed us
    path = plan_moves(g, start, keys, model, goal, forbidden=forbidden)
    assert path is not None and path != [4, 4] and len(path) == 4
