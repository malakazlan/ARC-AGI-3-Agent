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
    # trap right next to the start; goal removed so exploration keeps going until the trap is tested
    game = ToyGame(levels=1, extra_cells={(1, 2): 3, (6, 6): 0})
    brain, log = run(game, steps=120, planner=False)
    explorer = brain.policy
    # two traps (one placed, one in the layout), up to four approaches each; every (state, action)
    # pair may end the game once
    assert 1 <= game.game_overs <= 8
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
    brain, _ = run(game, steps=120, dial_cap=True, breadth_first=True)
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


# --- effects by signature: predictable actions are not executed ------------------------

def _explorer_seeing(grid, available, **kw):
    """An explorer that has observed one state with the given grid (no engine)."""
    import random
    from arc3.explore import GraphExplorer
    from arc3.types import Observation

    kw.setdefault("verify_first", False)
    ex = GraphExplorer(random.Random(0), use_action_prior=False, **kw)
    ex.observe(Observation("NOT_FINISHED", 0, 1, grid, list(available)))
    return ex


def test_click_with_a_global_no_op_effect_is_skipped_and_recorded_as_a_predicted_self_loop():
    import numpy as np

    g = np.zeros((8, 8), dtype=np.int8)
    g[3, 0:6] = 2                                   # a wall
    g[6, 6] = 5                                     # a button
    ex = _explorer_seeing(g, [6])
    key = ex.current_key
    wall = next(a for a in ex.graph.untested(key) if g[a[2], a[1]] == 2)
    sig = ex.click_sig[(key, wall)]
    for _ in range(3):
        ex.click_effects.record(sig, (wall[2], wall[1]), g, g)     # three consistent no-ops elsewhere
    live = ex._live_untested(key, count=True)
    assert wall not in live
    assert ex.diagnostics["effects_avoided"] == 1
    ex._record_predicted_edges(key)
    edge = ex.graph.edge(key, wall)
    assert edge is not None and edge.predicted and edge.dst_key == key


def test_click_whose_predicted_state_is_unknown_is_still_executed():
    import numpy as np

    g = np.zeros((8, 8), dtype=np.int8)
    g[6, 6] = 5
    ex = _explorer_seeing(g, [6])
    key = ex.current_key
    button = next(a for a in ex.graph.untested(key) if g[a[2], a[1]] == 5)
    sig = ex.click_sig[(key, button)]
    after = g.copy(); after[6, 6] = 0
    for _ in range(3):
        ex.click_effects.record(sig, (6, 6), g, after)          # removal is global now
    assert button in ex._live_untested(key, count=True)         # but the removed state is new
    assert ex.diagnostics["effects_avoided"] == 0


def test_click_into_an_already_known_state_becomes_a_predicted_edge():
    import numpy as np
    from arc3.types import Observation

    g = np.zeros((8, 8), dtype=np.int8)
    g[6, 6] = 5
    ex = _explorer_seeing(g, [6])
    key = ex.current_key
    button = next(a for a in ex.graph.untested(key) if g[a[2], a[1]] == 5)
    sig = ex.click_sig[(key, button)]
    after = g.copy(); after[6, 6] = 0
    for _ in range(3):
        ex.click_effects.record(sig, (6, 6), g, after)
    ex.observe(Observation("NOT_FINISHED", 0, 1, after, [6]))   # the removed state is known now
    ex.observe(Observation("NOT_FINISHED", 0, 1, g, [6]))       # back at the start state
    assert button not in ex._live_untested(key, count=True)
    ex._record_predicted_edges(key)
    edge = ex.graph.edge(key, button)
    assert edge is not None and edge.predicted and edge.dst_key != key


def test_no_op_key_effect_is_skipped_by_avatar_appearance():
    import numpy as np

    g = np.zeros((8, 8), dtype=np.int8)
    g[4, 4] = 1
    ex = _explorer_seeing(g, [1, 2, 3, 4, 7])
    key = ex.current_key
    for _ in range(3):
        ex.key_effects.record(7, frozenset(), g, g)
    live = ex._live_untested(key, count=True)
    assert (7, None, None) not in live
    assert ex.diagnostics["effects_avoided"] == 1


# --- dials --------------------------------------------------------------------------------

def test_dial_key_is_pressed_at_most_a_few_cycles_not_once_per_state():
    """ACTION7 cycles a lamp through 3 colours. Once the cycle is known, the explorer stops
    pressing it in every new position."""
    game = ToyGame(levels=1, available=[1, 2, 3, 4, 7], extra_cells={(6, 6): 0}, dial_cell=(0, 7))
    brain, log = run(game, steps=300, dial_cap=True, breadth_first=True)
    ex = brain.policy
    assert ex.dials.period((7,)) == 3
    sevens = sum(1 for _, c in log if c.action_id == 7)
    assert sevens <= 12
    assert ex.diagnostics["dial_capped"] > 0


# --- discovery: breadth over keys before depth --------------------------------------------

def test_each_key_is_tried_once_before_any_key_is_repeated():
    """The first presses must be four different keys, even when the first one succeeded."""
    game = ToyGame(levels=1)
    brain, log = run(game, steps=8, dial_cap=True, breadth_first=True)
    keys = [c.action_id for _, c in log if c.action_id in (1, 2, 3, 4)][:4]
    assert sorted(keys) == [1, 2, 3, 4]


def test_click_candidates_cover_every_signature_before_repeating_one():
    """70 dots and one big block with a 64-click cap: the block still gets a candidate click."""
    import numpy as np

    g = np.zeros((20, 16), dtype=np.int8)
    for i in range(70):
        g[2 * (i // 8), 2 * (i % 8)] = 2       # 70 isolated dots of colour 2 (rows 0-16, step 2)
    g[17:20, 12:15] = 5                         # one 3x3 block of colour 5
    ex = _explorer_seeing(g, [6])
    key = ex.current_key
    assert len(ex.graph.untested(key)) <= 64
    assert any(g[a[2], a[1]] == 5 for a in ex.graph.untested(key))


def test_exhausted_frontier_verifies_a_predicted_edge_instead_of_clicking_at_random():
    import numpy as np
    from arc3.types import Observation

    g = np.zeros((8, 8), dtype=np.int8)
    g[3, 0:6] = 2                                   # a wall
    g[6, 6] = 5                                     # a button
    ex = _explorer_seeing(g, [6])
    key = ex.current_key
    wall = next(a for a in ex.graph.untested(key) if g[a[2], a[1]] == 2)
    sig = ex.click_sig[(key, wall)]
    for _ in range(3):
        ex.click_effects.record(sig, (wall[2], wall[1]), g, g)
    for a in ex.graph.untested(key):
        if a != wall:
            ex.graph.record(key, a, key, changed=False, game_over=False, level_up=False)
    action, reason = ex._pick(key, Observation("NOT_FINISHED", 0, 1, g, [6]))
    assert action == wall
    assert "verify" in reason
    ex.graph.record(key, wall, key, changed=False, game_over=False, level_up=False)
    action, reason = ex._pick(key, Observation("NOT_FINISHED", 0, 1, g, [6]))
    assert g[action[2], action[1]] != 0             # a re-test of a candidate, not a background click


def test_a_click_rule_is_executed_once_before_it_is_trusted():
    """Three no-ops on one wall make a rule for the signature; the rule is verified on the
    second wall (one click) and only then are further instances skipped."""
    import numpy as np
    from arc3.types import Observation

    g = np.zeros((10, 10), dtype=np.int8)
    g[1, 0:6] = 2                                   # wall A
    g[5, 0:6] = 2                                   # wall B, same signature
    g[8, 0:6] = 2                                   # wall C
    g[9, 9] = 5                                     # a button
    ex = _explorer_seeing(g, [6], verify_first=True)
    key = ex.current_key
    walls = [a for a in ex.graph.untested(key) if g[a[2], a[1]] == 2]
    sig = ex.click_sig[(key, walls[0])]
    for _ in range(3):
        ex.click_effects.record(sig, (walls[0][2], walls[0][1]), g, g)
    live = ex._live_untested(key, count=True)
    assert walls[1] in live and walls[2] in live    # the rule is unverified: other instances stay live
    ex.pending = (key, walls[1])
    ex.observe(Observation("NOT_FINISHED", 0, 1, g, [6]))   # the click did nothing, as predicted
    assert sig in ex.verified_sigs
    live = ex._live_untested(key, count=True)
    assert walls[2] not in live                     # trusted now: the third wall is skipped
