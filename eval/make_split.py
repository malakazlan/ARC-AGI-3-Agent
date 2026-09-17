"""Write eval/games.json and eval/split.json from the public game roster.

games.json: every public game with its version, tags, level count and per-level human
baseline actions (as reported by the ARC API on the day it was generated).
split.json: a deterministic dev/holdout split. Seeded shuffle, ~70/30, stratified by the
game's input tag so click-only and keyboard-only games land in both halves.

Run once. Re-running with the same roster and seed reproduces the same split. If the public
roster changes, new games are appended to dev so the holdout never changes silently.

    .venv/bin/python eval/make_split.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path

import arc_agi
from arc_agi import OperationMode

ROOT = Path(__file__).resolve().parents[1]
GAMES_PATH = ROOT / "eval" / "games.json"
SPLIT_PATH = ROOT / "eval" / "split.json"
SEED = 20260917
HOLDOUT_FRACTION = 0.3


def fetch_roster() -> list[dict]:
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    roster = []
    for env in arc.get_environments():
        roster.append(
            {
                "game_id": env.game_id.split("-")[0],
                "versioned_id": env.game_id,
                "tags": sorted(env.tags or []),
                "num_levels": len(env.baseline_actions or []),
                "baseline_actions": list(env.baseline_actions or []),
            }
        )
    roster.sort(key=lambda g: g["game_id"])
    return roster


def stratified_split(roster: list[dict], seed: int, holdout_fraction: float) -> dict:
    rng = random.Random(seed)
    by_tag: dict[str, list[str]] = defaultdict(list)
    for game in roster:
        by_tag["+".join(game["tags"]) or "untagged"].append(game["game_id"])

    holdout: list[str] = []
    for tag in sorted(by_tag):
        ids = sorted(by_tag[tag])
        rng.shuffle(ids)
        n_hold = round(len(ids) * holdout_fraction)
        holdout.extend(ids[:n_hold])

    holdout_set = set(holdout)
    dev = [g["game_id"] for g in roster if g["game_id"] not in holdout_set]
    return {"dev": sorted(dev), "holdout": sorted(holdout)}


def merge_with_existing(new_split: dict, roster: list[dict]) -> dict:
    """Keep an existing holdout frozen; route any new games to dev."""
    if not SPLIT_PATH.exists():
        return new_split
    old = json.loads(SPLIT_PATH.read_text())
    known = set(old["dev"]) | set(old["holdout"])
    current = {g["game_id"] for g in roster}
    return {
        "dev": sorted((set(old["dev"]) & current) | (current - known)),
        "holdout": sorted(set(old["holdout"]) & current),
    }


def main() -> None:
    roster = fetch_roster()
    split = merge_with_existing(stratified_split(roster, SEED, HOLDOUT_FRACTION), roster)
    GAMES_PATH.write_text(
        json.dumps({"generated": date.today().isoformat(), "games": roster}, indent=2) + "\n"
    )
    SPLIT_PATH.write_text(
        json.dumps(
            {"seed": SEED, "holdout_fraction": HOLDOUT_FRACTION, "stratify_by": "tags", **split},
            indent=2,
        )
        + "\n"
    )
    print(f"{len(roster)} games -> dev {len(split['dev'])}, holdout {len(split['holdout'])}")
    print("dev:", " ".join(split["dev"]))
    print("holdout:", " ".join(split["holdout"]))


if __name__ == "__main__":
    main()
