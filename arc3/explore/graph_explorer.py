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

from arc3.perception import (AttemptSignature, countdown_mask_from_signatures, countdown_mask_single_attempt,
                             segment_objects, state_hash)
from arc3.world_model.energy import EnergyModel
from arc3.plan import path_to_nearest_frontier, plan_moves
from arc3.types import COMPLEX_ACTION_ID, ActionChoice, ActionKey, Observation
from arc3.world_model import (
    ActionPrior, AvatarModel, ClickEffects, DialModel, KeyEffects, PassabilityModel, StateGraph,
    cells_ahead, click_class, first_obstacle_colours, object_signature, predict_move, swept_cells,
)

MOVE_KEYS = (1, 2, 3, 4)
MISMATCH_RATE_LIMIT = 0.25  # disable planning for the level only when predictions are mostly wrong

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
                 max_mismatches: int = 3, use_effects: bool = True,
                 dial_cap: bool = True, breadth_first: bool = True, click_mask: bool = True,
                 click_split: bool = True, verify_first: bool = True, verify_predictions: bool = True,
                 diverse_clicks: bool = True, restart_by_frame: bool = True,
                 blame_silent_restart: bool = True) -> None:
        self.restart_by_frame = restart_by_frame
        self.blame_silent_restart = blame_silent_restart
        self.dial_cap = dial_cap
        self.breadth_first = breadth_first
        self.click_mask = click_mask
        self.verify_first = verify_first
        self.verify_predictions = verify_predictions
        self.diverse_clicks = diverse_clicks
        self.verified_sigs: set[tuple] = set()   # signatures whose click rule predicted right once
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
        self.predictions_checked = 0
        self.current_grid: np.ndarray | None = None
        self.expected: tuple[str, frozenset] | None = None  # prediction for the pending move
        self.move_plan: list[int] = []
        # effects by signature: game-level facts, survive level changes
        self.click_effects: ClickEffects | None = ClickEffects(split=click_split) if use_effects else None
        self.key_effects: KeyEffects | None = KeyEffects() if use_effects else None
        self.click_sig: dict[tuple[str, ActionKey], tuple] = {}  # (state key, click) -> object signature
        self.floor: Counter = Counter()  # colours revealed where the avatar used to stand
        self.transports: dict[Cells, Cells] = {}  # landing position -> where the game carries the avatar
        self.dials = DialModel()  # action classes that cycle a property with a period
        self._last_signatures: dict[ActionKey, tuple] = {}
        self.graph = StateGraph(max_nodes)
        self.level_index = 0
        self.current_key: str | None = None
        self.pending: tuple[str, ActionKey] | None = None
        self.plan: list[tuple[str, ActionKey]] = []  # (expected state key, action)
        self.trace: list[ActionKey] = []  # actions since the level started
        self._last_levels: int | None = None
        # per-level attempt memory
        self.mask: np.ndarray | None = None
        self.trail: set[tuple[int, int]] = set()  # every cell the avatar has occupied this level
        self.level_start: np.ndarray | None = None  # first frame of the current level
        self.carried: tuple[np.ndarray, dict, dict] | None = None  # (mask, drain values, full values)
        self.energy: EnergyModel | None = None
        self.restarted = False  # the last observation was a silent level restart
        self.lethal_moves: set[tuple[frozenset, int]] = set()  # (avatar cells, key) presses that ended the game
        self.probed_here: set[tuple[frozenset, int]] = set()   # (avatar cells, key) pressed in place to learn terrain
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
            "avatar_known_at": None, "kill_colours": 0, "effects_avoided": 0, "dial_capped": 0, "verifications": 0,
            "silent_deaths": 0, "mask_carried": 0,
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
            self.last_grid = None  # the next frame comes after a reset: never diff across a death
            self.expected = None
            return
        if observation.grid is None:
            self._forget_position()
            self.last_grid = None
            self.expected = None
            return

        self.restarted = False
        if self.level_start is None:
            self.level_start = observation.grid.copy()
            self._carry_mask(observation.grid)
        elif self._silent_restart(observation):
            self._on_restart()

        self._learn_move(observation.grid)
        self._learn_effect(observation.grid)
        if self.energy is not None and self.mask_ok(observation.grid):
            self.energy.observe(observation.grid)
        self.current_grid = observation.grid
        if self.attempt.length == 0:
            self.attempt_actions = 0
        elif self.pending is not None:
            self.attempt_actions += 1
        self.attempt.push(observation.grid, self.pending[1] if self.pending else None)
        if self.use_countdown_mask and self.mask is None and self.attempt.length >= 4:
            self._learn_mask_single()
        self.last_grid = observation.grid

        key = state_hash(observation.grid, self.mask)
        if self.pending is not None:
            src, action = self.pending
            changed = key != src
            self.graph.record(src, action, key, changed=changed, game_over=False, level_up=False)
            self._record_effect(src, action, changed=changed, game_over=False)
            if action[0] not in MOVE_KEYS:
                self.dials.note(self.graph.action_class(src, action), src, key)
            self.pending = None
        if key not in self.graph:
            if self.diagnostics["levels_seen"] == 0 or self.graph.size() == 0:
                self.diagnostics["levels_seen"] += 1
            candidates, classes = self._candidates(observation)
            if not self.graph.add_node(key, candidates, classes):
                self.diagnostics["capped"] += 1
            else:
                for action, sig in self._last_signatures.items():
                    self.click_sig[(key, action)] = sig
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
        if self.avatar.confident and self.avatar.last_cells:
            self.trail.update(self.avatar.last_cells)
            self._unmask_trail()
        vec = self.avatar.vector(key)
        if old_cells and vec is not None and self.mask_ok(before):
            kind = outcome
            if outcome == "moved":
                actual = self.avatar.last_vector.get(key)
                new_cells = self.avatar.last_cells
                if actual == vec or _partial_stroke(actual, vec):
                    for (y, x) in self._in_bounds(swept_cells(old_cells, actual), before.shape):
                        self.passability.vote(int(before[y, x]), "passes")
                    for (y, x) in old_cells - new_cells:
                        self.floor[int(grid[y, x])] += 1
                    if actual != vec:
                        kind = "partial"  # a slide stopped early contradicts nothing
                        # slid until obstructed: the cells just beyond the reached position block
                        step = (int(np.sign(vec[0])), int(np.sign(vec[1])))
                        for (y, x) in self._in_bounds(cells_ahead(new_cells, step), before.shape):
                            self.passability.vote(int(before[y, x]), "blocks")
                else:
                    kind = "other"  # moved in an unexpected direction: no votes
                    landing = frozenset((y + vec[0], x + vec[1]) for (y, x) in old_cells)
                    if new_cells and new_cells != landing:
                        # carried beyond the press: a transport from the landing position
                        self.transports[landing] = frozenset(new_cells)
                        self.diagnostics["transports"] = len(self.transports)
            elif outcome == "blocked":
                # the press stopped at the first obstacle along the sweep: blame that footprint
                for colour in first_obstacle_colours(before, old_cells, vec, self.passability):
                    self.passability.vote(colour, "blocks")
            if self.expected is not None and kind in ("moved", "blocked", "partial"):
                self.predictions_checked += 1
                if kind != "partial" and kind != self.expected[0]:
                    colours = {int(before[y, x]) for (y, x) in self._in_bounds(swept_cells(old_cells, vec), before.shape)}
                    self._on_mismatch_event(colours)
        self.expected = None

    def _learn_effect(self, grid: np.ndarray) -> None:
        """Record what a click or a non-move key did, by signature."""
        if self.pending is None or self.last_grid is None or self.last_grid.shape != grid.shape:
            return
        src, action = self.pending
        if action[0] == COMPLEX_ACTION_ID:
            sig = self.click_sig.get((src, action))
            if sig is not None and self.click_effects is not None:
                had_rule = self.click_effects.global_effect(sig) is not None
                mask = self.mask if self.click_mask else None
                if self.click_effects.record(sig, (action[2], action[1]), self.last_grid, grid, mask):
                    self._forget_predictions(sig)
                    self.verified_sigs.discard(sig)
                elif had_rule:
                    self.verified_sigs.add(sig)   # the rule predicted this outcome: trusted from now on
        elif action[0] not in MOVE_KEYS and self.key_effects is not None:
            self.key_effects.record(action[0], self._avatar_in(self.last_grid), self.last_grid, grid)

    def _forget_predictions(self, sig: tuple) -> None:
        """A signature's rule was contradicted: its predicted edges are hypotheses no more."""
        for node in self.graph.nodes.values():
            stale = [a for a, e in node.tested.items()
                     if e.predicted and self.click_sig.get((node.key, a)) == sig]
            for a in stale:
                del node.tested[a]
                self.graph.edges -= 1

    def _avatar_in(self, grid: np.ndarray) -> frozenset:
        if self.avatar is None or not self.avatar.confident:
            return frozenset()
        return self.avatar.avatar_cells(grid)

    def _effect_predictable(self, key: str, action: ActionKey) -> bool:
        """True when the action's effect is known and executing it would teach nothing: a no-op,
        or a transition into a state already in the graph."""
        predicted = self._predicted_effect_grid(key, action)
        if predicted is None:
            return False
        if np.array_equal(predicted, self.current_grid):
            return True
        return state_hash(predicted, self.mask) in self.graph

    def _learn_death(self) -> None:
        """A non-expiry death right after a key press: the colours ahead kill."""
        if self.avatar is None or self.pending is None or self.last_grid is None or not self.avatar.confident:
            return
        key = self.pending[1][0]
        vec = self.avatar.vector(key)
        cells = self.avatar.last_cells
        if key not in MOVE_KEYS or vec is None or not cells or self._bar_drained():
            return
        # one death, one vote per colour on the path (a 3x3 avatar sweeping 6 cells touches
        # 18 cells; counting each would drown the pass votes of an innocent colour)
        for colour in {int(self.last_grid[y, x]) for (y, x) in self._in_bounds(swept_cells(cells, vec), self.last_grid.shape)}:
            self.passability.vote(colour, "kills")
            self.diagnostics["kill_colours"] += 1
        self.expected = None

    def _on_mismatch(self, colour: int) -> None:
        self._on_mismatch_event({int(colour)})

    def _on_mismatch_event(self, colours: set[int]) -> None:
        """One misprediction = one event, however many cells were ahead."""
        for colour in colours:
            self.passability.contradict(colour)
        self.mismatches += 1
        self.diagnostics["mismatches"] += 1
        rate = self.mismatches / max(1, self.predictions_checked)
        if (self.mismatches >= self.max_mismatches and rate >= MISMATCH_RATE_LIMIT
                and self.planning_enabled):
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

    def _predicted_move_grid(self, key: int) -> np.ndarray | None:
        """Render the frame after a predictable move: avatar shifted, vacated cells = floor."""
        pred = self._prediction(key)
        if pred is None or self.current_grid is None:
            return None
        if pred[0] == "blocked":
            return self.current_grid
        cells = self.avatar.avatar_cells(self.current_grid)  # type: ignore[union-attr]
        out = self.current_grid.copy()
        floor = self.floor.most_common(1)[0][0] if self.floor else None
        if floor is None:
            return None
        for (y, x) in cells:
            out[y, x] = floor
        # shift by the key vector, keeping each cell's own colour
        vec = self.avatar.vector(key)  # type: ignore[union-attr]
        for (y, x) in cells:
            ny, nx = y + vec[0], x + vec[1]
            if 0 <= ny < out.shape[0] and 0 <= nx < out.shape[1]:
                out[ny, nx] = self.current_grid[y, x]
        return out

    def _predicted_effect_grid(self, key: str, action: ActionKey) -> np.ndarray | None:
        if self.current_grid is None:
            return None
        if action[0] == COMPLEX_ACTION_ID and self.click_effects is not None:
            sig = self.click_sig.get((key, action))
            if sig is None:
                return None
            pos = (action[2], action[1])
            if (self.verify_first and sig not in self.verified_sigs
                    and self.click_effects.instance_effect(sig, pos) is None):
                return None   # a rule generalised over instances is executed once before it is trusted
            return self.click_effects.predict(sig, pos, self.current_grid)
        if action[0] not in MOVE_KEYS and self.key_effects is not None:
            return self.key_effects.predict(action[0], self._avatar_in(self.current_grid), self.current_grid)
        return None

    def _record_predicted_edges(self, key: str) -> None:
        """Turn every predictable untested action at the current state into a predicted edge, so the
        graph keeps its connectivity without executing the action. Executing later overwrites it."""
        if key != self.current_key or key not in self.graph or self.current_grid is None:
            return
        for action in self.graph.untested(key):
            grid = None
            if action[0] in MOVE_KEYS:
                if self._planner_ready():
                    grid = self._predicted_move_grid(action[0])
            else:
                grid = self._predicted_effect_grid(key, action)
            if grid is None:
                continue
            if np.array_equal(grid, self.current_grid):
                self.graph.record(key, action, key, changed=False, game_over=False, level_up=False, predicted=True)
                continue
            dst = state_hash(grid, self.mask)
            if dst in self.graph:
                self.graph.record(key, action, dst, changed=True, game_over=False, level_up=False, predicted=True)

    def _prediction(self, key: int) -> tuple[str, frozenset] | None:
        if not self._planner_ready():
            return None
        vec = self.avatar.vector(key)  # type: ignore[union-attr]
        if vec is None:
            return None
        cells = self.avatar.avatar_cells(self.current_grid)  # type: ignore[union-attr]
        return predict_move(self.current_grid, cells, vec, self.passability)  # type: ignore[arg-type]

    RESTART_TOLERANCE = 16  # cells that may differ from the level's start frame (a counter)

    def _silent_restart(self, observation: Observation) -> bool:
        """The level started over without GAME_OVER: the frame is the level's start frame again
        (up to a counter), after a flash, or with the bar back to full from empty."""
        grid = observation.grid
        if self.level_start is None or grid.shape != self.level_start.shape or self.attempt_actions < 1:
            return False
        diff = grid != self.level_start
        if (self.restart_by_frame and self.mask is not None and self.mask.shape == grid.shape
                and self.attempt_actions >= 2 and self.pending is not None and self.pending[1][0] != 0
                and self.last_grid is not None and self.avatar is not None and self.avatar.confident
                and self.avatar.last_cells and not (diff & ~self.mask).any()):
            # everything but the bar is the level's first frame again and the avatar, which was
            # away, is back on its start cells without having walked there: a restart (g50t's
            # key 5). Games without an avatar are excluded: lp85's toggles recreate the first
            # frame legitimately and lost 50 actions to this rule.
            home = self.avatar.avatar_cells(self.level_start)
            prev = frozenset(self.avatar.last_cells)
            key = self.pending[1][0]
            vec = self.avatar.vector(key) if key in MOVE_KEYS else None
            if home and prev != home:
                stepped = frozenset((y + vec[0], x + vec[1]) for (y, x) in prev) if vec is not None else None
                if stepped != home:
                    return True
        if int(diff.sum()) > self.RESTART_TOLERANCE:
            return False
        if observation.flash:
            return True
        # no flash: only a bar that jumped from empty to full while the avatar is back at its
        # start cells counts (a refill taken from an empty bar elsewhere is not a restart)
        if self.avatar is not None and self.avatar.confident and self.avatar.last_cells:
            if any(diff[y, x] for (y, x) in self.avatar.last_cells if y < diff.shape[0] and x < diff.shape[1]):
                return False
        if self.energy is not None and self.last_grid is not None and self.last_grid.shape == grid.shape:
            before, after = self.energy.remaining(self.last_grid), self.energy.remaining(grid)
            return before <= self.energy.rate and after >= self.energy.capacity - 1
        return False

    def _on_restart(self) -> None:
        """Bookkeeping of a death that left no GAME_OVER: the attempt ends, nothing is blamed."""
        self.diagnostics["silent_deaths"] += 1
        died_at = self.attempt_actions + 1
        drained = self.budget_aware and self._bar_drained()
        if drained:
            self.diagnostics["budget_deaths"] += 1
        elif (self.blame_silent_restart and self.pending is not None and self.energy is not None and self.energy.capacity
              and self.last_grid is not None and self.mask_ok(self.last_grid)
              and self.energy.remaining(self.last_grid) > 2 * max(1.0, self.energy.rate)):
            # a restart with energy clearly left is this action's doing: never again from that
            # state (g50t: key 5 restarts the level; the agent walked nine steps into it 3 times)
            src, action = self.pending
            self.graph.record(src, action, None, changed=False, game_over=True, level_up=False)
            self._record_effect(src, action, changed=False, game_over=True)
            if action[0] in MOVE_KEYS and self.avatar is not None and self.avatar.confident and self.avatar.last_cells:
                self.lethal_moves.add((frozenset(self.avatar.last_cells), int(action[0])))
        self.death_lengths[died_at] += 1
        self._close_attempt()
        self._learn_budget()
        self._forget_position()
        self.last_grid = None
        self.expected = None
        self.restarted = True
        if self.energy is not None:
            self.energy.forget_last()

    def _carry_mask(self, grid: np.ndarray) -> None:
        """A new level whose bar cells look full where the old bar was keeps the old mask."""
        if self.carried is None:
            return
        mask, drain_values, full = self.carried
        self.carried = None
        if mask.shape != grid.shape or not full:
            return
        h, w = grid.shape
        agree = sum(1 for (y, x), v in full.items() if y < h and x < w and int(grid[y, x]) == v)
        if agree < 0.9 * len(full):
            return
        self.mask = mask
        self.drain_values = drain_values
        self.energy = EnergyModel(full, drain_values)
        self.diagnostics["mask_carried"] += 1
        self.diagnostics["mask_cells"] = int(mask.sum())

    def _whole_bar(self, mask: np.ndarray) -> np.ndarray:
        """Grow the detected cells to the whole object they belong to in the level's start
        frame: a refill mid-attempt shifts the drain schedule of the cells behind it, so the
        detector only ever sees the front of the bar agree across attempts, while the bar is
        plainly the one line those cells are part of. Bounded so a bar drawn in a floor colour
        cannot swallow the floor."""
        if self.level_start is None or self.level_start.shape != mask.shape:
            return mask
        detected = int(mask.sum())
        limit = max(20 * detected, 256)
        grown = mask.copy()
        vals, counts = np.unique(self.level_start, return_counts=True)
        background = int(vals[int(np.argmax(counts))])   # a bar is never drawn in the background
        for obj in segment_objects(self.level_start, background=background):
            y0, x0, y1, x1 = obj.bbox
            if obj.size > limit or min(y1 - y0, x1 - x0) + 1 > 4:
                continue   # too big, or not a line: a bar is thin
            if any(mask[y, x] for (y, x) in obj.cells):
                for (y, x) in obj.cells:
                    grown[y, x] = True
        return grown

    def _full_values(self, mask: np.ndarray) -> dict[tuple[int, int], int]:
        if self.level_start is None or self.level_start.shape != mask.shape:
            return {}
        ys, xs = np.nonzero(mask)
        return {(int(y), int(x)): int(self.level_start[y, x]) for y, x in zip(ys, xs)}

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
                if (action[0] in MOVE_KEYS and self.avatar is not None and self.avatar.confident
                        and self.avatar.last_cells):
                    self.lethal_moves.add((frozenset(self.avatar.last_cells), int(action[0])))
        self.death_lengths[died_at] += 1
        self._close_attempt()
        self._learn_budget()
        self._forget_position()

    def _bar_drained(self) -> bool:
        """True when the bar in the last frame before death could not pay for one more action."""
        if not self.drain_values or self.last_grid is None:
            return False
        grid = self.last_grid
        if self.energy is not None and self.energy.capacity and self.mask_ok(grid):
            return self.energy.remaining(grid) <= max(1, int(np.ceil(self.energy.rate)))
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
        for (y, x) in self.trail:
            if 0 <= y < shape[0] and 0 <= x < shape[1]:
                mask[y, x] = False  # the player's own trail is never an energy bar
        if self.mask is not None and self.mask.shape == mask.shape:
            mask |= self.mask   # evidence accumulates: identical replays later in the level
                                # (a policy repeating a good path) must not erase the bar
        if not mask.any():
            return
        mask = self._whole_bar(mask)
        if self.mask is None or mask.shape != self.mask.shape or not np.array_equal(mask, self.mask):
            self.mask = mask
            self.drain_values = self._drain_values(mask)
            self.energy = EnergyModel(self._full_values(mask), self.drain_values)
            self.diagnostics["mask_cells"] = int(mask.sum())
            self._rebuild_graph()

    def _learn_mask_single(self) -> None:
        """The bar as seen within the current attempt (no second attempt needed)."""
        shape = self.attempt.shape
        if shape is None:
            return
        mask = countdown_mask_single_attempt(self.attempt, shape)
        for (y, x) in self.trail:
            if 0 <= y < shape[0] and 0 <= x < shape[1]:
                mask[y, x] = False
        if not mask.any():
            return
        mask = self._whole_bar(mask)
        self.mask = mask
        self.drain_values = self._drain_values(mask)
        self.energy = EnergyModel(self._full_values(mask), self.drain_values)
        self.diagnostics["mask_cells"] = int(mask.sum())
        self.diagnostics["mask_single"] = self.diagnostics.get("mask_single", 0) + 1
        self._rebuild_graph()

    def _unmask_trail(self) -> None:
        """Mask cells the avatar turned out to walk over are not a bar: drop them."""
        if self.mask is None:
            return
        hit = [(y, x) for (y, x) in self.avatar.last_cells  # type: ignore[union-attr]
               if 0 <= y < self.mask.shape[0] and 0 <= x < self.mask.shape[1] and self.mask[y, x]]
        if not hit:
            return
        for (y, x) in hit:
            self.mask[y, x] = False
        self.drain_values = self._drain_values(self.mask) if self.mask.any() else {}
        self.diagnostics["mask_cells"] = int(self.mask.sum())
        if not self.mask.any():
            self.mask = None

    def _drain_values(self, mask: np.ndarray) -> dict[tuple[int, int], int]:
        """Per bar cell, the value it ends an attempt with (fully drained). Cells not yet seen
        draining take the value the drained cells of the same bar show."""
        values: dict[tuple[int, int], int] = {}
        for sig in list(self.attempts) + [self.attempt]:
            for cell, seq in sig.sequences.items():
                if mask[cell]:
                    values[cell] = seq[-1][1]
        if values:
            common = Counter(values.values()).most_common(1)[0][0]
            ys, xs = np.nonzero(mask)
            for y, x in zip(ys, xs):
                values.setdefault((int(y), int(x)), common)
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

    def adopt(self, action: ActionKey) -> None:
        """Another policy chose `action` at the current state: learn from it as if it were ours."""
        key = self.current_key
        if key is not None and key in self.graph:
            self.pending = (key, action)
        self.expected = self._prediction(action[0]) if action[0] in MOVE_KEYS else None
        self.plan = []
        self.move_plan = []
        self.trace.append(action)

    def _pick(self, key: str | None, observation: Observation) -> tuple[ActionKey, str]:
        if key is None or key not in self.graph:
            return self._random_legal(observation), "graph: state not stored"
        live = self._live_untested(key, count=True)
        self._live_now = live
        self._record_predicted_edges(key)
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
        verify = self._unverified_prediction(key) if self.verify_predictions else None
        if verify is not None:
            self.diagnostics["verifications"] += 1
            return verify, "graph: verify predicted edge"
        self.diagnostics["exhausted"] += 1
        node = self.graph.nodes.get(key)
        if node is not None and node.candidates:
            pool = node.candidates
            if self.prior is not None:
                pool = [a for a in pool if not self.prior.deferred(self.graph.action_class(key, a))]
            if pool:
                return self._best(key, pool), "graph: frontier exhausted, re-test"
        return self._random_legal(observation), "graph: frontier exhausted, random legal"

    def _unverified_prediction(self, key: str) -> ActionKey | None:
        """A predicted edge at this state, never executed: the cheapest check of the effect model
        (a change predicted into a known state first, then a predicted no-op). Ties random."""
        node = self.graph.nodes.get(key)
        if node is None:
            return None
        predicted = [(a, e) for a, e in node.tested.items() if e.predicted]
        if not predicted:
            return None
        return max(predicted, key=lambda ae: (ae[1].changed, self.rng.random()))[0]

    def _move_toward_unknown(self) -> tuple[ActionKey, str] | None:
        """Follow or make a movement plan to the nearest position with an unpredictable key."""
        if not self._planner_ready():
            self.move_plan = []
            return None
        if not self.move_plan:
            cells = self.avatar.avatar_cells(self.current_grid)  # type: ignore[union-attr]
            path = plan_moves(self.current_grid, cells, self._known_vectors(), self.passability, goal=None,
                              forbidden=self.lethal_moves, transports=self.transports)  # type: ignore[arg-type]
            if path is None:
                return None
            if not path:
                # already where a key's outcome is unknown: press that key now instead of
                # planning the same empty route again next turn
                for key, vec in self._known_vectors().items():
                    if (cells, key) in self.lethal_moves or (cells, key) in self.probed_here:
                        continue
                    if predict_move(self.current_grid, cells, vec, self.passability, cells) is None:
                        self.probed_here.add((cells, key))   # once per position and key
                        self.diagnostics["planned_moves"] += 1
                        return (key, None, None), "planner: probe unknown terrain here"
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
        if key == self.current_key and (self.click_effects is not None or self.key_effects is not None):
            kept = []
            for a in untested:
                if a[0] not in MOVE_KEYS and self._effect_predictable(key, a):
                    if count:
                        self.diagnostics["effects_avoided"] += 1
                    continue
                kept.append(a)
            untested = kept
        if self.dial_cap and self._planner_ready():
            # A confirmed key dial on an avatar game (rotate, recolour) is one axis of a product
            # space (position x dial state) that the effect model already predicts: pressing it in
            # every new position teaches nothing. Clicks are never capped: in click games a toggle
            # is the mechanic itself, and without a goal its states must be visited.
            kept = []
            for a in untested:
                if (a[0] not in MOVE_KEYS and a[0] != COMPLEX_ACTION_ID
                        and self.dials.confirmed(self.graph.action_class(key, a))):
                    if count:
                        self.diagnostics["dial_capped"] += 1
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
        def tries(a: ActionKey) -> int:
            stats = self.prior.stats.get(self.graph.action_class(key, a))  # type: ignore[union-attr]
            return stats.tries if stats else 0

        # breadth-first over the move keys only: pressing each direction once is what elects the
        # avatar and shows the bar draining under different keys; over clicks and other keys it
        # spent the early budget on classes the prior already ranks (cost su15 and tu93)
        scored = [(self.breadth_first and a[0] in MOVE_KEYS and tries(a) == 0,
                   self.prior.score(self.graph.action_class(key, a)), self.rng.random(), a) for a in tier]
        return max(scored)[3]

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
        self._last_signatures = {}
        if COMPLEX_ACTION_ID in legal and observation.grid is not None:
            objects = segment_objects(observation.grid)
            objects.sort(key=lambda o: (o.size, o.bbox))  # small things first: buttons
            ordered = objects
            if self.diverse_clicks and len(objects) > self.max_clicks:
                ordered = self._diverse(objects)   # only the cap may not drop a kind; the order stays
            for obj in ordered[: self.max_clicks]:
                y, x = obj.anchor
                key = (COMPLEX_ACTION_ID, int(x), int(y))
                keys.append(key)
                classes[key] = click_class(obj.color, obj.size)
                self._last_signatures[key] = object_signature(obj)
            if not objects:
                h, w = observation.grid.shape
                key = (COMPLEX_ACTION_ID, w // 2, h // 2)
                keys.append(key)
                classes[key] = click_class(int(observation.grid[h // 2, w // 2]), h * w)
        return keys, classes

    @staticmethod
    def _diverse(objects: list) -> list:
        """One instance of every signature first, then the rest, each part in the given order: a
        click cap must never drop the only object of its kind."""
        seen: set = set()
        first, rest = [], []
        for obj in objects:
            sig = object_signature(obj)
            (rest if sig in seen else first).append(obj)
            seen.add(sig)
        return first + rest

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
        if self.mask is not None and self.energy is not None:
            self.carried = (self.mask, dict(self.drain_values), dict(self.energy.full))
        self.mask = None
        self.energy = None
        self.level_start = None
        self.lethal_moves = set()
        self.probed_here = set()
        self.transports = {}
        self.trail = set()
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
        self.predictions_checked = 0
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
