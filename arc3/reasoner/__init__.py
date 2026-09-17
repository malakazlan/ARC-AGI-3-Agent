"""Optional local LLM reasoner. Off by default and absent on Kaggle unless measured to help.

The orchestrator only ever calls `propose`; a None answer means "no opinion, use the rules".
"""
from __future__ import annotations

from typing import Protocol

from arc3.agent import ActionChoice, Observation


class Reasoner(Protocol):
    def propose(self, observation: Observation, context: dict) -> ActionChoice | None: ...


class NullReasoner:
    """The disabled reasoner. Always defers to the rules-only agent."""

    def propose(self, observation: Observation, context: dict) -> ActionChoice | None:
        return None
