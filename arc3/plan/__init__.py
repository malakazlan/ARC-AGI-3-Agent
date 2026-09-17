"""Planning over the transition graph: shortest paths, replay of known wins.

Interface only (Phase 2). Phase 3 implements BFS shortest path to the frontier.
"""
from __future__ import annotations

from typing import Protocol

from arc3.world_model import Transition


class Planner(Protocol):
    def shortest_path(self, src_key: str, dst_key: str) -> list[Transition] | None: ...
