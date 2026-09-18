"""v2 policy: prior-driven discovery, rule store, goal templates (docs/DESIGN_V2.md).

Wraps the graph explorer: the explorer keeps learning the avatar, passability, effects and the
state graph from every action, and is the last resort. On top, this policy
  - discovers: once the avatar is known, walks to the nearest rare small object and touches it,
    reading the side effects of the touch as that object's tool type;
  - hypothesises: a touched object that changes a framed display resembling a static framed
    display yields T1 match_display;
  - exploits: touches the dial until the display matches, then tries exit candidates; a failed
    hypothesis is demoted and discovery resumes.
"""
from __future__ import annotations

import random
from typing import Any

import numpy as np

from arc3.config import Arc3Config
from arc3.explore import GraphExplorer
from arc3.perception import GridObject, segment_objects, shape_key
from arc3.plan import plan_moves
from arc3.rules import Goal, RuleStore, display_pairs, extract_events, match_progress
from arc3.types import ActionChoice, ActionKey, Observation
from arc3.world_model import cells_ahead

MOVE_KEYS = (1, 2, 3, 4)
SMALL = 16          # cells; larger objects are walls, floors or panels
RARE = 2            # at most this many objects share a salient signature
TOUCH_LIMIT = 12    # touches of one dial before the hypothesis is doubted
ENTRY_LIMIT = 4     # presses into the target display before it is dismissed as the exit
Cells = frozenset[tuple[int, int]]


def _sig(o: GridObject) -> tuple:
    return (int(o.color), shape_key(o), int(o.size))


class RulePolicy:
    def __init__(self, rng: random.Random, config: Arc3Config) -> None:
        self.rng = rng
        self.explorer = GraphExplorer(
            rng=rng, max_nodes=config.max_nodes_per_level, max_clicks=config.max_click_candidates,
            use_countdown_mask=config.countdown_mask, budget_aware=config.budget_aware,
            use_action_prior=config.action_prior, use_planner=config.planner,
            max_mismatches=config.planner_max_mismatches, use_effects=config.effects,
            dial_cap=config.dial_cap, breadth_first=config.breadth_first,
        )
        self.store = RuleStore()
        self.mode = "discover"
        self.probed: set[tuple] = set()          # signatures already touched this level
        self.tried_exits: set[tuple] = set()
        self.plan: list[int] = []
        self.plan_goal: str = ""
        self.pending_touch: tuple[tuple, int, Cells] | None = None  # (signature, key, cells) just pressed
        self.tool_cells: dict[tuple, Cells] = {}  # where each touched tool was (it may be under us)
        self.pending_exit: Cells | None = None    # avatar cells before a press into the display
        self.entry_presses = 0
        self.entry_blocked = 0
        self.display_exit_tried = False
        self.touches = 0
        self.last_grid: np.ndarray | None = None
        self._last_levels: int | None = None
        self.diagnostics: dict[str, Any] = {
            "mode": "discover", "probes": 0, "actions_to_hypothesis": None, "hypothesis_correct": 0,
            "hypotheses_demoted": 0, "exploit_steps": 0, "delegated": 0, "rule_actions": 0,
        }
        self._actions = 0

    # -- learning ---------------------------------------------------------------------------

    def observe(self, observation: Observation) -> None:
        levels = observation.levels_completed
        if self._last_levels is not None and levels > self._last_levels:
            self._level_up(levels)
        self._last_levels = levels
        self.explorer.observe(observation)
        if observation.grid is not None and self.last_grid is not None and self.pending_touch is not None:
            self._read_touch(self.last_grid, observation.grid)
        self.pending_touch = None
        if self.pending_exit is not None and observation.grid is not None and self.explorer.avatar is not None:
            after = self.explorer.avatar.avatar_cells(observation.grid)
            if after == self.pending_exit:
                self.entry_blocked += 1
        self.pending_exit = None
        if observation.grid is not None:
            self.last_grid = observation.grid
        else:
            self.last_grid = None
            self.plan = []

    def _read_touch(self, before: np.ndarray, after: np.ndarray) -> None:
        signature, key, cells = self.pending_touch  # type: ignore[misc]
        self.tool_cells[signature] = cells
        mask = self.explorer.mask if (self.explorer.mask is not None and self.explorer.mask.shape == before.shape) else None
        avatar_before = self.explorer.avatar.avatar_cells(before) if self.explorer.avatar else frozenset()
        avatar_after = self.explorer.avatar.last_cells or frozenset()
        touched_cells = set(avatar_before) | set(avatar_after)
        side = [e for e in extract_events(before, after, mask) if not (set(e.cells) & touched_cells)]
        if not side:
            if signature not in self.store.tools:
                self.store.set_tool(signature, "no_op")
            return
        changed = frozenset(c for e in side for c in e.cells)
        props = {e.prop for e in side if e.kind == "prop_changed"}
        if props:
            self.store.set_tool(signature, "dial", prop=sorted(props)[0])
        else:
            self.store.set_tool(signature, "unknown", events=[e.kind for e in side])
        if self.store.goal is None:
            pairs = display_pairs(after, changed)
            if pairs:
                pair = pairs[0]
                self.store.displays.append({"changeable": pair.changeable_box, "static": pair.static_box})
                self.store.propose_goal(Goal("match_display", {"pair": pair, "tool": signature}, confidence=0.6))
                if self.diagnostics["actions_to_hypothesis"] is None:
                    self.diagnostics["actions_to_hypothesis"] = self._actions

    def _level_up(self, levels: int) -> None:
        if self.store.goal is not None:
            self.diagnostics["hypothesis_correct"] += 1
            self.store.goal.confidence = min(0.95, self.store.goal.confidence + 0.2)
        self.store.record_level_path(levels - 1, list(self.explorer.trace))
        self.store.new_level(levels)
        self.probed = set()
        self.tried_exits = set()
        self.tool_cells = {}
        self.plan = []
        self.touches = 0
        self._reset_exit()

    def _reset_exit(self) -> None:
        self.entry_presses = 0
        self.entry_blocked = 0
        self.display_exit_tried = False
        self.pending_exit = None

    # -- choosing --------------------------------------------------------------------------

    def __call__(self, observation: Observation) -> ActionChoice:
        self._actions += 1
        try:
            choice = self._decide(observation)
        except Exception:  # noqa: BLE001 - the explorer is always a valid fallback
            choice = None
        if choice is None:
            self.diagnostics["delegated"] += 1
            return self.explorer(observation)
        self.diagnostics["rule_actions"] += 1
        self.explorer.adopt(choice.key)
        return choice

    def _decide(self, observation: Observation) -> ActionChoice | None:
        grid = observation.grid
        if grid is None or not self._avatar_ready(grid):
            self.plan = []
            return None
        if self.store.goal is not None and self.store.goal.template == "match_display":
            self.mode = "exploit"
            self.diagnostics["mode"] = "exploit"
            choice = self._exploit(observation)
            if choice is not None:
                self.diagnostics["exploit_steps"] += 1
                return choice
        self.mode = "discover"
        self.diagnostics["mode"] = "discover"
        return self._discover(observation)

    # -- exploit (T1) ------------------------------------------------------------------------

    def _exploit(self, observation: Observation) -> ActionChoice | None:
        grid = observation.grid
        goal = self.store.goal
        pair, tool_sig = goal.params["pair"], goal.params["tool"]
        progress = match_progress(grid, pair)
        if progress < 1.0:
            if self.touches >= TOUCH_LIMIT:
                self._demote()
                return None
            tool = self._find_tool(grid, tool_sig)
            if tool is None:
                self._demote()
                return None
            choice = self._touch_or_walk(observation, tool, purpose="dial")
            if choice is not None and choice.reason.startswith("rules: touch"):
                self.touches += 1
            return choice
        # matched: the static display itself is the first exit candidate (ls20: walk into the
        # target box), then other rare objects, nearest first
        choice = self._enter_display(observation, pair)
        if choice is not None:
            return choice
        for cand in self._salient(grid):
            sig = _sig(cand)
            if sig == tool_sig or sig in self.tried_exits or self._in_display(cand, pair):
                continue
            choice = self._touch_or_walk(observation, cand, purpose="exit")
            if choice is not None:
                if choice.reason.startswith("rules: touch"):
                    self.tried_exits.add(sig)
                return choice
        self._demote()
        return None

    def _enter_display(self, observation: Observation, pair) -> ActionChoice | None:
        """Press into the static display until the avatar is inside it, the presses stop moving
        it, or the entry budget is spent."""
        if self.display_exit_tried:
            return None
        grid = observation.grid
        y0, x0, y1, x1 = pair.static_box
        box = frozenset((y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))
        avatar = self.explorer.avatar.avatar_cells(grid)  # type: ignore[union-attr]
        if avatar <= box or self.entry_presses >= ENTRY_LIMIT or self.entry_blocked >= 2:
            self.display_exit_tried = True
            return None
        target = GridObject(color=int(grid[y0, x0]), size=len(box), bbox=pair.static_box,
                            centroid=((y0 + y1) / 2, (x0 + x1) / 2), anchor=(y0, x0),
                            cells=tuple(sorted(box - avatar)))
        choice = self._touch_or_walk(observation, target, purpose="exit")
        if choice is None:
            self.display_exit_tried = True
            return None
        if choice.reason.startswith("rules: touch"):
            self.entry_presses += 1
            self.pending_exit = avatar
            self.pending_touch = None  # entering the display is not a tool probe
        return choice

    def _demote(self) -> None:
        self.store.demote_goal(0.3)
        self.diagnostics["hypotheses_demoted"] += 1
        self.touches = 0
        self.tried_exits = set()
        self._reset_exit()
        self.plan = []

    # -- discovery ---------------------------------------------------------------------------

    def _discover(self, observation: Observation) -> ActionChoice | None:
        grid = observation.grid
        for cand in self._salient(grid):
            if _sig(cand) in self.probed:
                continue
            choice = self._touch_or_walk(observation, cand, purpose="probe")
            if choice is not None:
                if choice.reason.startswith("rules: touch"):
                    self.probed.add(_sig(cand))
                    self.diagnostics["probes"] += 1
                return choice
        return None  # nothing salient reachable: the explorer takes over

    # -- movement helpers --------------------------------------------------------------------

    def _avatar_ready(self, grid: np.ndarray) -> bool:
        ex = self.explorer
        return (ex.avatar is not None and ex.avatar.confident and ex.planning_enabled
                and bool(ex.avatar.avatar_cells(grid)) and len(ex._known_vectors()) >= 2)

    def _touch_or_walk(self, observation: Observation, target: GridObject, purpose: str) -> ActionChoice | None:
        """Press into the target if adjacent along a known key; else take one step of a path to a
        cell from which the next press touches it. None when unreachable."""
        grid = observation.grid
        ex = self.explorer
        cells = ex.avatar.avatar_cells(grid)
        vectors = ex._known_vectors()
        target_cells = set(target.cells)
        for key, vec in vectors.items():
            if cells_ahead(cells, vec) & target_cells:
                self.plan = []
                self.pending_touch = (_sig(target), key, frozenset(target.cells))
                return ActionChoice(key, None, None, f"rules: touch {purpose} {_sig(target)[:1]} with key {key}")
        if self.plan and self.plan_goal == (purpose, target.anchor):
            key = self.plan.pop(0)
            return ActionChoice(key, None, None, f"rules: walk to {purpose} ({len(self.plan)} left)")
        path = plan_moves(grid, cells, vectors, ex.passability,
                          goal=lambda c: any(cells_ahead(c, v) & target_cells for v in vectors.values()))
        if not path:
            return None
        self.plan = list(path)
        self.plan_goal = (purpose, target.anchor)
        key = self.plan.pop(0)
        return ActionChoice(key, None, None, f"rules: walk to {purpose} ({len(self.plan)} left)")

    def _salient(self, grid: np.ndarray) -> list[GridObject]:
        """Rare, small, static objects, nearest to the avatar first."""
        ex = self.explorer
        avatar = ex.avatar.avatar_cells(grid) if ex.avatar else frozenset()
        objects = segment_objects(grid)
        counts: dict[tuple, int] = {}
        for o in objects:
            counts[_sig(o)] = counts.get(_sig(o), 0) + 1
        avatar_sig = ex.avatar.signature if ex.avatar else None
        out = []
        for o in objects:
            s = _sig(o)
            if o.size > SMALL or counts[s] > RARE or s == avatar_sig or set(o.cells) & avatar:
                continue
            if ex.passability.lethal(int(o.color)):
                continue
            y0, x0, y1, x1 = o.bbox
            if (y1 - y0 + 1) * (x1 - x0 + 1) > o.size and o.size >= 6:
                continue  # hollow: a frame or panel border, not a tool
            out.append(o)
        ay, ax = min(avatar) if avatar else (0, 0)
        # smallest first (a symbol before a bar), then nearest
        out.sort(key=lambda o: (o.size, abs(o.anchor[0] - ay) + abs(o.anchor[1] - ax)))
        return out

    def _find(self, grid: np.ndarray, signature: tuple) -> GridObject | None:
        for o in segment_objects(grid):
            if _sig(o) == signature:
                return o
        return None

    def _find_tool(self, grid: np.ndarray, signature: tuple) -> GridObject | None:
        """A tool by signature; when it is hidden under the avatar, where it was last touched."""
        found = self._find(grid, signature)
        if found is not None:
            return found
        cells = self.tool_cells.get(signature)
        if not cells:
            return None
        avatar = self.explorer.avatar.avatar_cells(grid) if self.explorer.avatar else frozenset()
        if not (cells & avatar):
            return None
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        return GridObject(color=signature[0], size=len(cells), bbox=(min(ys), min(xs), max(ys), max(xs)),
                          centroid=(sum(ys) / len(ys), sum(xs) / len(xs)), anchor=min(cells),
                          cells=tuple(sorted(cells)))

    @staticmethod
    def _in_display(o: GridObject, pair) -> bool:
        for box in (pair.changeable_box, pair.static_box):
            y0, x0, y1, x1 = box
            if y0 <= o.anchor[0] <= y1 and x0 <= o.anchor[1] <= x1:
                return True
        return False

    # -- diagnostics -------------------------------------------------------------------------

    @property
    def diagnostics_all(self) -> dict[str, Any]:
        merged = dict(self.explorer.diagnostics)
        merged.update(self.diagnostics)
        merged["store"] = self.store.to_dict()
        return merged
