"""Orchestrator: turns observations into action choices, fail-safe, time-bounded.

Engine-agnostic on purpose. `agent/my_agent.py` adapts framework FrameData to Observation and
ActionChoice back to GameAction, so everything here is testable on synthetic grids.
"""
from __future__ import annotations

import random
import time
import zlib
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from arc3.config import Arc3Config

RESET_ID = 0
COMPLEX_ACTION_ID = 6
DEFAULT_GRID_SIZE = 64
NEEDS_RESET = ("NOT_PLAYED", "GAME_OVER")


@dataclass(frozen=True, eq=False)
class Observation:
    state: str  # GameState name: NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER
    levels_completed: int
    win_levels: int
    grid: np.ndarray | None  # last frame, int8 [y, x]; None before the first frame
    available_actions: list[int]


@dataclass(frozen=True)
class ActionChoice:
    action_id: int
    x: int | None
    y: int | None
    reason: str


Policy = Callable[[Observation], ActionChoice]

_PROCESS_STARTED_AT: float | None = None


def process_started_at() -> float:
    """Wall-clock start shared by every game in this process. First call fixes it."""
    global _PROCESS_STARTED_AT
    if _PROCESS_STARTED_AT is None:
        _PROCESS_STARTED_AT = time.time()
    return _PROCESS_STARTED_AT


def observation_from_frame(frame: Any) -> Observation:
    """Adapt a framework FrameData-like object. Empty frame lists (game over) give grid=None."""
    state = getattr(frame.state, "name", str(frame.state))
    frames = frame.frame or []
    grid = np.asarray(frames[-1], dtype=np.int8) if frames else None
    return Observation(
        state=state,
        levels_completed=int(frame.levels_completed),
        win_levels=int(frame.win_levels),
        grid=grid,
        available_actions=[int(a) for a in (frame.available_actions or [])],
    )


class Orchestrator:
    """One per game. Holds the RNG, the policy, counters, and the deadline."""

    def __init__(self, config: Arc3Config, game_id: str, started_at: float) -> None:
        self.config = config
        self.game_id = game_id
        self.started_at = started_at
        self.rng = random.Random(config.seed * 1_000_003 + zlib.crc32(game_id.encode()))
        self.policy: Policy = self._random_policy
        self.diagnostics: dict[str, Any] = {
            "game_id": game_id,
            "actions": 0,
            "resets": 0,
            "fallbacks": 0,
            "levels_completed": 0,
            "elapsed_s": 0.0,
        }

    # -- contract used by the framework adapter -------------------------------------------

    def is_done(self, observation: Observation, now: float) -> bool:
        self.diagnostics["levels_completed"] = observation.levels_completed
        self.diagnostics["elapsed_s"] = now - self.started_at
        if observation.state == "WIN":
            return True
        if now - self.started_at >= self.config.global_budget_s:
            return True
        return self.steps >= self.config.max_actions_per_game

    def choose(self, observation: Observation, now: float) -> ActionChoice:
        self.diagnostics["elapsed_s"] = now - self.started_at
        if observation.state in NEEDS_RESET:
            self.diagnostics["resets"] += 1
            return ActionChoice(RESET_ID, None, None, f"reset from {observation.state}")
        self.diagnostics["actions"] += 1
        try:
            return self.policy(observation)
        except Exception as exc:  # noqa: BLE001 - a crash on Kaggle scores zero everywhere
            self.diagnostics["fallbacks"] += 1
            return self._random_policy(observation, reason=f"fallback: {type(exc).__name__}")

    @property
    def steps(self) -> int:
        return self.diagnostics["actions"] + self.diagnostics["resets"]

    # -- policies --------------------------------------------------------------------------

    def _random_policy(self, observation: Observation, reason: str = "random legal") -> ActionChoice:
        legal = observation.available_actions or [1]
        action_id = self.rng.choice(legal)
        if action_id != COMPLEX_ACTION_ID:
            return ActionChoice(action_id, None, None, reason)
        height, width = _grid_shape(observation.grid)
        return ActionChoice(
            action_id, self.rng.randrange(width), self.rng.randrange(height), reason
        )


def _grid_shape(grid: np.ndarray | None) -> tuple[int, int]:
    if grid is None:
        return DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE
    return int(grid.shape[0]), int(grid.shape[1])
