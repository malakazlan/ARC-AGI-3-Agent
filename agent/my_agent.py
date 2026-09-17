"""Kaggle entry point. Thin adapter from the ARC-AGI-3-Agents framework to arc3.

Everything that thinks lives in `arc3/`. This file only converts FrameData to Observation,
ActionChoice to GameAction, keeps the process-wide deadline, and never lets an exception
escape (a crash on Kaggle scores zero on every game).

Contract (enforced by the framework): subclass `agents.agent.Agent`, class named `MyAgent`,
implement `is_done(frames, latest_frame)` and `choose_action(frames, latest_frame)`.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

from arcengine import FrameData, GameAction, GameState

from agents.agent import Agent


def _import_arc3():
    """Locally arc3 sits next to agent/; on Kaggle the notebook unpacks it to a bundle dir."""
    candidates = [
        os.environ.get("ARC3_BUNDLE_DIR", ""),
        "/tmp/arc3_bundle",
        str(Path(__file__).resolve().parents[1]),
    ]
    for candidate in candidates:
        if candidate and candidate not in sys.path:
            sys.path.insert(0, candidate)
    from arc3.agent import Orchestrator, observation_from_frame, process_started_at
    from arc3.config import Arc3Config

    return Orchestrator, observation_from_frame, process_started_at, Arc3Config


Orchestrator, observation_from_frame, process_started_at, Arc3Config = _import_arc3()


class MyAgent(Agent):
    """arc3 orchestrator behind the framework's Agent interface."""

    # The framework stops at MAX_ACTIONS; the real caps (time, per-game actions) live in arc3.
    MAX_ACTIONS = 100_000

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.brain = Orchestrator(Arc3Config(), game_id=self.game_id, started_at=process_started_at())

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        try:
            return self.brain.is_done(observation_from_frame(latest_frame), time.time())
        except Exception:  # noqa: BLE001
            return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        try:
            choice = self.brain.choose(observation_from_frame(latest_frame), time.time())
            action = GameAction.from_id(choice.action_id)
            if action.is_complex():
                action.set_data({"x": choice.x, "y": choice.y})
            action.reasoning = choice.reason
            return action
        except Exception as exc:  # noqa: BLE001
            return self._last_resort(latest_frame, exc)

    def diagnostics_line(self) -> str:
        record = dict(self.brain.diagnostics)
        record["ts"] = round(time.time(), 3)
        return json.dumps(record, separators=(",", ":"))

    def cleanup(self, scorecard: Any = None) -> None:
        if self._cleanup:
            print(f"ARC3DIAG {self.diagnostics_line()}", flush=True)
        super().cleanup(scorecard)

    @staticmethod
    def _last_resort(latest_frame: FrameData, exc: Exception) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            action = GameAction.RESET
        else:
            legal = [a for a in latest_frame.available_actions if 1 <= a <= 7] or [1]
            action = GameAction.from_id(random.choice(legal))
            if action.is_complex():
                action.set_data({"x": random.randrange(64), "y": random.randrange(64)})
        action.reasoning = f"last resort after {type(exc).__name__}"
        return action
