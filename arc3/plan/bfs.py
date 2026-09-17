"""Breadth-first search over known edges. Unit cost per action, so BFS is optimal."""
from __future__ import annotations

from collections import deque
from typing import Callable

from arc3.types import ActionKey
from arc3.world_model import StateGraph

Frontier = Callable[[str], bool]


def path_to_nearest_frontier(graph: StateGraph, start: str,
                             is_frontier: Frontier | None = None) -> list[ActionKey] | None:
    """Actions leading from `start` to the closest state satisfying `is_frontier`
    (default: has untested actions).

    [] when `start` itself is a frontier. None when no frontier state is reachable.
    No-op self loops and game-over edges are never followed.
    """
    if start not in graph:
        return None
    frontier = is_frontier or (lambda key: bool(graph.untested(key)))
    parent: dict[str, tuple[str, ActionKey] | None] = {start: None}
    queue: deque[str] = deque([start])
    while queue:
        key = queue.popleft()
        if frontier(key):
            return _unwind(parent, key)
        for action, edge in graph.nodes[key].tested.items():
            dst = edge.dst_key
            if dst is None or edge.game_over or dst == key or dst in parent or dst not in graph:
                continue
            parent[dst] = (key, action)
            queue.append(dst)
    return None


def _unwind(parent: dict[str, tuple[str, ActionKey] | None], key: str) -> list[ActionKey]:
    path: list[ActionKey] = []
    while parent[key] is not None:
        key, action = parent[key]
        path.append(action)
    path.reverse()
    return path
