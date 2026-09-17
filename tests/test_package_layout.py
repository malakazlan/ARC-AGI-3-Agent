"""Every arc3 subpackage imports without the game engine, and the disabled reasoner defers."""
from __future__ import annotations

import importlib

import numpy as np
import pytest

SUBPACKAGES = ["perception", "world_model", "explore", "goal", "plan", "memory", "reasoner"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name):
    assert importlib.import_module(f"arc3.{name}")


def test_null_reasoner_has_no_opinion():
    from arc3.agent import Observation
    from arc3.reasoner import NullReasoner

    observation = Observation("NOT_FINISHED", 0, 1, np.zeros((8, 8), dtype=np.int8), [1])
    assert NullReasoner().propose(observation, context={}) is None
