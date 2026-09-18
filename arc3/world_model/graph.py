"""Directed graph over state keys. Nodes know their candidate actions and which were tested."""
from __future__ import annotations

from dataclasses import dataclass, field

from arc3.types import ActionKey


@dataclass
class Edge:
    dst_key: str | None  # None when the action ended the game
    changed: bool
    game_over: bool
    level_up: bool
    predicted: bool = False  # from a learned effect, not yet executed; overwritten when executed


@dataclass
class Node:
    key: str
    candidates: list[ActionKey]
    classes: dict[ActionKey, tuple] = field(default_factory=dict)  # action -> effect class
    tested: dict[ActionKey, Edge] = field(default_factory=dict)

    def untested(self) -> list[ActionKey]:
        return [a for a in self.candidates if a not in self.tested]


class StateGraph:
    """Within-level transition graph. `max_nodes` bounds memory; extra states are not stored."""

    def __init__(self, max_nodes: int = 5000) -> None:
        self.max_nodes = max_nodes
        self.nodes: dict[str, Node] = {}
        self.inconsistent = 0  # same (state, action) seen with a different result
        self.edges = 0

    def add_node(self, key: str, candidates: list[ActionKey],
                 classes: dict[ActionKey, tuple] | None = None) -> bool:
        """Register a state. Returns False when the cap refuses a new state."""
        if key in self.nodes:
            return True
        if len(self.nodes) >= self.max_nodes:
            return False
        self.nodes[key] = Node(key, list(candidates), dict(classes or {}))
        return True

    def __contains__(self, key: str) -> bool:
        return key in self.nodes

    def record(self, src_key: str, action: ActionKey, dst_key: str | None,
               changed: bool, game_over: bool, level_up: bool, predicted: bool = False) -> None:
        node = self.nodes.get(src_key)
        if node is None:
            return
        previous = node.tested.get(action)
        if previous is not None and previous.dst_key != dst_key and not previous.predicted:
            self.inconsistent += 1
        elif previous is None:
            self.edges += 1
        node.tested[action] = Edge(dst_key, changed, game_over, level_up, predicted)

    def edge(self, src_key: str, action: ActionKey) -> Edge | None:
        node = self.nodes.get(src_key)
        return None if node is None else node.tested.get(action)

    def untested(self, key: str) -> list[ActionKey]:
        node = self.nodes.get(key)
        return [] if node is None else node.untested()

    def action_class(self, key: str, action: ActionKey) -> tuple:
        node = self.nodes.get(key)
        if node is None:
            return (action[0],)
        return node.classes.get(action, (action[0],))

    def size(self) -> int:
        return len(self.nodes)
