"""Orchestrator contract, without the game engine."""
from __future__ import annotations

import numpy as np
import pytest

from arc3.agent import ActionChoice, Observation, Orchestrator
from arc3.config import Arc3Config

RESET, A1, A6 = 0, 1, 6


def obs(state: str = "NOT_FINISHED", actions: list[int] | None = None, levels: int = 0,
        win_levels: int = 3, grid: np.ndarray | None = None) -> Observation:
    if grid is None and state == "NOT_FINISHED":
        grid = np.zeros((8, 8), dtype=np.int8)
    return Observation(
        state=state,
        levels_completed=levels,
        win_levels=win_levels,
        grid=grid,
        available_actions=[1, 2, 3, 4, 6] if actions is None else actions,
    )


def make(seed: int = 0, **overrides) -> Orchestrator:
    cfg = Arc3Config(seed=seed, **overrides)
    return Orchestrator(cfg, game_id="test", started_at=0.0)


def test_config_defaults_are_seeded_and_offline():
    cfg = Arc3Config()
    assert cfg.seed == 0
    assert cfg.reasoner_enabled is False
    assert cfg.global_budget_s > 0


def test_resets_when_not_played():
    choice = make().choose(obs(state="NOT_PLAYED", grid=None), now=1.0)
    assert choice.action_id == RESET


def test_resets_when_game_over():
    choice = make().choose(obs(state="GAME_OVER", grid=None), now=1.0)
    assert choice.action_id == RESET


def test_never_resets_while_playing():
    agent = make()
    for _ in range(50):
        assert agent.choose(obs(), now=1.0).action_id != RESET


def test_action_is_always_one_of_available_actions():
    agent = make()
    for _ in range(50):
        assert agent.choose(obs(actions=[2, 5]), now=1.0).action_id in (2, 5)


def test_action6_carries_coordinates_inside_the_grid():
    agent = make()
    for _ in range(50):
        c = agent.choose(obs(actions=[6], grid=np.zeros((10, 12), dtype=np.int8)), now=1.0)
        assert c.action_id == A6
        assert 0 <= c.x < 12 and 0 <= c.y < 10


def test_simple_actions_have_no_coordinates():
    c = make().choose(obs(actions=[1]), now=1.0)
    assert c.action_id == A1 and c.x is None and c.y is None


def test_falls_back_to_random_legal_action_when_policy_raises():
    agent = make()

    def broken_policy(observation):
        raise RuntimeError("boom")

    agent.policy = broken_policy
    c = agent.choose(obs(actions=[3, 4]), now=1.0)
    assert c.action_id in (3, 4)
    assert agent.diagnostics["fallbacks"] == 1


def test_done_on_win():
    assert make().is_done(obs(state="WIN", grid=None), now=1.0)
    assert not make().is_done(obs(), now=1.0)


def test_done_when_global_budget_is_spent():
    agent = make(global_budget_s=100.0)
    assert not agent.is_done(obs(), now=50.0)
    assert agent.is_done(obs(), now=100.5)


def test_done_when_per_game_action_cap_is_reached():
    agent = make(max_actions_per_game=3)
    for _ in range(3):
        agent.choose(obs(), now=1.0)
    assert agent.is_done(obs(), now=1.0)


def test_same_seed_gives_same_action_sequence():
    a, b = make(seed=7), make(seed=7)
    seq_a = [a.choose(obs(actions=[1, 2, 3, 4, 6]), now=1.0) for _ in range(20)]
    seq_b = [b.choose(obs(actions=[1, 2, 3, 4, 6]), now=1.0) for _ in range(20)]
    assert seq_a == seq_b


def test_diagnostics_count_actions_and_resets():
    agent = make()
    agent.choose(obs(state="NOT_PLAYED", grid=None), now=1.0)
    agent.choose(obs(), now=1.0)
    agent.choose(obs(), now=1.0)
    d = agent.diagnostics
    assert d["actions"] == 2 and d["resets"] == 1


def test_action_choice_is_a_plain_value():
    c = ActionChoice(action_id=1, x=None, y=None, reason="r")
    assert c == ActionChoice(action_id=1, x=None, y=None, reason="r")
