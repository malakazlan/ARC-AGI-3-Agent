"""Energy as a resource: silent restarts are deaths, the bar is read, refills are planned."""
from __future__ import annotations

import numpy as np

from arc3.agent import Orchestrator, observation_from_frame
from arc3.config import Arc3Config
from tests.toy_display import DisplayToy


def run(game, seed=0, steps=300, policy="rules", **cfg):
    brain = Orchestrator(Arc3Config(seed=seed, policy=policy, **cfg), game_id="display", started_at=0.0)
    obs = game.observe()
    log = []
    for _ in range(steps):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        log.append((obs, choice))
        obs = game.apply(choice.action_id, choice.x, choice.y)
    return brain, log


class _Frame:
    def __init__(self, frames, state="NOT_FINISHED"):
        self.frame = frames
        self.state = type("S", (), {"name": state})()
        self.levels_completed = 0
        self.win_levels = 3
        self.available_actions = [1, 2, 3, 4]


def test_observation_flags_a_solid_colour_flash_in_the_frame_stack():
    """ls20's death animation: five frames of one colour, then the level's start frame."""
    start = np.zeros((8, 8), dtype=np.int8); start[3, 3] = 1
    flash = np.full((8, 8), 11, dtype=np.int8)
    assert observation_from_frame(_Frame([flash] * 5 + [start])).flash is True
    assert observation_from_frame(_Frame([start])).flash is False
    moved = start.copy(); moved[3, 3] = 0; moved[3, 4] = 1
    assert observation_from_frame(_Frame([start, moved])).flash is False


def test_silent_restart_is_a_death_without_lethal_votes():
    """A flash followed by the level's start frame ends the attempt like GAME_OVER does, but
    blames nothing: the floor the avatar was walking on does not become lethal."""
    game = DisplayToy(energy=10, exit_in_target=True)
    brain, _ = run(game, steps=120, policy="graph")
    ex = brain.policy
    assert game.silent_deaths >= 1
    # the run may end on a restart the policy has not observed yet
    assert ex.diagnostics["silent_deaths"] in (game.silent_deaths, game.silent_deaths - 1)
    assert not ex.passability.lethal(0)
    assert ex.diagnostics["mask_cells"] > 0      # attempts split at the restart: bar found


def test_rule_policy_refills_before_a_walk_it_cannot_afford():
    """Rotator and target are farther than one bar; the refill cell lies between them. The
    policy learns the refill and wins without exhausting its attempts."""
    game = DisplayToy(energy=20, exit_in_target=True)
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.refills >= 1
    store = brain.policy.store
    assert any(t.kind == "refill" for t in store.tools.values())
    assert game.silent_deaths <= 3


def test_bar_mask_is_carried_into_the_next_level_when_the_bar_is_where_it_was():
    game = DisplayToy(energy=20, exit_in_target=True, levels=2)
    brain, log = run(game, steps=400)
    ex = brain.policy.explorer
    assert game.levels_completed >= 1
    first_level2 = next((i for i, (o, _) in enumerate(log) if o.levels_completed == 1), None)
    assert first_level2 is not None
    assert ex.diagnostics["mask_carried"] >= 1


def test_explorer_knows_the_bar_before_the_first_death():
    """The bar is read within the first attempt: the mask exists before any death."""
    game = DisplayToy(energy=20, exit_in_target=True)
    brain = Orchestrator(Arc3Config(seed=0, policy="graph"), game_id="display", started_at=0.0)
    obs = game.observe()
    seen_before_death = False
    for _ in range(60):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        if game.silent_deaths == 0 and brain.policy.mask is not None and brain.policy.mask.any():
            seen_before_death = True
            break
        obs = game.apply(choice.action_id, choice.x, choice.y)
    assert seen_before_death
    assert brain.policy.energy is not None and brain.policy.energy.capacity >= 5


def test_an_unknown_second_dial_is_probed_as_a_stop_of_the_route():
    """Shape dial known, colour still wrong and its dial unknown: the nearest untouched object
    is planned as a probe stop of the route (not walked to greedily), and the level is won."""
    game = DisplayToy(energy=40, exit_in_target=True, colour_dial=True)
    brain, _ = run(game, steps=250)
    assert game.levels_completed == 1
    assert brain.policy.diagnostics.get("route_probes", 0) >= 1
