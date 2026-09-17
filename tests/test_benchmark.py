"""eval/benchmark.py writes a results file with per-game, per-seed records. Needs the engine."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = [pytest.mark.engine, pytest.mark.slow]

if not (ROOT / "vendor" / "ARC-AGI-3-Agents").exists():
    pytest.skip("vendored framework missing; run `make setup`", allow_module_level=True)


def load_benchmark():
    spec = importlib.util.spec_from_file_location("benchmark", ROOT / "eval" / "benchmark.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["benchmark"] = module
    spec.loader.exec_module(module)
    return module


def test_benchmark_writes_results_for_one_game_and_two_seeds(tmp_path):
    bench = load_benchmark()
    out = bench.run(games=["vc33"], seeds=[0, 1], max_actions=25, time_per_game_s=60,
                    experiment_id="pytest-smoke", experiments_dir=tmp_path)
    results = json.loads((tmp_path / "pytest-smoke" / "results.json").read_text())
    assert results["experiment_id"] == "pytest-smoke"
    assert {r["game_id"] for r in results["runs"]} == {"vc33"}
    assert sorted(r["seed"] for r in results["runs"]) == [0, 1]
    run = results["runs"][0]
    for key in ("levels_completed", "actions", "level_actions", "level_scores", "score",
                "wall_s", "states", "fallbacks"):
        assert key in run, key
    assert results["summary"]["games"] == 1
    assert (tmp_path / "pytest-smoke" / "config.yaml").exists()
    assert (tmp_path / "pytest-smoke" / "notes.md").exists()
    assert out == results
