"""Benchmark the agent on a split of public games, N seeds, and write an experiment folder.

    .venv/bin/python eval/benchmark.py --split dev --seeds 3
    .venv/bin/python eval/benchmark.py --games vc33,ls20 --seeds 1 --max-actions 300

Writes experiments/<id>/{results.json, config.yaml, notes.md}. Scores are the engine's own
per-run scorecard (RHAE against the public human baselines, 0..100 per game).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VENDOR = ROOT / "vendor" / "ARC-AGI-3-Agents"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import arc_agi  # noqa: E402
from arc_agi import OperationMode  # noqa: E402

import arc3.agent as arc3_agent  # noqa: E402
from arc3.config import Arc3Config  # noqa: E402
from eval.traces import TraceRecorder  # noqa: E402

SPLIT_PATH = ROOT / "eval" / "split.json"
EXPERIMENTS_DIR = ROOT / "experiments"


def load_my_agent_class():
    spec = importlib.util.spec_from_file_location("my_agent_bench", ROOT / "agent" / "my_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.MyAgent


def games_for_split(split: str) -> list[str]:
    return list(json.loads(SPLIT_PATH.read_text())[split])


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def run_one(arc: Any, MyAgent: Any, game_id: str, seed: int, max_actions: int,
            time_per_game_s: float, overrides: dict, traces_dir: Path | None = None) -> dict:
    config = {"seed": seed, "max_actions_per_game": max_actions, "global_budget_s": time_per_game_s}
    config.update(overrides)
    os.environ["ARC3_CONFIG_JSON"] = json.dumps(config)
    arc3_agent._PROCESS_STARTED_AT = None  # each run gets its own clock
    MyAgent.MAX_ACTIONS = max_actions + 5  # the orchestrator stops first; this is the backstop

    env = arc.make(game_id, seed=seed)
    if env is None:
        return {"game_id": game_id, "seed": seed, "error": "could not create env"}
    recorder = TraceRecorder(env, game_id, seed) if traces_dir is not None else None
    env = recorder or env
    agent = MyAgent(card_id="bench", game_id=game_id, agent_name=f"bench.{game_id}.{seed}",
                    ROOT_URL="http://localhost", record=False, arc_env=env, tags=["bench"])
    started = time.time()
    agent.main()
    wall = time.time() - started
    if recorder is not None:
        traces_dir.mkdir(parents=True, exist_ok=True)
        recorder.to_trace().save(traces_dir / f"{game_id}_s{seed}.npz")

    run = _scorecard_run(arc, game_id)
    diagnostics = agent.brain.diagnostics
    return {
        "game_id": game_id,
        "seed": seed,
        "levels_completed": run.levels_completed,
        "win_levels": len(run.level_scores or []),
        "actions": run.actions,
        "level_actions": list(run.level_actions or []),
        "level_scores": [round(s, 2) for s in (run.level_scores or [])],
        "score": round(run.score, 3),
        "state": getattr(run.state, "name", str(run.state)),
        "wall_s": round(wall, 2),
        "states": diagnostics.get("states", 0),
        "edges": diagnostics.get("edges", 0),
        "inconsistent": diagnostics.get("inconsistent", 0),
        "exhausted": diagnostics.get("exhausted", 0),
        "capped": diagnostics.get("capped", 0),
        "resets": diagnostics.get("resets", 0),
        "fallbacks": diagnostics.get("fallbacks", 0),
        "retests_avoided": diagnostics.get("retests_avoided", 0),
        "planned_moves": diagnostics.get("planned_moves", 0),
        "mismatches": diagnostics.get("mismatches", 0),
        "planner_resets": diagnostics.get("planner_resets", 0),
        "avatar_known_at": diagnostics.get("avatar_known_at"),
        "budget_deaths": diagnostics.get("budget_deaths", 0),
    }


def _scorecard_run(arc: Any, game_id: str) -> Any:
    card = arc.get_scorecard()
    for env in card.environments:
        if env.id.split("-")[0] == game_id:
            return env.runs[-1]
    raise RuntimeError(f"no scorecard entry for {game_id}")


def summarize(runs: list[dict]) -> dict:
    per_game: dict[str, dict] = {}
    for game_id in sorted({r["game_id"] for r in runs}):
        rows = [r for r in runs if r["game_id"] == game_id and "error" not in r]
        if not rows:
            per_game[game_id] = {"error": "all runs failed"}
            continue
        per_game[game_id] = {
            "levels": [r["levels_completed"] for r in rows],
            "median_levels": statistics.median(r["levels_completed"] for r in rows),
            "median_score": round(statistics.median(r["score"] for r in rows), 2),
            "mean_actions": round(statistics.mean(r["actions"] for r in rows), 1),
            "mean_wall_s": round(statistics.mean(r["wall_s"] for r in rows), 2),
            "mean_states": round(statistics.mean(r["states"] for r in rows), 1),
        }
    ok = [g for g in per_game.values() if "error" not in g]
    total_levels = sum(r["levels_completed"] for r in runs if "error" not in r)
    total_actions = sum(r["actions"] for r in runs if "error" not in r)
    return {
        "games": len(per_game),
        "seeds": len({r["seed"] for r in runs}),
        "sum_median_levels": sum(g["median_levels"] for g in ok),
        "mean_median_score": round(statistics.mean(g["median_score"] for g in ok), 2) if ok else 0.0,
        "actions_per_completed_level": round(total_actions / total_levels, 1) if total_levels else None,
        "total_wall_s": round(sum(r["wall_s"] for r in runs if "error" not in r), 1),
        "fallbacks": sum(r.get("fallbacks", 0) for r in runs),
        "per_game": per_game,
    }


def format_table(summary: dict) -> str:
    lines = [f"{'game':6} {'levels/seed':14} {'med lv':>6} {'med score':>9} {'actions':>8} {'states':>7} {'wall s':>7}"]
    for game_id, g in summary["per_game"].items():
        if "error" in g:
            lines.append(f"{game_id:6} {g['error']}")
            continue
        lines.append(f"{game_id:6} {str(g['levels']):14} {g['median_levels']:>6} {g['median_score']:>9} "
                     f"{g['mean_actions']:>8} {g['mean_states']:>7} {g['mean_wall_s']:>7}")
    lines.append(f"TOTAL  games={summary['games']} seeds={summary['seeds']} "
                 f"sum_median_levels={summary['sum_median_levels']} "
                 f"mean_median_score={summary['mean_median_score']} "
                 f"actions/level={summary['actions_per_completed_level']} "
                 f"wall={summary['total_wall_s']}s fallbacks={summary['fallbacks']}")
    return "\n".join(lines)


def write_experiment(folder: Path, results: dict, bench_args: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    config_lines = [f"{k}: {json.dumps(v)}" for k, v in {**Arc3Config().to_dict(), **bench_args}.items()]
    (folder / "config.yaml").write_text("# effective config (defaults + benchmark overrides)\n"
                                        + "\n".join(config_lines) + "\n")
    if not (folder / "notes.md").exists():
        (folder / "notes.md").write_text(
            f"# {results['experiment_id']}\n\n"
            "- What changed: TODO\n- Result vs baseline: TODO\n- Keep or drop: TODO\n\n"
            "```\n" + format_table(results["summary"]) + "\n```\n"
        )


def run(games: list[str], seeds: list[int], max_actions: int, time_per_game_s: float,
        experiment_id: str, experiments_dir: Path = EXPERIMENTS_DIR,
        overrides: dict | None = None, quiet: bool = True, traces: bool = False) -> dict:
    if quiet:
        logging.disable(logging.CRITICAL)
    overrides = overrides or {}
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    MyAgent = load_my_agent_class()
    runs: list[dict] = []
    started = time.time()
    traces_dir = Path(experiments_dir) / experiment_id / "traces" if traces else None
    for seed in seeds:
        for game_id in games:
            result = run_one(arc, MyAgent, game_id, seed, max_actions, time_per_game_s, overrides,
                             traces_dir=traces_dir)
            runs.append(result)
            print(f"  seed={seed} {game_id:6} levels={result.get('levels_completed', '?'):>2} "
                  f"score={result.get('score', 0):>6} actions={result.get('actions', 0):>5} "
                  f"states={result.get('states', 0):>5} wall={result.get('wall_s', 0):>6}s", flush=True)
    bench_args = {"bench_games": games, "bench_seeds": seeds, "bench_max_actions": max_actions,
                  "bench_time_per_game_s": time_per_game_s, "bench_overrides": overrides}
    results = {
        "experiment_id": experiment_id,
        "date": date.today().isoformat(),
        "git": git_sha(),
        "bench": bench_args,
        "config_defaults": Arc3Config().to_dict(),
        "runs": runs,
        "summary": summarize(runs),
        "total_wall_s": round(time.time() - started, 1),
    }
    write_experiment(Path(experiments_dir) / experiment_id, results, bench_args)
    print(format_table(results["summary"]))
    print(f"wrote {Path(experiments_dir) / experiment_id}")
    return results


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", default="dev", choices=["dev", "holdout"])
    p.add_argument("--games", default=None, help="comma-separated game ids (overrides --split)")
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--max-actions", type=int, default=1000)
    p.add_argument("--time-per-game", type=float, default=300.0, help="seconds")
    p.add_argument("--id", default=None, help="experiment id (default <date>-<split>-<sha>)")
    p.add_argument("--config", default="{}", help="JSON overrides for Arc3Config")
    p.add_argument("--traces", action="store_true", help="record per-step frames to <id>/traces/")
    args = p.parse_args()

    games = args.games.split(",") if args.games else games_for_split(args.split)
    tag = "custom" if args.games else args.split
    experiment_id = args.id or f"{date.today().isoformat()}-{tag}-{git_sha()}"
    run(games, list(range(args.seeds)), args.max_actions, args.time_per_game, experiment_id,
        overrides=json.loads(args.config), traces=args.traces)


if __name__ == "__main__":
    main()
