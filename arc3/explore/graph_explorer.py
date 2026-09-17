"""Baseline 1: systematic exploration of the state graph (after arXiv 2512.24156).

Per state: candidate actions = legal simple actions + one click per segmented object.
Choice rule: an untested action here (simple actions first, then clicks, uniform within the
tier); else follow the shortest known path to the nearest state with untested actions; else a
random legal action. Actions that ended the game are tested edges and are never planned
through. The graph is rebuilt on every level change.

Attempts (start to game over or level-up) are remembered so that an energy bar can be
recognised and dropped from the state key, and so that deaths at a fixed per-attempt step
count are treated as budget expiry rather than as a lethal action.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Any

import numpy as np

from arc3.perception import AttemptSignature, countdown_mask_from_signatures, segment_objects, state_hash
from arc3.plan import path_to_nearest_frontier
from arc3.types import COMPLEX_ACTION_ID, ActionChoice, ActionKey, Observation
from arc3.world_model import StateGraph

KEPT_ATTEMPTS = 10  # attempt signatures remembered per level (sparse, tiny)
DRAINED_FRACTION = 0.9  # bar cells at their drained value => the death was an expiry


class GraphExplorer:
    def __init__(self, rng: random.Random, max_nodes: int = 5000, max_clicks: int = 64,
                 use_countdown_mask: bool = True, budget_aware: bool = True) -> None:
        self.rng = rng
        self.max_nodes = max_nodes
        self.max_clicks = max_clicks
        self.use_countdown_mask = use_countdown_mask
        self.budget_aware = budget_aware
        self.graph = StateGraph(max_nodes)
        self.level_index = 0
        self.current_key: str | None = None
        self.pending: tuple[str, ActionKey] | None = None
        self.plan: list[tuple[str, ActionKey]] = []  # (expected state key, action)
        self.trace: list[ActionKey] = []  # actions since the level started
        self._last_levels: int | None = None
        # per-level attempt memory
        self.mask: np.ndarray | None = None
        self.drain_values: dict[tuple[int, int], int] = {}  # bar cell -> value it drains to
        self.last_grid: np.ndarray | None = None
        self.budget: int | None = None
        self.attempts: list[AttemptSignature] = []
        self.attempt = AttemptSignature()
        self.attempt_actions = 0
        self.death_lengths: Counter = Counter()
        self.diagnostics: dict[str, Any] = {
            "states": 0, "edges": 0, "inconsistent": 0, "repeats": 0, "game_overs": 0,
            "game_over_retries": 0, "exhausted": 0, "capped": 0, "plans": 0, "plan_steps": 0,
            "levels_seen": 0, "win_path_lengths": [], "budget_deaths": 0, "mask_cells": 0,
            "budget": None, "graph_rebuilds": 0,
        }

    # -- learning from what happened -------------------------------------------------------

    def observe(self, observation: Observation) -> None:
        levels = observation.levels_completed
        if self._last_levels is not None and levels > self._last_levels:
            self._level_changed(levels)
        self._last_levels = levels

        if observation.state == "GAME_OVER":
            self._on_game_over()
            return
        if observation.grid is None:
            self._forget_position()
            return

        if self.attempt.length == 0:
            self.attempt_actions = 0
        elif self.pending is not None:
            self.attempt_actions += 1
        self.attempt.push(observation.grid, self.pending[1] if self.pending else None)
        self.last_grid = observation.grid

        key = state_hash(observation.grid, self.mask)
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

    def _on_game_over(self) -> None:
        self.diagnostics["game_overs"] += 1
        died_at = self.attempt_actions + 1  # the pending action counts
        expired = self.budget_aware and (
            self._bar_drained()
            or (self.budget is not None and died_at >= self.budget)
        )
        if self.pending is not None:
            src, action = self.pending
            if expired:
                self.diagnostics["budget_deaths"] += 1
            else:
                self.graph.record(src, action, None, changed=False, game_over=True, level_up=False)
        self.death_lengths[died_at] += 1
        self._close_attempt()
        self._learn_budget()
        self._forget_position()

    def _bar_drained(self) -> bool:
        """True when the learned bar cells read as empty in the last frame before death."""
        if not self.drain_values or self.last_grid is None:
            return False
        grid = self.last_grid
        hits = sum(1 for (y, x), v in self.drain_values.items()
                   if y < grid.shape[0] and x < grid.shape[1] and grid[y, x] == v)
        return hits / len(self.drain_values) >= DRAINED_FRACTION

    def _close_attempt(self) -> None:
        if self.attempt.length >= 2:
            self.attempts = (self.attempts + [self.attempt])[-KEPT_ATTEMPTS:]
        self.attempt = AttemptSignature()
        self.attempt_actions = 0
        self._learn_mask()

    def _learn_mask(self) -> None:
        if not self.use_countdown_mask or len(self.attempts) < 2:
            return
        shape = self.attempts[-1].shape
        if shape is None:
            return
        mask = countdown_mask_from_signatures(self.attempts, shape)
        if not mask.any():
            return
        if self.mask is None or mask.shape != self.mask.shape or not np.array_equal(mask, self.mask):
            self.mask = mask
            self.drain_values = self._drain_values(mask)
            self.diagnostics["mask_cells"] = int(mask.sum())
            self._rebuild_graph()

    def _drain_values(self, mask: np.ndarray) -> dict[tuple[int, int], int]:
        values: dict[tuple[int, int], int] = {}
        for sig in self.attempts:
            for cell, (_offset, value) in sig.once.items():
                if mask[cell] and cell not in values:
                    values[cell] = value
        return values

    def _learn_budget(self) -> None:
        if not self.budget_aware or self.budget is not None:
            return
        length, count = self.death_lengths.most_common(1)[0]
        if count >= 2:
            self.budget = length
            self.diagnostics["budget"] = length
            self._rebuild_graph()  # earlier expiries were recorded as lethal edges

    def _rebuild_graph(self) -> None:
        self.graph = StateGraph(self.max_nodes)
        self.diagnostics["graph_rebuilds"] += 1
        self._forget_position()

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
        self.mask = None
        self.drain_values = {}
        self.last_grid = None
        self.budget = None
        self.attempts = []
        self.attempt = AttemptSignature()
        self.attempt_actions = 0
        self.death_lengths = Counter()
        self.diagnostics["mask_cells"] = 0
        self.diagnostics["budget"] = None
        self._forget_position()

    def _forget_position(self) -> None:
        self.pending = None
        self.plan = []
        self.current_key = None

    def _sync_counters(self) -> None:
        self.diagnostics["states"] = self.graph.size()
        self.diagnostics["edges"] = self.graph.edges
        self.diagnostics["inconsistent"] = self.graph.inconsistent
