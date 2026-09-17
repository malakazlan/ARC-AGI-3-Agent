"""Exploration policies: which untested (state, action) pair to go test next.

Interface only (Phase 2). Phase 3 adds the shortest-path-to-frontier explorer.
"""
from __future__ import annotations

from typing import Protocol

from arc3.agent import ActionChoice, Observation


class ExplorationPolicy(Protocol):
    def __call__(self, observation: Observation) -> ActionChoice: ...
