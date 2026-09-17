"""State graph and shortest path to the exploration frontier."""
from __future__ import annotations

from arc3.plan import path_to_nearest_frontier
from arc3.world_model import StateGraph

A1, A2, A3 = (1, None, None), (2, None, None), (3, None, None)
CLICK = (6, 3, 4)


def test_new_node_has_every_candidate_untested():
    g = StateGraph()
    g.add_node("s0", [A1, A2, CLICK])
    assert g.untested("s0") == [A1, A2, CLICK]
    assert g.size() == 1


def test_recording_a_transition_marks_the_action_tested():
    g = StateGraph()
    g.add_node("s0", [A1, A2])
    g.record("s0", A1, dst_key="s1", changed=True, game_over=False, level_up=False)
    assert g.untested("s0") == [A2]
    assert g.edge("s0", A1).dst_key == "s1"


def test_game_over_edge_is_tested_and_has_no_destination():
    g = StateGraph()
    g.add_node("s0", [A1])
    g.record("s0", A1, dst_key=None, changed=False, game_over=True, level_up=False)
    assert g.untested("s0") == []
    assert g.edge("s0", A1).game_over


def test_re_recording_with_a_different_destination_counts_as_inconsistent():
    g = StateGraph()
    g.add_node("s0", [A1])
    g.record("s0", A1, dst_key="s1", changed=True, game_over=False, level_up=False)
    g.record("s0", A1, dst_key="s2", changed=True, game_over=False, level_up=False)
    assert g.inconsistent == 1
    assert g.edge("s0", A1).dst_key == "s2"


def test_add_node_is_idempotent_and_keeps_tested_edges():
    g = StateGraph()
    g.add_node("s0", [A1, A2])
    g.record("s0", A1, dst_key="s1", changed=True, game_over=False, level_up=False)
    g.add_node("s0", [A1, A2])
    assert g.untested("s0") == [A2]


def test_node_cap_refuses_new_nodes_but_keeps_known_ones():
    g = StateGraph(max_nodes=2)
    assert g.add_node("s0", [A1])
    assert g.add_node("s1", [A1])
    assert not g.add_node("s2", [A1])
    assert g.add_node("s0", [A1])
    assert g.size() == 2


def test_frontier_path_is_empty_when_current_node_has_untested_actions():
    g = StateGraph()
    g.add_node("s0", [A1, A2])
    assert path_to_nearest_frontier(g, "s0") == []


def test_frontier_path_follows_known_edges_to_nearest_untested_node():
    g = StateGraph()
    g.add_node("s0", [A1, A2])
    g.add_node("s1", [A1])
    g.add_node("s2", [A1, A3])
    g.record("s0", A1, "s1", True, False, False)
    g.record("s0", A2, "s2", True, False, False)
    g.record("s1", A1, "s2", True, False, False)
    g.record("s2", A1, "s0", True, False, False)
    # s2 still has A3 untested; nearest from s0 is one step via A2.
    assert path_to_nearest_frontier(g, "s0") == [A2]


def test_frontier_path_ignores_no_op_and_game_over_edges():
    g = StateGraph()
    g.add_node("s0", [A1, A2, A3])
    g.add_node("s1", [A1, A2])
    g.record("s0", A1, "s0", False, False, False)   # no-op self loop
    g.record("s0", A2, None, False, True, False)    # game over
    g.record("s0", A3, "s1", True, False, False)
    g.record("s1", A1, "s0", True, False, False)
    assert path_to_nearest_frontier(g, "s0") == [A3]


def test_frontier_path_is_none_when_everything_is_tested():
    g = StateGraph()
    g.add_node("s0", [A1])
    g.add_node("s1", [A1])
    g.record("s0", A1, "s1", True, False, False)
    g.record("s1", A1, "s0", True, False, False)
    assert path_to_nearest_frontier(g, "s0") is None


def test_frontier_path_from_unknown_node_is_none():
    assert path_to_nearest_frontier(StateGraph(), "nope") is None
