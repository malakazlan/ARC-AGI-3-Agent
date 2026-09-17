"""Re-checkable facts from docs/ENVIRONMENT.md, run against the local engine offline.

Skips when no game is cached in environment_files/ (run `make verify-local` once first).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "environment_files"

pytestmark = pytest.mark.engine


@pytest.fixture(scope="module")
def cached_env():
    import arc_agi
    from arc_agi import OperationMode

    if not ENV_DIR.exists():
        pytest.skip("no cached games; run `make verify-local` once")
    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ENV_DIR))
    envs = arc.get_environments()
    if not envs:
        pytest.skip("no cached games; run `make verify-local` once")
    return arc, envs[0].game_id.split("-")[0]


def test_reset_frame_shape_and_values(cached_env):
    from arcengine import GameAction, GameState

    arc, gid = cached_env
    env = arc.make(gid, seed=0)
    frame = env.step(GameAction.RESET)
    assert frame.state is GameState.NOT_FINISHED
    assert frame.full_reset is True
    assert len(frame.frame) >= 1
    grid = np.asarray(frame.frame[-1])
    assert grid.ndim == 2 and grid.shape[0] <= 64 and grid.shape[1] <= 64
    assert grid.min() >= 0 and grid.max() <= 15
    assert set(frame.available_actions) <= set(range(1, 8))


def test_reset_is_not_counted_as_an_action(cached_env):
    from arcengine import GameAction

    arc, gid = cached_env
    env = arc.make(gid, seed=0)
    for _ in range(3):
        env.step(GameAction.RESET)
    first = GameAction.from_id(env.step(GameAction.RESET).available_actions[0])
    data = {"x": 0, "y": 0} if first.is_complex() else {}
    env.step(first, data=data)
    env.step(first, data=data)
    run = arc.get_scorecard().environments[-1].runs[-1]
    assert run.actions == 2


def test_same_seed_and_actions_reproduce_frames(cached_env):
    from arcengine import GameAction, GameState

    arc, gid = cached_env

    def rollout() -> list[bytes]:
        env = arc.make(gid, seed=0)
        frame = env.step(GameAction.RESET)
        out = []
        for i in range(30):
            if frame.state in (GameState.GAME_OVER, GameState.WIN):
                frame = env.step(GameAction.RESET)
                continue
            action = GameAction.from_id(frame.available_actions[i % len(frame.available_actions)])
            data = {"x": (i * 7) % 64, "y": (i * 13) % 64} if action.is_complex() else {}
            frame = env.step(action, data=data)
            if frame.frame:
                out.append(np.asarray(frame.frame[-1]).tobytes())
        return out

    assert rollout() == rollout()
