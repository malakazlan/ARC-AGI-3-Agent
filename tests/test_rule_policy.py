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
    assert game.steps <= 60


def test_rule_policy_learns_the_rotator_as_a_dial_and_the_display_pair():
    game = DisplayToy()
    brain, _ = run(game, steps=200)
    store = brain.policy.store
    rotator = next((sig for sig, t in store.tools.items() if t.kind == "dial"), None)
    assert rotator is not None and rotator[0] == 7
    assert store.goal is not None and store.goal.template == "match_display"
    assert brain.diagnostics["actions_to_hypothesis"] is not None
    assert brain.diagnostics["actions_to_hypothesis"] <= 35


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
