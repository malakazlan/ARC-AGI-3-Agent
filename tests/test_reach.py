"""Reach and collect goal templates on the reach toy."""
from __future__ import annotations

from arc3.agent import Orchestrator
from arc3.config import Arc3Config
from tests.toy_reach import ReachToy


def run(game, seed=0, steps=200, policy="rules", **cfg):
    brain = Orchestrator(Arc3Config(seed=seed, policy=policy, **cfg), game_id="reach", started_at=0.0)
    obs = game.observe()
    log = []
    for _ in range(steps):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        log.append((obs, choice))
        obs = game.apply(choice.action_id, choice.x, choice.y)
    return brain, log


def test_rule_policy_reaches_a_hollow_target_and_wins():
    """T2: a rare hollow frame is a place to enter. Entering it wins; decoys are probed once."""
    game = ReachToy()
    brain, _ = run(game, steps=150)
    assert game.levels_completed == 1
    assert game.steps <= 80
    assert brain.policy.store.goal is not None and brain.policy.store.goal.template == "reach"


def test_rule_policy_collects_vanishing_objects_then_reaches():
    """T3/T5: dots vanish when touched (the count drops under our action), so the goal is to
    take every dot, then enter the target."""
    game = ReachToy(collect=3)
    brain, _ = run(game, steps=250)
    assert game.levels_completed == 1
    assert game.steps <= 140
    kinds = {t.kind for t in brain.policy.store.tools.values()}
    assert "consumable" in kinds


def test_reach_goal_carries_to_the_next_level():
    game = ReachToy(levels=2)
    brain, _ = run(game, steps=250)
    assert game.levels_completed == 2
    level1 = brain.policy.store.level_paths[0]
    assert game.steps - len(level1) <= 40


def test_explorer_learns_a_conveyor_and_the_policy_rides_it():
    """The target sits behind the wall; a strip at the wall's gap carries the avatar to the
    far side. After one ride the explorer knows the transport and the win path uses it."""
    game = ReachToy(decoys=False, conveyor=((6, 9), (4, 9)))
    brain, log = run(game, steps=150)
    ex = brain.policy.explorer
    assert ex.diagnostics.get("transports"), "the ride was not learned as a transport"
    assert game.levels_completed == 1
    assert ex.diagnostics["planner_resets"] == 0


def test_collect_gives_up_on_a_dot_that_never_vanishes():
    """One real dot makes colour 9 a consumable; two sticky dots share the signature and never
    go. The policy must stop pressing into them and still win through the doorway."""
    game = ReachToy(collect=1, sticky=2, decoys=False)
    brain, log = run(game, steps=250)
    assert game.levels_completed == 1
    presses = [c for _, c in log if c.reason.startswith("rules: touch collect")]
    assert len(presses) <= 8


def test_a_frame_is_entered_through_its_opening():
    """g50t: the socket opens on one side. Pressing into a closed side is not an attempt; the
    avatar walks round to the opening and enters there."""
    game = ReachToy(decoys=False, door="top")
    brain, _ = run(game, steps=200)
    assert game.levels_completed == 1
    assert game.steps <= 45
    assert not any(sig[0] == 6 for sig in brain.policy.reach_tried)   # the frame was never given up on
