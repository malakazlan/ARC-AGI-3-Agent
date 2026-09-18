"""Census of the public games from the offline cache: what the agent can know about a game
before its first real action, plus what a few probing actions reveal. Writes
docs/GAME_CENSUS.md (table) and experiments/game_census.json.

    .venv/bin/python scripts/game_census.py
"""
from __future__ import annotations

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
from arcengine import GameAction  # noqa: E402

from arc3.agent import Orchestrator, observation_from_frame  # noqa: E402
from arc3.config import Arc3Config  # noqa: E402
from arc3.perception import segment_objects  # noqa: E402

PROBE_ACTIONS = 60


def first_frame_stats(grid: np.ndarray) -> dict:
    vals, counts = np.unique(grid, return_counts=True)
    bg = int(vals[int(np.argmax(counts))])
    objs = segment_objects(grid, background=bg)
    small = [o for o in objs if o.size <= 16]
    hollow = [o for o in objs if (o.bbox[2] - o.bbox[0] + 1) * (o.bbox[3] - o.bbox[1] + 1) > o.size and o.size >= 8]
    lines = [o for o in objs if min(o.bbox[2] - o.bbox[0], o.bbox[3] - o.bbox[1]) + 1 <= 2
             and max(o.bbox[2] - o.bbox[0], o.bbox[3] - o.bbox[1]) + 1 >= 8]
    return {
        "colours": int(len(vals)),
        "background": bg,
        "background_share": round(float(counts.max()) / grid.size, 2),
        "objects": len(objs),
        "small_objects": len(small),
        "hollow_frames": len(hollow),
        "line_objects": len(lines),
        "rare_signatures": sum(1 for _, c in Counter((int(o.color), o.size) for o in small).items() if c <= 2),
    }


def probe(arc, game_id: str, actions: int) -> dict:
    """Run the default agent for a few actions and report what its world model found."""
    env = arc.make(game_id, seed=0)
    brain = Orchestrator(Arc3Config(seed=0, max_actions_per_game=actions), game_id, started_at=0.0)
    obs = observation_from_frame(env.observation_space)
    available = list(obs.available_actions)
    first = None
    frames_per_step = []
    for t in range(actions):
        if brain.is_done(obs, now=1.0):
            break
        choice = brain.choose(obs, now=1.0)
        action = GameAction.from_id(choice.action_id)
        if action.is_complex():
            action.set_data({"x": choice.x, "y": choice.y})
        raw = env.step(action, data=action.action_data.model_dump() if action.is_complex() else {})
        frames_per_step.append(len(raw.frame or []))
        obs = observation_from_frame(raw)
        if first is None and obs.grid is not None:
            first = obs.grid.copy()
            available = list(obs.available_actions)
    ex = getattr(brain.policy, "explorer", brain.policy)
    d = brain.diagnostics
    avatar = ex.avatar
    return {
        "available_actions": available,
        "win_levels": obs.win_levels,
        "first_frame": first_frame_stats(first) if first is not None else {},
        "avatar_known_at": d.get("avatar_known_at"),
        "avatar_vectors": {k: v for k, v in ((k, avatar.vector(k)) for k in (1, 2, 3, 4)) if v} if avatar and avatar.confident else {},
        "mask_cells": d.get("mask_cells", 0),
        "multi_frame_steps": sum(1 for n in frames_per_step if n > 1),
        "levels_in_probe": obs.levels_completed,
        "states": d.get("states"),
    }


def main() -> None:
    logging.disable(logging.CRITICAL)
    games = json.loads((ROOT / "eval" / "games.json").read_text())["games"]
    split = json.loads((ROOT / "eval" / "split.json").read_text())
    dev = set(split.get("dev", [])); holdout = set(split.get("holdout", []))
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ROOT / "environment_files"))
    rows = []
    for g in games:
        gid = g["game_id"]
        try:
            p = probe(arc, gid, PROBE_ACTIONS)
        except Exception as e:  # noqa: BLE001
            p = {"error": repr(e)}
        rows.append({"game_id": gid, "split": "dev" if gid in dev else ("holdout" if gid in holdout else "?"),
                     "human_baseline": g.get("baseline_actions"), **p})
        print(gid, json.dumps({k: v for k, v in p.items() if k != "first_frame"}), flush=True)
    (ROOT / "experiments" / "game_census.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = ["# Game census (offline cache, first frame + 60 probe actions of the default agent)", "",
             "| game | split | levels | human per level | actions | colours | objects | small | frames | lines | avatar at | keys | mask | anim steps |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f = r.get("first_frame", {})
        acts = ",".join(str(a) for a in r.get("available_actions", []))
        lines.append(f"| {r['game_id']} | {r['split']} | {r.get('win_levels')} | {r.get('human_baseline')} | {acts} | "
                     f"{f.get('colours')} | {f.get('objects')} | {f.get('small_objects')} | {f.get('hollow_frames')} | {f.get('line_objects')} | "
                     f"{r.get('avatar_known_at')} | {len(r.get('avatar_vectors', {}))} | {r.get('mask_cells')} | {r.get('multi_frame_steps')} |")
    (ROOT / "docs" / "GAME_CENSUS.md").write_text("\n".join(lines) + "\n")
    print("wrote docs/GAME_CENSUS.md")


if __name__ == "__main__":
    main()
