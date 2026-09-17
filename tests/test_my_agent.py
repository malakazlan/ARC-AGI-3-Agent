"""agent/my_agent.py adapts the framework Agent to arc3. Needs the vendored framework only."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ARC-AGI-3-Agents"

if not VENDOR.exists():
    pytest.skip("vendored framework missing; run `make setup`", allow_module_level=True)
sys.path.insert(0, str(VENDOR))

from arcengine import FrameData, GameAction, GameState  # noqa: E402


class FakeEnv:
    """Minimal stand-in for EnvironmentWrapper: never called in these tests."""

    observation_space = None

    def step(self, *args, **kwargs):
        raise AssertionError("tests must not step the environment")


def load_my_agent():
    spec = importlib.util.spec_from_file_location("my_agent_under_test", ROOT / "agent" / "my_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MyAgent


def make_agent(game_id="test-game"):
    MyAgent = load_my_agent()
    return MyAgent(card_id="c", game_id=game_id, agent_name="a", ROOT_URL="http://x",
                   record=False, arc_env=FakeEnv(), tags=[])


def frame(state, actions=(1, 2, 3), levels=0, win_levels=5, with_grid=True):
    grid = [[0] * 8 for _ in range(8)] if with_grid else []
    return FrameData(game_id="g", frame=[grid] if with_grid else [], state=state,
                     levels_completed=levels, win_levels=win_levels,
                     available_actions=list(actions))


def test_first_frame_not_played_gets_reset():
    agent = make_agent()
    f = frame(GameState.NOT_PLAYED, with_grid=False)
    assert agent.choose_action([f], f) is GameAction.RESET


def test_game_over_gets_reset():
    agent = make_agent()
    f = frame(GameState.GAME_OVER, with_grid=False)
    assert agent.choose_action([f], f) is GameAction.RESET


def test_action_is_legal_and_complex_action_has_coordinates():
    agent = make_agent()
    for _ in range(30):
        f = frame(GameState.NOT_FINISHED, actions=(5, 6))
        action = agent.choose_action([f], f)
        assert action in (GameAction.ACTION5, GameAction.ACTION6)
        if action is GameAction.ACTION6:
            data = action.action_data.model_dump()
            assert 0 <= data["x"] < 8 and 0 <= data["y"] < 8


def test_done_on_win_but_not_on_game_over():
    agent = make_agent()
    assert agent.is_done([], frame(GameState.WIN, with_grid=False))
    assert not agent.is_done([], frame(GameState.GAME_OVER, with_grid=False))
    assert not agent.is_done([], frame(GameState.NOT_FINISHED))


def test_all_agents_in_a_process_share_one_deadline():
    a, b = make_agent("g1"), make_agent("g2")
    assert a.brain.started_at == b.brain.started_at
    assert a.brain.config.global_budget_s == b.brain.config.global_budget_s


def test_max_actions_is_not_the_framework_default_of_80():
    MyAgent = load_my_agent()
    assert MyAgent.MAX_ACTIONS >= 1000


def test_diagnostics_line_is_json_with_game_id():
    import json

    agent = make_agent("g9")
    f = frame(GameState.NOT_FINISHED)
    agent.choose_action([f], f)
    line = agent.diagnostics_line()
    record = json.loads(line)
    assert record["game_id"] == "g9" and record["actions"] == 1


def test_config_can_be_injected_through_the_environment(monkeypatch):
    monkeypatch.setenv("ARC3_CONFIG_JSON", '{"seed": 5, "max_actions_per_game": 7}')
    agent = make_agent("g1")
    assert agent.brain.config.seed == 5 and agent.brain.config.max_actions_per_game == 7
