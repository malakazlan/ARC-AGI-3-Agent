"""Orchestrator: turns observations into action choices, fail-safe, time-bounded.

Engine-agnostic on purpose. `agent/my_agent.py` adapts framework FrameData to Observation and
ActionChoice back to GameAction, so everything here is testable on synthetic grids.
"""
from __future__ import annotations

import random
import time
import zlib
from typing import Any, Callable

import numpy as np

from arc3.config import Arc3Config
from arc3.types import COMPLEX_ACTION_ID, RESET_ID, ActionChoice, Observation

__all__ = ["ActionChoice", "Observation", "Orchestrator", "observation_from_frame", "process_started_at"]

DEFAULT_GRID_SIZE = 64
NEEDS_RESET = ("NOT_PLAYED", "GAME_OVER")

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
        self.policy: Policy = self._build_policy(config)
        self._counters: dict[str, Any] = {
            "game_id": game_id,
            "actions": 0,
            "resets": 0,
            "fallbacks": 0,
            "levels_completed": 0,
            "elapsed_s": 0.0,
        }

    # -- contract used by the framework adapter -------------------------------------------

    def is_done(self, observation: Observation, now: float) -> bool:
        self._counters["levels_completed"] = observation.levels_completed
        self._counters["elapsed_s"] = now - self.started_at
        if observation.state == "WIN":
            self._notify_policy(observation)  # choose() never runs on WIN; let it record the win
            return True
        if now - self.started_at >= self.config.global_budget_s:
            return True
        return self.steps >= self.config.max_actions_per_game

    def choose(self, observation: Observation, now: float) -> ActionChoice:
        self._counters["elapsed_s"] = now - self.started_at
        self._counters["levels_completed"] = observation.levels_completed
        self._notify_policy(observation)
        if observation.state in NEEDS_RESET:
            self._counters["resets"] += 1
            return ActionChoice(RESET_ID, None, None, f"reset from {observation.state}")
        self._counters["actions"] += 1
        try:
            return self.policy(observation)
        except Exception as exc:  # noqa: BLE001 - a crash on Kaggle scores zero everywhere
            self._counters["fallbacks"] += 1
            return self._random_policy(observation, reason=f"fallback: {type(exc).__name__}")

    @property
    def steps(self) -> int:
        return self._counters["actions"] + self._counters["resets"]

    @property
    def diagnostics(self) -> dict[str, Any]:
        merged = dict(self._counters)
        merged.update(getattr(self.policy, "diagnostics", {}))
        return merged

    # -- policies --------------------------------------------------------------------------

    def _build_policy(self, config: Arc3Config) -> Policy:
        if config.policy == "graph":
            from arc3.explore import GraphExplorer  # local import: explore depends on types only

            return GraphExplorer(
                rng=self.rng,
                max_nodes=config.max_nodes_per_level,
                max_clicks=config.max_click_candidates,
                use_countdown_mask=config.countdown_mask,
                budget_aware=config.budget_aware,
                use_action_prior=config.action_prior,
            )
        return self._random_policy

    def _notify_policy(self, observation: Observation) -> None:
        observe = getattr(self.policy, "observe", None)
        if observe is None:
            return
        try:
            observe(observation)
        except Exception:  # noqa: BLE001
            self._counters["fallbacks"] += 1

    def _random_policy(self, observation: Observation, reason: str = "random legal") -> ActionChoice:
        legal = observation.available_actions or [1]
        action_id = self.rng.choice(legal)
        if action_id != COMPLEX_ACTION_ID:
            return ActionChoice(action_id, None, None, reason)
        height, width = _grid_shape(observation.grid)
        return ActionChoice(action_id, self.rng.randrange(width), self.rng.randrange(height), reason)


def _grid_shape(grid: np.ndarray | None) -> tuple[int, int]:
    if grid is None:
        return DEFAULT_GRID_SIZE, DEFAULT_GRID_SIZE
    return int(grid.shape[0]), int(grid.shape[1])
