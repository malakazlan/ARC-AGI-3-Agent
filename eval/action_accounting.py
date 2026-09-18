"""Action accounting: where do the actions go on the levels we win?

Drives the engine with the orchestrator directly (no framework) so every choice's reason is
known, and classifies each action up to each level-up:

  learn      first time we test an action class (fewer than LEARNED tries so far): mechanic discovery
  retest     testing a class we already know, in a new state, and it did change something
  navigate   following a plan along known edges, or a RESET
  waste      no-op outcome of a retest, deferred-class pick, frontier-exhausted random pick,
             or the action that killed us (non-expiry)

Human baseline per level comes from eval/games.json.

    .venv/bin/python eval/action_accounting.py --games lp85,m0r0,r11l --seed 0 --max-actions 1000
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import arc_agi  # noqa: E402
from arc_agi import OperationMode  # noqa: E402
from arcengine import GameAction, GameState  # noqa: E402

from arc3.agent import Orchestrator, observation_from_frame  # noqa: E402
from arc3.config import Arc3Config  # noqa: E402

LEARNED = 3
CATEGORIES = ("learn", "retest", "navigate", "waste")


def classify(reason: str, tries_before: int, changed: bool, died: bool, expired: bool) -> str:
    if reason.startswith("reset"):
        return "navigate"
    if died and not expired:
        return "waste"
    if "plan" in reason:
        return "navigate"
    if "exhausted" in reason or "deferred" in reason or "not stored" in reason:
        return "waste"
    if "untested" in reason:
        if tries_before < LEARNED:
            return "learn"
        return "retest" if changed else "waste"
    return "waste"


def account(game_id: str, seed: int, max_actions: int, baselines: dict[str, list[int]]) -> list[dict]:
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ROOT / "environment_files"))
    env = arc.make(game_id, seed=seed)
    brain = Orchestrator(Arc3Config(seed=seed, max_actions_per_game=max_actions), game_id, started_at=0.0)
    explorer = brain.policy
    raw = env.observation_space
    obs = observation_from_frame(raw)
    rows: list[dict] = []
    per_level: Counter = Counter()
    level = 0
    for step in range(max_actions):
        if brain.is_done(obs, now=1.0):
            break
        prev_grid = obs.grid
        prior = getattr(explorer, "prior", None)
        choice = brain.choose(obs, now=1.0)
        cls = explorer.graph.action_class(explorer.current_key, choice.key) if explorer.current_key else (choice.action_id,)
        tries_before = prior.stats[cls].tries - 1 if prior and cls in prior.stats else 0
        # the prior was already updated for the previous action, not this one; tries_before counts earlier tries
        stats = prior.stats.get(cls) if prior else None
        tries_before = stats.tries if stats else 0
        action = GameAction.from_id(choice.action_id)
        if action.is_complex():
            action.set_data({"x": choice.x, "y": choice.y})
        raw = env.step(action, data=action.action_data.model_dump() if action.is_complex() else {})
        obs = observation_from_frame(raw)
        died = obs.state == "GAME_OVER"
        budget_deaths_before = explorer.diagnostics["budget_deaths"]
        changed = (not died) and obs.grid is not None and prev_grid is not None and not np.array_equal(prev_grid, obs.grid)
        # expiry is only known after the explorer observes the death; peek via the bar reading
        expired = died and bool(getattr(explorer, "_bar_drained", lambda: False)())
        cat = classify(choice.reason, tries_before, changed, died, expired)
        per_level[cat] += 1
        if cat == "retest":
            per_level[f"retest_A{choice.action_id}"] += 1
        if obs.levels_completed > level:
            human = baselines.get(game_id, [])
            rows.append({"game": game_id, "level": level + 1, "human": human[level] if level < len(human) else None,
                         **{c: per_level[c] for c in CATEGORIES},
                         "total": sum(v for k, v in per_level.items() if not k.startswith("retest_")),
                         "retest_by_action": {k[7:]: v for k, v in per_level.items() if k.startswith("retest_")},
                         "planner": {k: explorer.diagnostics.get(k) for k in
                                     ("retests_avoided", "planned_moves", "mismatches", "planner_resets", "avatar_known_at")}})
            per_level = Counter()
            level = obs.levels_completed
    if not rows:
        rows.append({"game": game_id, "level": 0, "human": None, **{c: per_level[c] for c in CATEGORIES},
                     "total": sum(v for k, v in per_level.items() if not k.startswith("retest_")),
                     "retest_by_action": {k[7:]: v for k, v in per_level.items() if k.startswith("retest_")},
                     "planner": {k: explorer.diagnostics.get(k) for k in
                                 ("retests_avoided", "planned_moves", "mismatches", "planner_resets", "avatar_known_at")}})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--games", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-actions", type=int, default=1000)
    args = p.parse_args()
    logging.disable(logging.CRITICAL)
    games = json.loads((ROOT / "eval" / "games.json").read_text())["games"]
    baselines = {g["game_id"]: g["baseline_actions"] for g in games}
    rows = []
    for gid in args.games.split(","):
        rows.extend(account(gid, args.seed, args.max_actions, baselines))
    print(f"{'game':6} {'lvl':>3} {'human':>5} {'total':>5} {'learn':>5} {'retest':>6} {'navig':>5} {'waste':>5}  {'learn%':>6} {'waste%':>6}")
    tot = Counter()
    for r in rows:
        t = r["total"] or 1
        print(f"{r['game']:6} {r['level']:>3} {str(r['human']):>5} {r['total']:>5} {r['learn']:>5} {r['retest']:>6} {r['navigate']:>5} {r['waste']:>5}  "
              f"{100 * r['learn'] / t:>5.0f}% {100 * r['waste'] / t:>5.0f}%   retest by action {r['retest_by_action']}  planner {r['planner']}")
        for c in CATEGORIES + ("total",):
            tot[c] += r[c]
    t = tot["total"] or 1
    print(f"{'ALL':6} {'':>3} {'':>5} {tot['total']:>5} {tot['learn']:>5} {tot['retest']:>6} {tot['navigate']:>5} {tot['waste']:>5}  "
          f"{100 * tot['learn'] / t:>5.0f}% {100 * tot['waste'] / t:>5.0f}%")
    out = ROOT / "experiments" / "action_accounting.json"
    out.write_text(json.dumps(rows, indent=2) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
