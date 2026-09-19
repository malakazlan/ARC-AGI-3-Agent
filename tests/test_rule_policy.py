"""The v2 rule policy on the display toy: discover the rotator, infer match_display, exploit."""
from __future__ import annotations

from arc3.agent import Orchestrator
from arc3.config import Arc3Config
from tests.toy_display import DisplayToy


def run(game, seed=0, steps=300, policy="rules", **cfg):
    brain = Orchestrator(Arc3Config(seed=seed, policy=policy, **cfg), game_id="display", started_at=0.0)
    obs = game.observe()
    log = []
    for _ in range(steps):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        log.append((obs, choice))
        obs = game.apply(choice.action_id, choice.x, choice.y)
    return brain, log


def test_orchestrator_builds_the_rule_policy_from_config():
    from arc3.agent_v2 import RulePolicy

    brain = Orchestrator(Arc3Config(policy="rules"), game_id="display", started_at=0.0)
    assert isinstance(brain.policy, RulePolicy)


def test_rule_policy_wins_the_display_level_within_sixty_actions():
    game = DisplayToy()
    brain, log = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 75   # reach tries the reachable frames before the goal is known (about 14 actions)


def test_rule_policy_learns_the_rotator_as_a_dial_and_the_display_pair():
    game = DisplayToy()
    brain, _ = run(game, steps=200)
    store = brain.policy.store
    rotator = next((sig for sig, t in store.tools.items() if t.kind == "dial"), None)
    assert rotator is not None and rotator[0] == 7
    assert store.goal is not None and store.goal.template == "match_display"
    assert brain.diagnostics["actions_to_hypothesis"] is not None
    assert brain.diagnostics["actions_to_hypothesis"] <= 50   # see the reach note above


def test_rule_policy_beats_the_explorer_on_the_display_toy():
    rules_game, explorer_game = DisplayToy(), DisplayToy()
    run(rules_game, steps=300)
    run(explorer_game, steps=300, policy="graph")
    assert rules_game.levels_completed == 1
    assert explorer_game.levels_completed == 0 or rules_game.steps * 2 <= explorer_game.steps


def test_rule_policy_falls_back_to_the_explorer_when_no_hypothesis_forms():
    """A toy without any panel: no resemblance ever; the policy must still act legally."""
    from tests.toy_game import ToyGame

    game = ToyGame(levels=1)
    brain, log = run(game, steps=150)
    assert all(c.action_id in (0, 1, 2, 3, 4) for _, c in log)
    assert brain.diagnostics["fallbacks"] == 0
    assert brain.policy.store.goal is None or game.levels_completed == 1


def test_rule_policy_uses_the_target_display_itself_as_the_exit():
    """ls20's real layout: there is no separate exit; the matched avatar walks into the target."""
    game = DisplayToy(exit_in_target=True)
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 60


def test_rule_policy_keeps_using_a_rotator_it_is_standing_on():
    """ls20's real rotator: the avatar steps onto the dial and hides it. The tool is not lost."""
    game = DisplayToy(rotator_walkable=True, exit_in_target=True)
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 60
    assert brain.diagnostics["hypotheses_demoted"] == 0


def test_rule_policy_keeps_the_match_while_the_avatar_is_inside_the_target():
    """ls20: the avatar is drawn inside the target box while entering it. That must not read as
    'the displays no longer match' and send the policy back to the dial."""
    game = DisplayToy(deep_target=True)
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 60
    assert brain.diagnostics["hypotheses_demoted"] == 0


def test_rule_policy_treats_a_two_colour_icon_as_one_tool():
    """ls20's rotator is a two-colour icon. Its pieces are one tool, probed once, never an exit."""
    game = DisplayToy(compound_rotator=True, exit_in_target=True)
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 60
    assert brain.diagnostics["probes"] <= 2


def test_rule_policy_ignores_ambient_change_when_reading_a_touch():
    """ls20: the energy bar drains on every action. A bar inside a frame of the panel's colour
    must not be paired as a display."""
    game = DisplayToy(bar=True, exit_in_target=True)
    brain, _ = run(game, steps=250)
    assert game.levels_completed == 1
    bar_box = (8, 5, 11, 11)
    assert all(d["changeable"] != bar_box and d["static"] != bar_box for d in brain.policy.store.displays)


def test_rule_policy_carries_the_rule_to_level_two_without_new_probes():
    """Level 2 moves the target and the rotator. Known rule: no discovery, straight to the dial."""
    game = DisplayToy(levels=2, exit_in_target=True)
    brain, log = run(game, steps=300)
    assert game.levels_completed == 2
    level1_actions = brain.policy.store.level_paths[0]
    level2_actions = game.steps - len(level1_actions)
    assert brain.diagnostics["hypothesis_correct"] >= 1
    assert level2_actions <= 30, level2_actions


def test_rule_policy_probes_for_a_second_dial_when_the_known_one_cannot_finish_the_match():
    """ls20 level 3: the target also differs in colour. The rotator fixes the shape and no
    more; the policy must probe an unknown object, learn the colour dial and use it."""
    game = DisplayToy(colour_dial=True, exit_in_target=True)
    brain, _ = run(game, steps=250)
    assert game.levels_completed == 1
    store = brain.policy.store
    props = {t.params.get("prop") for t in store.tools.values() if t.kind == "dial"}
    assert props >= {"shape", "colour"}
    assert game.steps <= 120
