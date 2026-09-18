"""Per-game rule store: tools, displays, goal, level paths; persists across levels."""
from __future__ import annotations

from arc3.rules import Goal, RuleStore


def test_tools_are_remembered_across_levels():
    store = RuleStore()
    store.set_tool((4, "1x1:1", 1), "dial", k=4, prop="shape")
    store.new_level(1)
    tool = store.tool((4, "1x1:1", 1))
    assert tool is not None and tool.kind == "dial" and tool.params == {"k": 4, "prop": "shape"}


def test_unknown_signature_has_no_tool():
    assert RuleStore().tool((1, "x", 1)) is None


def test_goal_and_confidence_carry_over_and_can_be_demoted():
    store = RuleStore()
    store.propose_goal(Goal("match_display", {"pair": 0}, confidence=0.6))
    store.new_level(1)
    assert store.goal is not None and store.goal.template == "match_display"
    store.demote_goal(0.2)
    assert store.goal.confidence == 0.4
    store.demote_goal(0.4)
    assert store.goal is None            # below the floor: dropped


def test_level_paths_and_deaths_are_kept():
    store = RuleStore()
    store.record_level_path(0, [(1, None, None), (5, None, None)])
    store.record_death((9, "1x1:1", 1))
    store.new_level(1)
    assert store.level_paths[0] == [(1, None, None), (5, None, None)]
    assert store.lethal((9, "1x1:1", 1))


def test_store_is_json_serialisable_for_diagnostics():
    import json

    store = RuleStore()
    store.set_tool((4, "1x1:1", 1), "refill")
    store.propose_goal(Goal("reach", {"signature": (7, "2x2:f", 4)}, confidence=0.5))
    json.dumps(store.to_dict())
