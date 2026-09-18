"""Ordered subgoal routes with energy projected along the whole route (design v2 section 6)."""
from __future__ import annotations

from arc3.plan.route import Stop, plan_route


def grid_dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def names(route):
    return [s.name for s in route]


def test_direct_route_when_the_bar_pays_for_it():
    stops = [Stop("dial", (0, 10)), Stop("exit", (0, 20), final=True)]
    route = plan_route((0, 0), stops, refills=[(5, 10)], moves_left=30, capacity=30, dist=grid_dist)
    assert names(route) == ["dial", "exit"]


def test_a_refill_is_inserted_where_the_projection_runs_dry():
    """20 moves to the dial, 10 more to the exit, 25 in the bar: the refill next to the dial is
    taken after the dial, not before it and not skipped."""
    stops = [Stop("dial", (0, 20)), Stop("exit", (0, 30), final=True)]
    route = plan_route((0, 0), stops, refills=[(1, 21)], moves_left=25, capacity=25, dist=grid_dist)
    assert names(route) == ["dial", "refill", "exit"]


def test_the_refill_is_taken_before_it_is_needed_when_the_projection_says_so():
    """Near dial, far dial, exit beyond both, refill behind the start. Nearest-first dies on
    the way to the exit; the only cheap route takes the refill first."""
    stops = [Stop("near", (0, 4)), Stop("far", (0, 16)), Stop("exit", (0, 20), final=True)]
    route = plan_route((0, 0), stops, refills=[(0, 2)], moves_left=21, capacity=21, dist=grid_dist)
    assert names(route) == ["refill", "near", "far", "exit"]


def test_presses_at_a_stop_count_against_the_bar():
    stops = [Stop("dial", (0, 10), presses=3), Stop("exit", (0, 12), final=True)]
    assert plan_route((0, 0), stops, refills=[], moves_left=14, capacity=14, dist=grid_dist) is None
    route = plan_route((0, 0), stops, refills=[], moves_left=16, capacity=16, dist=grid_dist)
    assert names(route) == ["dial", "exit"]


def test_no_route_when_even_the_refills_cannot_pay():
    stops = [Stop("dial", (0, 50)), Stop("exit", (0, 0), final=True)]
    assert plan_route((0, 0), stops, refills=[(0, 10)], moves_left=12, capacity=12, dist=grid_dist) is None


def test_unreachable_stops_make_no_route():
    def dist(a, b):
        return None if b == (0, 10) else grid_dist(a, b)
    stops = [Stop("dial", (0, 10)), Stop("exit", (0, 20), final=True)]
    assert plan_route((0, 0), stops, refills=[], moves_left=99, capacity=99, dist=dist) is None


def test_cell_route_length_counts_moves_of_the_step_size_through_walkable_cells():
    import numpy as np
    from arc3.plan.route import cell_route_length

    walk = np.ones((12, 12), dtype=bool)
    walk[5, 2:12] = False                      # a wall with a gap at the left
    # moves until the goal is within one step: around the gap, 5 left, 5 up, 4 right to (3, 5)
    assert cell_route_length(walk, (8, 6), (2, 6), step=1) == 14
    assert cell_route_length(walk, (8, 6), (8, 9), step=1) == 2
    assert cell_route_length(walk, (8, 6), (8, 6), step=1) == 0


def test_cell_route_length_reaches_a_goal_cell_within_one_step_and_reports_unreachable():
    import numpy as np
    from arc3.plan.route import cell_route_length

    walk = np.ones((20, 20), dtype=bool)
    walk[10, :] = False                        # a full wall: the far side is unreachable
    assert cell_route_length(walk, (2, 2), (15, 2), step=5) is None
    # tiles of 5: from (2,2) to (2,12) is two jumps; the goal is a wall cell next to the lattice
    walk[2, 13] = False
    assert cell_route_length(walk, (2, 2), (2, 13), step=5) == 2


def test_cell_route_length_rides_a_known_portal():
    import numpy as np
    from arc3.plan.route import cell_route_length

    walk = np.ones((10, 30), dtype=bool)
    walk[:, 15] = False                        # a full wall
    portals = {(5, 5): (5, 25)}                # landing on (5,5) carries the avatar across
    assert cell_route_length(walk, (5, 0), (5, 28), step=5) is None
    assert cell_route_length(walk, (5, 0), (5, 28), step=5, portals=portals) == 1
