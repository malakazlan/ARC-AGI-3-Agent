"""The explorer with the movement planner on the toy game: fewer re-tests, faster wins."""
from __future__ import annotations

from arc3.agent import Orchestrator
from arc3.config import Arc3Config
from tests.toy_game import ToyGame


def run(game, seed=0, steps=400, **cfg):
    brain = Orchestrator(Arc3Config(seed=seed, policy="graph", **cfg), game_id="toy", started_at=0.0)
    obs = game.observe()
    log = []
    for _ in range(steps):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        log.append((obs, choice))
        obs = game.apply(choice.action_id, choice.x, choice.y)
    return brain, log


def test_avatar_and_passability_are_learned_on_the_toy():
    game = ToyGame(levels=1)
    brain, _ = run(game, steps=60)
    ex = brain.policy
    assert ex.avatar is not None and ex.avatar.confident
    assert ex.passability.passable(0) is True      # floor
    assert ex.passability.passable(2) is False     # walls


def test_planner_wins_the_toy_level_much_faster_than_exploration():
    with_planner = ToyGame(levels=1)
    without = ToyGame(levels=1)
    run(with_planner, steps=600)
    run(without, steps=600, planner=False)
    assert with_planner.levels_completed == 1
    assert with_planner.steps < 150
    assert without.levels_completed == 0 or with_planner.steps * 2 < without.steps


def test_known_moves_are_not_retested_once_the_model_is_confident():
    game = ToyGame(levels=1, extra_cells={(6, 6): 0})      # remove the goal: pure exploration
    brain, log = run(game, steps=300)
    ex = brain.policy
    retests = ex.diagnostics["retests_avoided"]
    assert retests > 20
    # after confidence, "untested" picks of a move key with a known prediction must not happen
    late = [c for (o, c) in log[100:] if c.action_id in (1, 2, 3, 4) and "untested" in c.reason]
    assert len(late) <= 5


def test_mismatch_disables_planning_for_the_level_and_is_logged():
    game = ToyGame(levels=1)
    brain, _ = run(game, steps=60)
    ex = brain.policy
    for _ in range(3):
        ex._on_mismatch(colour=0)
    assert ex.planning_enabled is False
    assert ex.diagnostics["planner_resets"] == 1
    assert ex.diagnostics["mismatches"] == 3


def test_planner_can_be_disabled_by_config():
    game = ToyGame(levels=1)
    brain, _ = run(game, steps=30, planner=False)
    assert brain.policy.avatar is None
