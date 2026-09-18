"""Graph explorer policy driven through the orchestrator on the toy game."""
from __future__ import annotations

from arc3.agent import Orchestrator
from arc3.config import Arc3Config
from arc3.explore import GraphExplorer
from tests.toy_game import ToyGame


def run(game: ToyGame, seed: int = 0, steps: int = 400, **cfg) -> tuple[Orchestrator, list]:
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


def test_orchestrator_builds_graph_explorer_from_config():
    brain = Orchestrator(Arc3Config(policy="graph"), game_id="toy", started_at=0.0)
    assert isinstance(brain.policy, GraphExplorer)


def test_explorer_never_repeats_a_tested_pair_while_a_frontier_exists():
    brain, _ = run(ToyGame(), steps=300)
    explorer = brain.policy
    assert explorer.graph.inconsistent == 0
    assert explorer.diagnostics["repeats"] == 0


def test_explorer_marks_game_over_edges_and_never_retries_them():
    game = ToyGame(levels=1, extra_cells={(1, 2): 3})   # trap right next to the start
    brain, log = run(game, steps=80, planner=False)     # with the planner it wins before dying
    explorer = brain.policy
    # the trap has up to four approaches; each (state, action) pair may end the game once
    assert 1 <= game.game_overs <= 4
    assert explorer.diagnostics["game_overs"] == game.game_overs
    assert explorer.diagnostics["game_over_retries"] == 0
    resets = sum(1 for _, c in log if c.action_id == 0)
    assert resets == game.game_overs + 1   # one per game over, plus the initial reset


def test_explorer_clears_both_toy_levels_within_budget():
    game = ToyGame()
    brain, _ = run(game, steps=1500)
    assert game.levels_completed == 2
    assert brain.diagnostics["levels_completed"] == 2


def test_same_seed_gives_the_same_trajectory():
    _, log_a = run(ToyGame(), seed=3, steps=200)
    _, log_b = run(ToyGame(), seed=3, steps=200)
    assert [c for _, c in log_a] == [c for _, c in log_b]


def test_graph_is_reset_on_every_level_change():
    game = ToyGame()
    brain, _ = run(game, steps=1500)
    explorer = brain.policy
    assert game.levels_completed == 2
    assert explorer.level_index == 2
    assert explorer.diagnostics["levels_seen"] == 2   # two levels were actually played
    assert explorer.graph.size() == 0                  # nothing left over after the final win


def test_click_candidates_are_object_anchors_and_buttons_get_found():
    game = ToyGame(available=[6], extra_cells={(2, 2): 5, (5, 5): 5})
    brain, log = run(game, steps=25)
    clicks = [(c.y, c.x) for _, c in log if c.action_id == 6]
    assert (2, 2) in clicks and (5, 5) in clicks
    assert brain.policy.diagnostics["repeats"] == 0


def test_explorer_falls_back_to_random_legal_when_frontier_is_exhausted():
    game = ToyGame(available=[3])          # only "left": walks into the wall forever
    brain, log = run(game, steps=30)
    assert all(c.action_id == 3 for _, c in log[1:])   # log[0] is the initial reset
    assert brain.policy.diagnostics["exhausted"] > 0
    assert brain.diagnostics["fallbacks"] == 0


def test_explorer_diagnostics_are_exported_through_the_orchestrator():
    brain, _ = run(ToyGame(), steps=50)
    d = brain.diagnostics
    assert d["states"] > 1 and d["edges"] >= d["states"] - 1


# --- countdown bars and per-attempt budgets ------------------------------------------

def test_explorer_learns_the_countdown_mask_after_two_attempts():
    game = ToyGame(levels=1, budget=12)
    brain, _ = run(game, steps=60, planner=False)
    explorer = brain.policy
    assert game.game_overs >= 2
    assert explorer.mask is not None and explorer.mask[7].any()
    assert not explorer.mask[:7].any()


def test_budget_deaths_are_not_recorded_as_lethal_edges():
    game = ToyGame(levels=1, budget=12)
    brain, _ = run(game, steps=80, planner=False)
    explorer = brain.policy
    assert explorer.diagnostics["budget_deaths"] >= 1
    assert explorer.budget == 12          # diagnostic cadence; expiry itself is read from the bar
    # after the budget is known, no edge in the graph is marked game_over by an expiry
    lethal = sum(1 for node in explorer.graph.nodes.values() for e in node.tested.values() if e.game_over)
    assert lethal == 0


def test_masked_state_space_is_small_despite_the_bar():
    with_bar = ToyGame(levels=1, budget=15)
    brain, _ = run(with_bar, steps=400)
    assert brain.policy.diagnostics["states"] < 80    # ~58 reachable cells, not 58 x bar phases


def test_explorer_still_clears_a_level_with_a_budget_bar():
    game = ToyGame(levels=1, budget=40)
    brain, _ = run(game, steps=1500, planner=False)
    assert game.levels_completed == 1


def test_countdown_masking_can_be_disabled_by_config():
    game = ToyGame(levels=1, budget=12)
    brain, _ = run(game, steps=60, countdown_mask=False)
    assert brain.policy.mask is None


def test_expiry_is_read_from_the_bar_not_the_clock():
    """Once the bar is known, a death with the bar empty is expiry; with the bar full it is not.
    (planner off: these tests exercise the bar logic; a deterministic planner replays the same
    opening, which by design gives the independence rule no evidence.)"""
    import numpy as np

    game = ToyGame(levels=1, budget=12)
    brain, _ = run(game, steps=60, planner=False)
    explorer = brain.policy
    assert explorer.mask is not None and explorer.drain_values
    empty = game.grid.copy()
    empty[7, :] = 0
    full = game.grid.copy()
    full[7, :] = 6
    explorer.last_grid = empty
    assert explorer._bar_drained()
    explorer.last_grid = full
    assert not explorer._bar_drained()
    explorer.budget = None            # the clock rule is off; the bar alone decides
    explorer.last_grid = empty
    before = explorer.diagnostics["budget_deaths"]
    explorer.pending = (next(iter(explorer.graph.nodes)), (3, None, None))
    explorer._on_game_over()
    assert explorer.diagnostics["budget_deaths"] == before + 1


def test_death_with_energy_left_is_still_a_lethal_edge():
    game = ToyGame(levels=1, budget=40, extra_cells={(1, 2): 3})   # trap next to the start
    brain, _ = run(game, steps=120)
    explorer = brain.policy
    assert explorer.diagnostics["game_overs"] >= 1
    assert explorer.diagnostics["game_over_retries"] == 0
    trap_deaths = explorer.diagnostics["game_overs"] - explorer.diagnostics["budget_deaths"]
    assert trap_deaths >= 1


# --- action-effect prior --------------------------------------------------------------

def test_dead_click_classes_are_explored_last():
    """Walls never react to clicks; after a few tries the explorer stops clicking them."""
    game = ToyGame(levels=1, available=[6], extra_cells={(2, 2): 5, (5, 5): 5, (6, 6): 5})
    brain, log = run(game, steps=40)
    wall_clicks = [c for _, c in log if c.action_id == 6 and game.grid[c.y, c.x] == 2]
    assert len(wall_clicks) <= 4
    prior = brain.policy.prior
    assert prior.score((6, 5, "1-4")) > prior.score((6, 2, "5-16"))   # buttons learned as useful
    button_steps = [i for i, (_, c) in enumerate(log) if c.action_id == 6 and (c.y, c.x) in {(2, 2), (5, 5), (6, 6)}]
    assert sorted(button_steps)[2] <= 6                                # all three found almost at once


def test_lethal_commit_is_deferred_after_two_deaths():
    game = ToyGame(levels=1, available=[1, 2, 3, 4, 5], extra_cells={(6, 6): 7})
    brain, log = run(game, steps=400)
    ex = brain.policy
    assert ex.prior.deferred((5,)) or game.levels_completed == 1
    # once deferred, the commit is only pressed when nothing live is left: every later press
    # is a deferred pick, and it is never pressed twice from the same state
    presses = [(o.grid.tobytes(), c) for o, c in log if c.action_id == 5 and o.grid is not None]
    states = [g for g, _ in presses]
    assert len(states) == len(set(states))
    assert ex.diagnostics["deferred_picks"] >= len(presses) - 2


def test_deferred_actions_still_get_tested_when_nothing_else_is_left():
    game = ToyGame(levels=1, available=[1, 2, 3, 4, 5], extra_cells={(6, 6): 7})
    brain, _ = run(game, steps=2500)
    assert game.levels_completed == 1


def test_action_prior_can_be_disabled():
    game = ToyGame(levels=1, available=[1, 2, 3, 4, 5], extra_cells={(6, 6): 7})
    brain, _ = run(game, steps=100, action_prior=False)
    assert brain.policy.prior is None
