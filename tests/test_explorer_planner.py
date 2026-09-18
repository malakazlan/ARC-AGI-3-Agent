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
    ex.predictions_checked = 4                     # 3 of 4 predictions wrong: mostly wrong
    for _ in range(3):
        ex._on_mismatch(colour=0)
    assert ex.planning_enabled is False
    assert ex.diagnostics["planner_resets"] == 1
    assert ex.diagnostics["mismatches"] == 3


def test_rare_mismatches_do_not_disable_planning():
    game = ToyGame(levels=1)
    brain, _ = run(game, steps=60)
    ex = brain.policy
    ex.predictions_checked = 200                   # 3 of 200 wrong: keep planning
    for _ in range(3):
        ex._on_mismatch(colour=0)
    assert ex.planning_enabled is True
    assert ex.diagnostics["planner_resets"] == 0


def test_planner_can_be_disabled_by_config():
    game = ToyGame(levels=1)
    brain, _ = run(game, steps=30, planner=False)
    assert brain.policy.avatar is None


def _explorer_with_known_avatar():
    """An explorer whose avatar model already knows key 4 = (0, 2) and a 1x1 avatar of colour 1."""
    import numpy as np
    from arc3.explore import GraphExplorer
    import random

    ex = GraphExplorer(random.Random(0))
    g0 = np.zeros((8, 8), dtype=np.int8); g0[4, 0] = 1
    g1 = np.zeros((8, 8), dtype=np.int8); g1[4, 2] = 1
    g2 = np.zeros((8, 8), dtype=np.int8); g2[4, 4] = 1
    g3 = np.zeros((8, 8), dtype=np.int8); g3[4, 6] = 1
    up = np.zeros((8, 8), dtype=np.int8); up[2, 6] = 1
    for a, b in ((g0, g1), (g1, g2), (g2, g3)):
        ex.avatar.observe(a, 4, b)
    ex.avatar.observe(g3, 1, up)          # a second key: control is established
    ex.avatar.observe(up, 2, g3)
    ex.avatar.observe(g3, 1, up)
    ex.avatar.observe(up, 2, g3)
    for _ in range(3):
        ex.passability.vote(0, "passes")
    return ex, g3


def test_partial_move_toward_a_wall_is_not_a_mismatch_and_teaches_passability():
    import numpy as np

    ex, before = _explorer_with_known_avatar()
    before = before.copy(); before[4, 7] = 0            # avatar at (4,6); full stroke would be (4,8): off grid
    before[4, 6] = 1
    ex.last_grid = before
    ex.pending = ("k", (4, None, None))
    ex.expected = ("blocked", frozenset({(4, 6)}))      # off-grid ahead -> predicted blocked
    after = np.zeros((8, 8), dtype=np.int8); after[4, 7] = 1   # it slid one cell instead
    ex._learn_move(after)
    assert ex.diagnostics["mismatches"] == 0
    assert ex.avatar.last_cells == {(4, 7)}


def test_partial_move_votes_blocks_for_the_cells_beyond():
    import numpy as np

    ex, before = _explorer_with_known_avatar()
    before = np.zeros((8, 8), dtype=np.int8); before[4, 2] = 1; before[4, 4] = 5   # wall of colour 5 two cells ahead
    ex.avatar.last_cells = frozenset({(4, 2)}); ex.avatar.template = {(0, 0): 1}
    ex.last_grid = before
    ex.pending = ("k", (4, None, None))
    ex.expected = ("moved", frozenset({(4, 4)}))
    after = np.zeros((8, 8), dtype=np.int8); after[4, 3] = 1; after[4, 4] = 5    # slid one cell
    ex._learn_move(after)
    assert ex.diagnostics["mismatches"] == 0
    assert ex.passability.votes[5].blocks == 1
    assert ex.passability.votes[0].passes >= 4
