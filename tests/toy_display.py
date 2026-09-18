"""A toy of the ls20 level structure (owner's play notes, docs/HUMAN_PLAY.md).

12x12, background 0. Avatar colour 1 (1 cell), moved by ACTION1-4 one cell; walls colour 2 block.
Panel: 4x4 frame of colour 6 at bottom-left whose 2x2 interior shows an L glyph (3 cells) in
one of four orientations and one of three colours. Target: the same frame at top-right with
the orientation and colour to reach. Rotator: a colour-7 cell; walking into it turns the
panel's L. Colour dial (`colour_dial`): a colour-10 cell; walking into it cycles the panel's
colour through (9, 3, 5). Exit: colour 4 cell; walking into it wins the level only if the
panel equals the target, otherwise it is a wall.

Variants (each mirrors something seen on the real ls20):
  exit_in_target   no separate exit; stepping onto the target frame wins when matched
  rotator_walkable the avatar moves onto the rotator when it touches it, hiding it
  deep_target      the target is a 5x5 frame the avatar walks through; the win needs its
                   centre, so the avatar is drawn inside the target for two presses
  compound_rotator the rotator is a two-colour icon (7 and 8, three cells); any cell rotates
  colour_dial      the target also differs in colour; a second dial (colour 10) is needed
  bar              a meter inside a colour-6 frame cycles one cell per action (no death)
  energy=N         N actions of energy per attempt, shown as a 5-cell bar (colour 11, row 7,
                   cols 0-4) that loses a cell every N/5 actions; an action on an empty bar
                   restarts the level in place with a flash (no GAME_OVER), like ls20. Refill
                   cells of the bar's colour at (6, 9) and (0, 5) restore it.
  consumable_refills  a refill cell vanishes once used (ls20 level 3); a restart brings it back
  levels           2: level 2 keeps the rule, moves the target and the rotator
"""
from __future__ import annotations

import numpy as np

from arc3.agent import Observation

MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
CYCLE = (9, 3, 5)
ROTATOR_COLOURS = (7, 8)
COLOUR_DIAL = 10
BAR_COLOUR = 11
REFILL_CELLS = ((6, 9), (0, 5))
BAR_CELLS = 5
# an L of three cells inside a 2x2 box, four orientations
ORIENTATIONS = (
    ((0, 0), (1, 0), (1, 1)),
    ((0, 0), (0, 1), (1, 0)),
    ((0, 0), (0, 1), (1, 1)),
    ((0, 1), (1, 0), (1, 1)),
)
START = (6, 6)


class DisplayToy:
    def __init__(self, exit_in_target: bool = False, rotator_walkable: bool = False,
                 deep_target: bool = False, compound_rotator: bool = False,
                 colour_dial: bool = False, bar: bool = False, levels: int = 1,
                 energy: int | None = None, consumable_refills: bool = False) -> None:
        self.exit_in_target = exit_in_target or deep_target
        self.rotator_walkable = rotator_walkable
        self.deep_target = deep_target
        self.compound_rotator = compound_rotator
        self.colour_dial = colour_dial
        self.bar = bar
        self.energy = energy
        self.energy_left = energy
        self.consumable_refills = consumable_refills
        self.refills_left: set[tuple[int, int]] = set(REFILL_CELLS)
        self.under_avatar = 0
        self.levels = levels
        self.levels_completed = 0
        self.state = "NOT_PLAYED"
        self.steps = 0
        self.level_steps = 0
        self.game_overs = 0
        self.silent_deaths = 0
        self.refills = 0
        self.touches = 0
        self.colour_touches = 0
        self.bar_left = 5
        self.flash = False
        self.orientation = 0
        self.colour = CYCLE[0]
        self.target_orientation = 2
        self.target_colour = 5 if colour_dial else CYCLE[0]
        self.grid = self._layout()

    # -- geometry per level ----------------------------------------------------------------

    @property
    def level(self) -> int:
        return self.levels_completed

    def _target_box(self) -> tuple[int, int, int, int]:
        if self.deep_target:
            return (0, 7, 4, 11)
        return (0, 8, 3, 11) if self.level == 0 else (0, 0, 3, 3)

    def _target_inner_origin(self) -> tuple[int, int]:
        y0, x0, y1, x1 = self._target_box()
        if self.deep_target:
            return (1, 9)
        return (y0 + 1, x0 + 1)

    def _rotator_cells(self) -> dict[tuple[int, int], int]:
        base = (2, 2) if self.level == 0 else (7, 10)
        if self.compound_rotator:
            return {base: 7, (base[0], base[1] + 1): 8, (base[0] + 1, base[1]): 8}
        return {base: 7}

    def _colour_dial_cell(self) -> tuple[int, int]:
        return (2, 6) if self.level == 0 else (9, 6)

    def _draw_glyph(self, g: np.ndarray, origin: tuple[int, int], orientation: int, colour: int) -> None:
        oy, ox = origin
        for dy, dx in ORIENTATIONS[orientation % 4]:
            g[oy + dy, ox + dx] = colour

    def _layout(self) -> np.ndarray:
        g = np.zeros((12, 12), dtype=np.int8)
        g[5, 2:10] = 2                          # a wall with gaps at the sides
        g[8:12, 0:4] = 6                        # panel (changeable)
        g[9:11, 1:3] = 0
        self._draw_glyph(g, (9, 1), self.orientation, self.colour)
        y0, x0, y1, x1 = self._target_box()
        g[y0:y1 + 1, x0:x1 + 1] = 6             # target (static)
        if self.deep_target:
            g[1:4, 8:11] = 0
        else:
            g[y0 + 1:y1, x0 + 1:x1] = 0
        self._draw_glyph(g, self._target_inner_origin(), self.target_orientation, self.target_colour)
        for cell, colour in self._rotator_cells().items():
            g[cell] = colour
        if self.colour_dial:
            g[self._colour_dial_cell()] = COLOUR_DIAL
        if not self.exit_in_target:
            g[10, 10] = 4                       # exit
        if self.bar:
            g[8:12, 5:12] = 6                   # a frame of the panel's colour around the meter
            g[9:11, 6:11] = 0
            g[10, 6:6 + self.bar_left] = 3
        if self.energy is not None:
            self.energy_left = self.energy
            self.refills_left = set(REFILL_CELLS)
            for cell in REFILL_CELLS:
                g[cell] = BAR_COLOUR
            self._draw_energy(g)
        g[START] = 1                            # avatar
        return g

    def _draw_energy(self, g: np.ndarray) -> None:
        per_cell = self.energy / BAR_CELLS
        full = int(np.ceil(self.energy_left / per_cell))
        g[7, 0:BAR_CELLS] = 0
        g[7, 0:full] = BAR_COLOUR

    def _redraw_panel(self) -> None:
        self.grid[9:11, 1:3] = 0
        self._draw_glyph(self.grid, (9, 1), self.orientation, self.colour)

    def observe(self) -> Observation:
        grid = self.grid.copy() if self.state == "NOT_FINISHED" else None
        flash, self.flash = self.flash, False
        return Observation(self.state, self.levels_completed, self.levels, grid, [1, 2, 3, 4], flash=flash)

    @property
    def matched(self) -> bool:
        return self.orientation % 4 == self.target_orientation and self.colour == self.target_colour

    def _tick_bar(self) -> None:
        if not self.bar:
            return
        self.bar_left = 5 if self.bar_left <= 1 else self.bar_left - 1
        self.grid[10, 6:11] = 0
        self.grid[10, 6:6 + self.bar_left] = 3

    def _reset_panel(self) -> None:
        self.orientation = 0
        self.colour = CYCLE[0]

    def _restart_level(self) -> Observation:
        """ls20-style silent death: the level starts over, state stays NOT_FINISHED."""
        self.silent_deaths += 1
        self.under_avatar = 0
        self._reset_panel()
        self.grid = self._layout()
        self.flash = True
        return self.observe()

    def _win(self) -> Observation:
        self.levels_completed += 1
        self.level_steps = 0
        if self.levels_completed >= self.levels:
            self.state = "WIN"
        else:
            self.under_avatar = 0
            self._reset_panel()
            self.grid = self._layout()
        return self.observe()

    def apply(self, action_id: int, x=None, y=None) -> Observation:
        self.steps += 1
        self.level_steps += 1
        if action_id == 0:
            self._reset_panel()
            self.grid = self._layout()
            self.under_avatar = 0
            self.state = "NOT_FINISHED"
            return self.observe()
        if self.state != "NOT_FINISHED" or action_id not in MOVES:
            return self.observe()
        if self.energy is not None:
            if self.energy_left <= 0:
                return self._restart_level()
            self.energy_left -= 1
            self._draw_energy(self.grid)
        dy, dx = MOVES[action_id]
        py, px = map(int, np.argwhere(self.grid == 1)[0])
        ny, nx = py + dy, px + dx
        if not (0 <= ny < 12 and 0 <= nx < 12):
            return self.observe()
        self._tick_bar()
        if self.energy is not None and ny == 7 and nx < BAR_CELLS:
            return self.observe()                # the bar row is not walkable
        cell = int(self.grid[ny, nx])
        ty0, tx0, ty1, tx1 = self._target_box()
        in_target = ty0 <= ny <= ty1 and tx0 <= nx <= tx1
        if self.energy is not None and (ny, nx) in self.refills_left:
            self.refills += 1
            self.energy_left = self.energy
            self._draw_energy(self.grid)
            if self.consumable_refills:
                self.refills_left.discard((ny, nx))
                self.grid[ny, nx] = 0
            return self.observe()
        if cell in ROTATOR_COLOURS:              # rotator: touch (and step onto it if walkable)
            self.touches += 1
            self.orientation = (self.orientation + 1) % 4
            self._redraw_panel()
            if not self.rotator_walkable:
                return self.observe()
        elif cell == COLOUR_DIAL:                # colour dial: touch, do not move
            self.colour_touches += 1
            self.colour = CYCLE[(CYCLE.index(self.colour) + 1) % 3]
            self._redraw_panel()
            return self.observe()
        elif cell == 4 or (self.exit_in_target and in_target and not self.deep_target):
            if self.matched:                     # exit (or the target frame itself)
                return self._win()
            return self.observe()
        elif self.deep_target and in_target:
            if (ny, nx) == (2, 9):
                if self.matched:
                    return self._win()
                return self.observe()
            # walking through the target's frame is allowed; it is redrawn when we leave
        elif cell != 0:                          # walls, panels, bar: blocked
            return self.observe()
        self.grid[py, px] = self.under_avatar
        self.under_avatar = cell if (cell in ROTATOR_COLOURS or (self.deep_target and in_target)) else 0
        self.grid[ny, nx] = 1
        return self.observe()
