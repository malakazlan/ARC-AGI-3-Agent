"""Offline probes on recorded traces (docs/BOTTLENECKS.md tests 1 and 2).

1. Waste rules: how many actions would a class-level no-impact rule and a dead-signature rule
   have flagged? no-impact = the action's only change lies inside the ambient region (cells that
   change on most actions of the level whatever the key). dead-signature = a click on an object
   class that never produced a non-ambient change this level, after DEAD_TRIES tries.
2. Win probe: for every level-up, which goal template holds in the frame before the winning
   action compared with the level's first frame: a class count reached zero, the avatar-like
   mover reached a rare static object, a region became uniform, two framed regions became equal.

    .venv/bin/python eval/trace_probes.py experiments/<id>/traces
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arc3.perception import AttemptSignature, countdown_mask_single_attempt, segment_objects, shape_key  # noqa: E402
from arc3.rules.resemblance import _frames, _inner_objects, normalized_shape  # noqa: E402
from eval.traces import Trace  # noqa: E402

AMBIENT_SHARE = 0.6   # a cell that changes on this share of a level's actions is ambient
DEAD_TRIES = 2


def levels_of(t: Trace) -> list[tuple[int, int]]:
    """(start, end) index ranges of each level's frames, split at level-ups."""
    out, start = [], 0
    for i in range(1, len(t.actions)):
        if t.levels[i] > t.levels[i - 1]:
            out.append((start, i))
            start = i
    out.append((start, len(t.actions)))
    return out


def live(t: Trace, i: int) -> bool:
    return t.states[i] == "NOT_FINISHED" and t.grids[i].shape == t.grids[max(i - 1, 0)].shape


def object_class(grid: np.ndarray, y: int, x: int) -> tuple | None:
    for o in segment_objects(grid):
        if (y, x) in set(o.cells):
            return (int(o.color), shape_key(o), min(o.size, 16))
    return None


def waste_rules(t: Trace) -> dict:
    stats = Counter()
    for (s, e) in levels_of(t):
        idx = [i for i in range(s + 1, e) if live(t, i) and live(t, i - 1) and t.actions[i] != 0]
        if len(idx) < 5:
            continue
        # ambient = the level's step-budget bar as our single-attempt detector sees it, grown to
        # the whole line it belongs to on the level's first frame, plus any cell that changes on
        # most actions whatever the key
        sig = AttemptSignature()
        for k, i in enumerate(range(s, e)):
            if not live(t, i):
                break
            sig.push(t.grids[i], None if k == 0 else int(t.actions[i]))
        ambient = countdown_mask_single_attempt(sig, t.grids[0].shape) if sig.length >= 4 else np.zeros(t.grids[0].shape, bool)
        if ambient.any():
            first = t.grids[s]
            vals, cnts = np.unique(first, return_counts=True)
            bg = int(vals[int(np.argmax(cnts))])
            for o in segment_objects(first, background=bg):
                y0, x0, y1, x1 = o.bbox
                if min(y1 - y0, x1 - x0) + 1 <= 4 and any(ambient[y, x] for (y, x) in o.cells):
                    for (y, x) in o.cells:
                        ambient[y, x] = True
        change_count = np.zeros(t.grids[0].shape, dtype=np.int32)
        for i in idx:
            change_count += (t.grids[i] != t.grids[i - 1])
        ambient |= change_count >= AMBIENT_SHARE * len(idx)
        stats["actions"] += len(idx)
        stats["ambient_cells"] += int(ambient.sum())
        tries: Counter = Counter()
        responded: set = set()
        for i in idx:
            diff = t.grids[i] != t.grids[i - 1]
            outside = diff & ~ambient
            if not diff.any():
                stats["no_change"] += 1
            elif not outside.any():
                stats["no_impact"] += 1
            if t.actions[i] == 6 and t.xs[i] >= 0:
                cls = object_class(t.grids[i - 1], int(t.ys[i]), int(t.xs[i]))
                if cls is None:
                    continue
                if tries[cls] >= DEAD_TRIES and cls not in responded:
                    stats["dead_click"] += 1
                tries[cls] += 1
                if outside.any():
                    responded.add(cls)
    return dict(stats)


def win_probe(t: Trace) -> list[dict]:
    out = []
    for (s, e) in levels_of(t):
        if e >= len(t.actions) or t.levels[e] <= t.levels[e - 1]:
            continue  # no level-up at the end of this range
        first = t.grids[s]
        before = t.grids[e - 1]      # the frame before the winning action
        if first.shape != before.shape:
            continue
        counts0 = Counter((int(o.color), min(o.size, 16)) for o in segment_objects(first))
        counts1 = Counter((int(o.color), min(o.size, 16)) for o in segment_objects(before))
        gone = [k for k, v in counts0.items() if v >= 2 and counts1.get(k, 0) == 0]
        dropped = [k for k, v in counts0.items() if v >= 2 and 0 < counts1.get(k, 0) < v]
        # resemblance: two frames whose inner glyphs match (colour + scale-free shape) in `before`
        def equal_pairs(grid):
            vals, cnts = np.unique(grid, return_counts=True)
            bg = int(vals[int(np.argmax(cnts))])
            frames = _frames(grid, bg)
            pairs = set()
            for a in frames:
                for b in frames:
                    if a.bbox >= b.bbox:
                        continue
                    ia = _inner_objects(grid, a.bbox, int(a.color)); ib = _inner_objects(grid, b.bbox, int(b.color))
                    if (ia and ib and ia[0].size >= 2 and ia[0].color == ib[0].color
                            and normalized_shape(frozenset(ia[0].cells)) == normalized_shape(frozenset(ib[0].cells))):
                        pairs.add((a.bbox, b.bbox))
            return pairs

        equal_frames = len(equal_pairs(before) - equal_pairs(first))   # pairs that BECAME equal

        def uniform_rect(grid):
            vals, cnts = np.unique(grid, return_counts=True)
            bg = int(vals[int(np.argmax(cnts))])
            objs = segment_objects(grid, background=bg)
            return {o.bbox for o in objs if (o.bbox[2] - o.bbox[0] + 1) * (o.bbox[3] - o.bbox[1] + 1) == o.size and o.size >= 64}

        uniform = bool(uniform_rect(before) - uniform_rect(first))   # a big rectangle that BECAME uniform
        # movers: cells that changed on the winning action, near a rare static object
        diff = t.grids[e] != before if t.grids[e].shape == before.shape else np.zeros_like(before, dtype=bool)
        moved = int(diff.sum())
        out.append({"game": t.game_id, "level": int(t.levels[e]), "actions_in_level": e - s,
                    "count_to_zero": [list(k) for k in gone], "count_dropped": [list(k) for k in dropped],
                    "equal_frames": equal_frames, "uniform_region": uniform, "cells_changed_by_win_action": moved})
    return out


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "experiments" / "2026-09-17-traces-dev" / "traces"
    totals = Counter()
    wins: list[dict] = []
    print(f"{'game':6} {'actions':>7} {'no_chg':>6} {'no_imp':>6} {'dead':>5} {'ambient':>7}  level-ups")
    for p in sorted(folder.glob("*.npz")):
        t = Trace.load(p)
        w = waste_rules(t)
        totals.update(w)
        probe = win_probe(t)
        wins.extend(probe)
        print(f"{t.game_id:6} {w.get('actions', 0):>7} {w.get('no_change', 0):>6} {w.get('no_impact', 0):>6} {w.get('dead_click', 0):>5} {w.get('ambient_cells', 0):>7}  "
              + "; ".join(f"L{x['level']}:{x['actions_in_level']}a zero={len(x['count_to_zero'])} drop={len(x['count_dropped'])} eq={x['equal_frames']} uni={int(x['uniform_region'])}" for x in probe))
    a = totals.get("actions", 1)
    print(f"ALL    {a:>7} {totals.get('no_change', 0):>6} {totals.get('no_impact', 0):>6} {totals.get('dead_click', 0):>5}   "
          f"no-change {100 * totals.get('no_change', 0) / a:.0f}%  no-impact {100 * totals.get('no_impact', 0) / a:.0f}%  dead-click {100 * totals.get('dead_click', 0) / a:.0f}%")
    tmpl = Counter()
    for x in wins:
        tmpl["count_to_zero"] += bool(x["count_to_zero"]); tmpl["count_dropped"] += bool(x["count_dropped"])
        tmpl["equal_frames"] += x["equal_frames"] > 0; tmpl["uniform"] += x["uniform_region"]
    print(f"level-ups: {len(wins)}  templates holding before the win: {dict(tmpl)}")
    (ROOT / "experiments" / "trace_probes.json").write_text(json.dumps({"waste": dict(totals), "wins": wins}, indent=2) + "\n")


if __name__ == "__main__":
    main()
