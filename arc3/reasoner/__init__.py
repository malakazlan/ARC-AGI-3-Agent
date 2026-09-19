"""Optional local LLM reasoner. Off by default and absent on Kaggle unless measured to help.

The orchestrator only ever calls `propose`; a None answer means "no opinion, use the rules".
The summary/prompt/render/client modules serve the offline Track B goal-naming experiment
(eval/reasoner_eval.py); nothing there is wired into the agent.
"""
from __future__ import annotations

from typing import Protocol

from arc3.reasoner.client import MockClient, VLLMClient
from arc3.reasoner.prompt import build_messages, parse_answer
from arc3.reasoner.render import PALETTE, grid_to_png_b64
from arc3.reasoner.summary import TEMPLATE_MEANINGS, world_summary
from arc3.types import ActionChoice, Observation


class Reasoner(Protocol):
    def propose(self, observation: Observation, context: dict) -> ActionChoice | None: ...


class NullReasoner:
    """The disabled reasoner. Always defers to the rules-only agent."""

    def propose(self, observation: Observation, context: dict) -> ActionChoice | None:
        return None


__all__ = [
    "MockClient",
    "NullReasoner",
    "PALETTE",
    "Reasoner",
    "TEMPLATE_MEANINGS",
    "VLLMClient",
    "build_messages",
    "grid_to_png_b64",
    "parse_answer",
    "world_summary",
]
