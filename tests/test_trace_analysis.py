"""Offline trajectory analysis on synthetic traces. No engine."""
from __future__ import annotations

import numpy as np

from eval.traces import Trace, analyze


def make_trace(grids, actions, levels=None, states=None) -> Trace:
    n = len(grids)
    return Trace(
        game_id="toy",
        seed=0,
        grids=np.stack(grids).astype(np.int8),
        actions=np.array(actions, dtype=np.int16),
        xs=np.full(n, -1, dtype=np.int16),
        ys=np.full(n, -1, dtype=np.int16),
        levels=np.array(levels or [0] * n, dtype=np.int16),
        states=np.array(states or ["NOT_FINISHED"] * n),
        n_frames=np.ones(n, dtype=np.int16),
    )


def test_noop_rate_counts_actions_that_changed_nothing():
    g = np.zeros((8, 8), dtype=np.int8)
    g2 = g.copy(); g2[1, 1] = 3
    # step i shows the grid AFTER action i; grid before step 0 is the reset frame (given first)
    trace = make_trace([g, g, g2, g2], actions=[0, 1, 2, 3])
    report = analyze(trace)
    assert report["steps"] == 3                 # the leading reset frame is not a step
    assert report["noop_rate"] == 2 / 3


def test_volatile_cells_are_those_that_change_on_most_steps():
    grids = []
    for t in range(10):
        g = np.zeros((8, 8), dtype=np.int8)
        g[0, 0] = t % 4          # timer cell changes every step
        g[5, 5] = 7 if t >= 5 else 0   # a cell that changes once
        grids.append(g)
    trace = make_trace(grids, actions=[0] + [1] * 9)
    report = analyze(trace, volatile_threshold=0.5)
    assert report["volatile_cells"] == [(0, 0)]


def test_unique_states_drop_when_volatile_cells_are_masked():
    grids = []
    for t in range(10):
        g = np.zeros((8, 8), dtype=np.int8)
        g[0, 0] = t % 5
        grids.append(g)
    trace = make_trace(grids, actions=[0] + [1] * 9)
    report = analyze(trace, volatile_threshold=0.5)
    assert report["unique_states_raw"] == 5
    assert report["unique_states_masked"] == 1


def test_per_action_effect_table():
    g = np.zeros((8, 8), dtype=np.int8)
    g2 = g.copy(); g2[2, 2] = 1
    trace = make_trace([g, g2, g2, g], actions=[0, 1, 2, 1])
    report = analyze(trace)
    assert report["per_action"][1] == {"count": 2, "changed": 2}
    assert report["per_action"][2] == {"count": 1, "changed": 0}


def test_level_ups_and_game_overs_are_counted_with_step_index():
    g = np.zeros((8, 8), dtype=np.int8)
    trace = make_trace([g] * 5, actions=[0, 1, 1, 1, 1], levels=[0, 0, 1, 1, 1],
                       states=["NOT_FINISHED"] * 3 + ["GAME_OVER", "NOT_FINISHED"])
    report = analyze(trace)
    assert report["level_up_steps"] == [2]
    assert report["game_over_steps"] == [3]
