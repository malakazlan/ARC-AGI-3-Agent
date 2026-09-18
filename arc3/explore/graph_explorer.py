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
from arc3.plan import path_to_nearest_frontier, plan_moves
from arc3.types import COMPLEX_ACTION_ID, ActionChoice, ActionKey, Observation
from arc3.world_model import (
    ActionPrior, AvatarModel, PassabilityModel, StateGraph, cells_ahead, click_class, predict_move,
)

MOVE_KEYS = (1, 2, 3, 4)

KEPT_ATTEMPTS = 10  # attempt signatures remembered per level (sparse, tiny)
DRAINED_FRACTION = 0.9  # bar cells at their drained value => the death was an expiry


def _partial_stroke(actual: tuple[int, int] | None, vec: tuple[int, int]) -> bool:
    """True when `actual` is a shorter move in the same direction as `vec` (a slide stopped early)."""
    if actual is None:
        return False
    same_axis = all((a == 0) == (v == 0) for a, v in zip(actual, vec))
    same_sign = all(a * v >= 0 for a, v in zip(actual, vec))
    shorter = abs(actual[0]) + abs(actual[1]) < abs(vec[0]) + abs(vec[1])
    return same_axis and same_sign and shorter


class GraphExplorer:
    def __init__(self, rng: random.Random, max_nodes: int = 5000, max_clicks: int = 64,
                 use_countdown_mask: bool = True, budget_aware: bool = True,
                 use_action_prior: bool = True, use_planner: bool = True,
                 max_mismatches: int = 3) -> None:
        self.rng = rng
        self.max_nodes = max_nodes
        self.max_clicks = max_clicks
        self.use_countdown_mask = use_countdown_mask
        self.budget_aware = budget_aware
        self.prior: ActionPrior | None = ActionPrior() if use_action_prior else None
        # movement planner: game-level facts (avatar, vectors, passability) survive level changes
        self.avatar: AvatarModel | None = AvatarModel() if use_planner else None
        self.passability = PassabilityModel()
        self.max_mismatches = max_mismatches
        self.planning_enabled = use_planner
        self.mismatches = 0
        self.current_grid: np.ndarray | None = None
        self.expected: tuple[str, frozenset] | None = None  # prediction for the pending move
        self.move_plan: list[int] = []
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
            "budget": None, "graph_rebuilds": 0, "deferred_picks": 0,
            "retests_avoided": 0, "mismatches": 0, "planner_resets": 0, "planned_moves": 0,
            "avatar_known_at": None, "kill_colours": 0,
        }

    # -- learning from what happened -------------------------------------------------------

    def observe(self, observation: Observation) -> None:
        levels = observation.levels_completed
        if self._last_levels is not None and levels > self._last_levels:
            self._level_changed(levels)
        self._last_levels = levels

        if observation.state == "GAME_OVER":
            self._learn_death()
            self._on_game_over()
            return
        if observation.grid is None:
            self._forget_position()
            return

        self._learn_move(observation.grid)
        self.current_grid = observation.grid
        if self.attempt.length == 0:
            self.attempt_actions = 0
        elif self.pending is not None:
            self.attempt_actions += 1
        self.attempt.push(observation.grid, self.pending[1] if self.pending else None)
        self.last_grid = observation.grid

        key = state_hash(observation.grid, self.mask)
        if self.pending is not None:
            src, action = self.pending
            changed = key != src
            self.graph.record(src, action, key, changed=changed, game_over=False, level_up=False)
            self._record_effect(src, action, changed=changed, game_over=False)
            self.pending = None
        if key not in self.graph:
            if self.diagnostics["levels_seen"] == 0 or self.graph.size() == 0:
                self.diagnostics["levels_seen"] += 1
            candidates, classes = self._candidates(observation)
            if not self.graph.add_node(key, candidates, classes):
                self.diagnostics["capped"] += 1
        self.current_key = key
        self._sync_counters()

    # -- avatar, passability and prediction checks ------------------------------------------

    def _learn_move(self, grid: np.ndarray) -> None:
        """After a key press: update the avatar model, passability votes and the prediction check."""
        if self.avatar is None or self.pending is None or self.last_grid is None:
            self.expected = None
            return
        key = self.pending[1][0]
        if key not in MOVE_KEYS or self.last_grid.shape != grid.shape:
            self.expected = None
            return
        before = self.last_grid
        old_cells = self.avatar.last_cells if self.avatar.confident else None
        was_confident = self.avatar.confident
        outcome = self.avatar.observe(before, key, grid, self.mask)
        if not was_confident and self.avatar.confident and self.diagnostics["avatar_known_at"] is None:
            self.diagnostics["avatar_known_at"] = self.trace and len(self.trace)
        vec = self.avatar.vector(key)
        if old_cells and vec is not None and self.mask_ok(before):
            kind = outcome
            if outcome == "moved":
                actual = self.avatar.last_vector.get(key)
                new_cells = self.avatar.last_cells
                if actual == vec or _partial_stroke(actual, vec):
                    for (y, x) in new_cells - old_cells:
                        self.passability.vote(int(before[y, x]), "passes")
                    if actual != vec:
                        # slid until obstructed: the cells just beyond the reached position block
                        step = (int(np.sign(vec[0])), int(np.sign(vec[1])))
                        for (y, x) in self._in_bounds(cells_ahead(new_cells, step), before.shape):
                            self.passability.vote(int(before[y, x]), "blocks")
                else:
                    kind = "other"  # moved in an unexpected direction: no votes
            elif outcome == "blocked":
                for (y, x) in self._in_bounds(cells_ahead(old_cells, vec), before.shape):
                    self.passability.vote(int(before[y, x]), "blocks")
            if self.expected is not None and kind in ("moved", "blocked") and kind != self.expected[0]:
                for (y, x) in self._in_bounds(cells_ahead(old_cells, vec), before.shape):
                    self._on_mismatch(int(before[y, x]))
        self.expected = None

    def _learn_death(self) -> None:
        """A non-expiry death right after a key press: the colours ahead kill."""
        if self.avatar is None or self.pending is None or self.last_grid is None or not self.avatar.confident:
            return
        key = self.pending[1][0]
        vec = self.avatar.vector(key)
        cells = self.avatar.last_cells
        if key not in MOVE_KEYS or vec is None or not cells or self._bar_drained():
            return
        for (y, x) in self._in_bounds(cells_ahead(cells, vec), self.last_grid.shape):
            self.passability.vote(int(self.last_grid[y, x]), "kills")
            self.diagnostics["kill_colours"] += 1
        self.expected = None

    def _on_mismatch(self, colour: int) -> None:
        self.passability.contradict(colour)
        self.mismatches += 1
        self.diagnostics["mismatches"] += 1
        if self.mismatches >= self.max_mismatches and self.planning_enabled:
            self.planning_enabled = False
            self.diagnostics["planner_resets"] += 1
        self.move_plan = []

    def mask_ok(self, grid: np.ndarray) -> bool:
        return self.mask is None or self.mask.shape == grid.shape

    @staticmethod
    def _in_bounds(cells, shape) -> list[tuple[int, int]]:
        h, w = shape
        return [(y, x) for (y, x) in cells if 0 <= y < h and 0 <= x < w]

    def _planner_ready(self) -> bool:
        return (self.avatar is not None and self.planning_enabled and self.avatar.confident
                and self.current_grid is not None and bool(self.avatar.avatar_cells(self.current_grid)))

    def _known_vectors(self) -> dict[int, tuple[int, int]]:
        if self.avatar is None:
            return {}
        return {k: v for k in MOVE_KEYS if (v := self.avatar.vector(k)) is not None}

    def _prediction(self, key: int) -> tuple[str, frozenset] | None:
        if not self._planner_ready():
            return None
        vec = self.avatar.vector(key)  # type: ignore[union-attr]
        if vec is None:
            return None
        cells = self.avatar.avatar_cells(self.current_grid)  # type: ignore[union-attr]
        return predict_move(self.current_grid, cells, vec, self.passability)  # type: ignore[arg-type]

    def _on_game_over(self) -> None:
        self.diagnostics["game_overs"] += 1
        died_at = self.attempt_actions + 1  # the pending action counts
        expired = self.budget_aware and self._bar_drained()
        if self.pending is not None:
            src, action = self.pending
            if expired:
                self.diagnostics["budget_deaths"] += 1
            else:
                self.graph.record(src, action, None, changed=False, game_over=True, level_up=False)
                self._record_effect(src, action, changed=False, game_over=True)
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

    def _record_effect(self, src: str, action: ActionKey, changed: bool, game_over: bool) -> None:
        if self.prior is not None:
            self.prior.record(self.graph.action_class(src, action), changed, game_over)

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
        """Diagnostic only: the most common death cadence. A deterministic policy dies at the
        same step count for non-budget reasons too, so this never drives decisions."""
        if self.budget is not None:
            return
        length, count = self.death_lengths.most_common(1)[0]
        if count >= 2:
            self.budget = length
            self.diagnostics["budget"] = length

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
            if edge is not None and getattr(self, "_live_now", None):
                self.diagnostics["repeats"] += 1
            self.pending = (key, action)
        self.expected = self._prediction(action[0]) if action[0] in MOVE_KEYS else None
        self.trace.append(action)
        return ActionChoice(action[0], action[1], action[2], reason)

    def _pick(self, key: str | None, observation: Observation) -> tuple[ActionKey, str]:
        if key is None or key not in self.graph:
            return self._random_legal(observation), "graph: state not stored"
        live = self._live_untested(key, count=True)
        self._live_now = live
        if live:
            self.plan = []
            return self._best(key, live), f"graph: untested ({len(live)} live here)"
        if self.plan and self.plan[0][0] == key:
            _, action = self.plan.pop(0)
            self.diagnostics["plan_steps"] += 1
            return action, f"graph: plan step ({len(self.plan)} left)"
        move = self._move_toward_unknown()
        if move is not None:
            return move
        self.plan = self._plan_from(key, self._has_live_untested)
        if self.plan:
            self.diagnostics["plans"] += 1
            _, action = self.plan.pop(0)
            self.diagnostics["plan_steps"] += 1
            return action, f"graph: new plan ({len(self.plan)} more)"
        deferred = self.graph.untested(key)
        if deferred:
            self.diagnostics["deferred_picks"] += 1
            return self.rng.choice(deferred), f"graph: deferred class ({len(deferred)} left here)"
        self.plan = self._plan_from(key, lambda k: bool(self.graph.untested(k)))
        if self.plan:
            self.diagnostics["plans"] += 1
            _, action = self.plan.pop(0)
            self.diagnostics["plan_steps"] += 1
            return action, f"graph: plan to deferred ({len(self.plan)} more)"
        self.diagnostics["exhausted"] += 1
        return self._random_legal(observation), "graph: frontier exhausted, random legal"

    def _move_toward_unknown(self) -> tuple[ActionKey, str] | None:
        """Follow or make a movement plan to the nearest position with an unpredictable key."""
        if not self._planner_ready():
            self.move_plan = []
            return None
        if not self.move_plan:
            cells = self.avatar.avatar_cells(self.current_grid)  # type: ignore[union-attr]
            path = plan_moves(self.current_grid, cells, self._known_vectors(), self.passability, goal=None)  # type: ignore[arg-type]
            if not path:
                return None
            self.move_plan = list(path)
        key = self.move_plan.pop(0)
        self.diagnostics["planned_moves"] += 1
        return (key, None, None), f"planner: toward unknown terrain ({len(self.move_plan)} left)"

    def _live_untested(self, key: str, count: bool = False) -> list[ActionKey]:
        untested = self.graph.untested(key)
        if self.prior is not None:
            untested = [a for a in untested if not self.prior.deferred(self.graph.action_class(key, a))]
        if self._planner_ready():
            # movement is the planner's job: predictable moves here are not worth testing, and
            # moves at other states are never a graph frontier (unknown terrain is reached by
            # the movement planner instead)
            kept = []
            for a in untested:
                if a[0] in MOVE_KEYS:
                    if key != self.current_key or self._prediction(a[0]) is not None:
                        if count:
                            self.diagnostics["retests_avoided"] += 1
                        continue
                kept.append(a)
            untested = kept
        return untested

    def _has_live_untested(self, key: str) -> bool:
        return bool(self._live_untested(key))

    def _best(self, key: str, actions: list[ActionKey]) -> ActionKey:
        """Simple actions before clicks; within the tier, the most promising class (ties random)."""
        simple = [a for a in actions if a[0] != COMPLEX_ACTION_ID]
        tier = simple or actions
        if self.prior is None:
            return self.rng.choice(tier)
        scored = [(self.prior.score(self.graph.action_class(key, a)), self.rng.random(), a) for a in tier]
        return max(scored)[2]

    def _plan_from(self, key: str, is_frontier) -> list[tuple[str, ActionKey]]:
        path = path_to_nearest_frontier(self.graph, key, is_frontier)
        if not path:
            return []
        steps: list[tuple[str, ActionKey]] = []
        cursor = key
        for action in path:
            steps.append((cursor, action))
            cursor = self.graph.edge(cursor, action).dst_key  # type: ignore[union-attr]
        return steps

    # -- candidates ------------------------------------------------------------------------

    def _candidates(self, observation: Observation) -> tuple[list[ActionKey], dict[ActionKey, tuple]]:
        legal = observation.available_actions
        keys: list[ActionKey] = [(a, None, None) for a in legal if a != COMPLEX_ACTION_ID]
        classes: dict[ActionKey, tuple] = {k: (k[0],) for k in keys}
        if COMPLEX_ACTION_ID in legal and observation.grid is not None:
            objects = segment_objects(observation.grid)
            objects.sort(key=lambda o: (o.size, o.bbox))  # small things first: buttons
            for obj in objects[: self.max_clicks]:
                y, x = obj.anchor
                key = (COMPLEX_ACTION_ID, int(x), int(y))
                keys.append(key)
                classes[key] = click_class(obj.color, obj.size)
            if not objects:
                h, w = observation.grid.shape
                key = (COMPLEX_ACTION_ID, w // 2, h // 2)
                keys.append(key)
                classes[key] = click_class(int(observation.grid[h // 2, w // 2]), h * w)
        return keys, classes

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
        self.mismatches = 0
        if self.avatar is not None:
            self.planning_enabled = True
        self._forget_position()

    def _forget_position(self) -> None:
        self.pending = None
        self.plan = []
        self.move_plan = []
        self.expected = None
        self.current_key = None

    def _sync_counters(self) -> None:
        self.diagnostics["states"] = self.graph.size()
        self.diagnostics["edges"] = self.graph.edges
        self.diagnostics["inconsistent"] = self.graph.inconsistent
