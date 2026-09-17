"""Baseline 1: systematic exploration of the state graph (after arXiv 2512.24156).

Per state: candidate actions = legal simple actions + one click per segmented object.
Choice rule: an untested action here (simple actions first, then clicks, uniform within the
tier); else follow the shortest known path to the nearest state with untested actions; else a
random legal action. Actions that ended the game are tested edges and are never planned
through. The graph is rebuilt on every level change.
"""
from __future__ import annotations

import random
from typing import Any

from arc3.perception import segment_objects, state_hash
from arc3.plan import path_to_nearest_frontier
from arc3.types import COMPLEX_ACTION_ID, ActionChoice, ActionKey, Observation
from arc3.world_model import StateGraph


class GraphExplorer:
    def __init__(self, rng: random.Random, max_nodes: int = 5000, max_clicks: int = 64) -> None:
        self.rng = rng
        self.max_nodes = max_nodes
        self.max_clicks = max_clicks
        self.graph = StateGraph(max_nodes)
        self.level_index = 0
        self.current_key: str | None = None
        self.pending: tuple[str, ActionKey] | None = None
        self.plan: list[tuple[str, ActionKey]] = []  # (expected state key, action)
        self.trace: list[ActionKey] = []  # actions since the level started
        self._last_levels: int | None = None
        self.diagnostics: dict[str, Any] = {
            "states": 0, "edges": 0, "inconsistent": 0, "repeats": 0, "game_overs": 0,
            "game_over_retries": 0, "exhausted": 0, "capped": 0, "plans": 0, "plan_steps": 0,
            "levels_seen": 0, "win_path_lengths": [],
        }

    # -- learning from what happened -------------------------------------------------------

    def observe(self, observation: Observation) -> None:
        levels = observation.levels_completed
        if self._last_levels is not None and levels > self._last_levels:
            self._level_changed(levels)
        self._last_levels = levels

        if observation.state == "GAME_OVER":
            if self.pending is not None:
                src, action = self.pending
                self.graph.record(src, action, None, changed=False, game_over=True, level_up=False)
                self.diagnostics["game_overs"] += 1
            self._forget_position()
            return
        if observation.grid is None:
            self._forget_position()
            return

        key = state_hash(observation.grid)
        if self.pending is not None:
            src, action = self.pending
            self.graph.record(src, action, key, changed=key != src, game_over=False, level_up=False)
            self.pending = None
        if key not in self.graph:
            if self.diagnostics["levels_seen"] == 0 or self.graph.size() == 0:
                self.diagnostics["levels_seen"] += 1
            if not self.graph.add_node(key, self._candidates(observation)):
                self.diagnostics["capped"] += 1
        self.current_key = key
        self._sync_counters()

    # -- choosing --------------------------------------------------------------------------

    def __call__(self, observation: Observation) -> ActionChoice:
        if self.current_key is None:
            self.observe(observation)
        key = self.current_key
        action, reason = self._pick(key, observation)
        if key is not None and key in self.graph:
            edge = self.graph.edge(key, action)
            if edge is not None and edge.game_over:
                self.diagnostics["game_over_retries"] += 1
            if edge is not None and self.graph.untested(key):
                self.diagnostics["repeats"] += 1
            self.pending = (key, action)
        self.trace.append(action)
        return ActionChoice(action[0], action[1], action[2], reason)

    def _pick(self, key: str | None, observation: Observation) -> tuple[ActionKey, str]:
        if key is None or key not in self.graph:
            return self._random_legal(observation), "graph: state not stored"
        untested = self.graph.untested(key)
        if untested:
            self.plan = []
            simple = [a for a in untested if a[0] != COMPLEX_ACTION_ID]
            tier = simple or untested
            return self.rng.choice(tier), f"graph: untested ({len(untested)} left here)"
        if self.plan and self.plan[0][0] == key:
            _, action = self.plan.pop(0)
            self.diagnostics["plan_steps"] += 1
            return action, f"graph: plan step ({len(self.plan)} left)"
        self.plan = self._plan_from(key)
        if self.plan:
            self.diagnostics["plans"] += 1
            _, action = self.plan.pop(0)
            self.diagnostics["plan_steps"] += 1
            return action, f"graph: new plan ({len(self.plan)} more)"
        self.diagnostics["exhausted"] += 1
        return self._random_legal(observation), "graph: frontier exhausted, random legal"

    def _plan_from(self, key: str) -> list[tuple[str, ActionKey]]:
        path = path_to_nearest_frontier(self.graph, key)
        if not path:
            return []
        steps: list[tuple[str, ActionKey]] = []
        cursor = key
        for action in path:
            steps.append((cursor, action))
            cursor = self.graph.edge(cursor, action).dst_key  # type: ignore[union-attr]
        return steps

    # -- candidates ------------------------------------------------------------------------

    def _candidates(self, observation: Observation) -> list[ActionKey]:
        legal = observation.available_actions
        keys: list[ActionKey] = [(a, None, None) for a in legal if a != COMPLEX_ACTION_ID]
        if COMPLEX_ACTION_ID in legal and observation.grid is not None:
            objects = segment_objects(observation.grid)
            objects.sort(key=lambda o: (o.size, o.bbox))  # small things first: buttons
            for obj in objects[: self.max_clicks]:
                y, x = obj.anchor
                keys.append((COMPLEX_ACTION_ID, int(x), int(y)))
            if not objects:
                h, w = observation.grid.shape
                keys.append((COMPLEX_ACTION_ID, w // 2, h // 2))
        return keys

    def _random_legal(self, observation: Observation) -> ActionKey:
        legal = observation.available_actions or [1]
        action_id = self.rng.choice(legal)
        if action_id != COMPLEX_ACTION_ID:
            return (action_id, None, None)
        h, w = observation.grid.shape if observation.grid is not None else (64, 64)
        return (action_id, self.rng.randrange(w), self.rng.randrange(h))

    # -- bookkeeping -----------------------------------------------------------------------

    def _level_changed(self, levels: int) -> None:
        self.diagnostics["win_path_lengths"].append(len(self.trace))
        self.level_index = levels
        self.graph = StateGraph(self.max_nodes)
        self.trace = []
        self._forget_position()

    def _forget_position(self) -> None:
        self.pending = None
        self.plan = []
        self.current_key = None

    def _sync_counters(self) -> None:
        self.diagnostics["states"] = self.graph.size()
        self.diagnostics["edges"] = self.graph.edges
        self.diagnostics["inconsistent"] = self.graph.inconsistent
