"""Offline validation of the step-1 models on recorded traces (no agent change).

Keyboard games: replay each trace through AvatarModel (energy bar masked). Report the action
index at which the first key vector became known, the share of state-changing moves the
translation test explains, the learned key map, and how often the model's predicted avatar
cells match the observed move once it is confident.

Click games: replay clicks through ClickEffects keyed by object signature. Report the share of
clicks whose outcome a global effect predicted correctly before the click happened (an upper
bound on re-tests that could be skipped), and how many signatures ever became global.

    .venv/bin/python eval/validate_models.py experiments/<id-with-traces>
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arc3.perception import AttemptSignature, countdown_mask_from_signatures, segment_objects  # noqa: E402
from arc3.world_model import AvatarModel, ClickEffects, object_signature  # noqa: E402
from eval.traces import Trace  # noqa: E402

MOVE_KEYS = (1, 2, 3, 4)


def bar_mask(t: Trace) -> np.ndarray:
    n = len(t.actions)
    starts = [0] + [i for i in range(1, n) if t.actions[i] == 0 or t.levels[i] > t.levels[i - 1]]
    segs = [(s, (starts[k + 1] if k + 1 < len(starts) else n)) for k, s in enumerate(starts)]
    sigs = []
    for s, e in segs:
        idx = [i for i in range(s, e) if t.states[i] == "NOT_FINISHED"]
        if len(idx) >= 2:
            sig = AttemptSignature()
            for k, i in enumerate(idx):
                sig.push(t.grids[i], None if k == 0 else (int(t.actions[i]), int(t.xs[i]), int(t.ys[i])))
            sigs.append(sig)
    shape = t.grids.shape[1:]
    return countdown_mask_from_signatures(sigs[-10:], shape) if len(sigs) >= 2 else np.zeros(shape, bool)


def validate_avatar(t: Trace) -> dict | None:
    if not any(int(a) in MOVE_KEYS for a in t.actions):
        return None
    mask = bar_mask(t)
    model = AvatarModel()
    first_known = None
    checked = consistent = blocked = 0
    n = len(t.actions)
    for i in range(1, n):
        a = int(t.actions[i])
        if a not in MOVE_KEYS or t.states[i - 1] != "NOT_FINISHED" or t.states[i] != "NOT_FINISHED" or t.levels[i] != t.levels[i - 1]:
            continue
        before, after = t.grids[i - 1], t.grids[i]
        expected = model.vector(a) if model.confident else None
        known = expected is not None and bool(model.last_cells)
        outcome = model.observe(before, a, after, mask)
        if known and outcome in ("moved", "blocked"):
            checked += 1
            if outcome == "blocked":
                blocked += 1
                consistent += 1  # the avatar stayed: a passability fact, not a misprediction
            else:
                consistent += int(model.last_vector.get(a) == expected)
        if first_known is None and any(model.vector(k) is not None for k in MOVE_KEYS):
            first_known = i
    keymap = {k: model.vector(k) for k in MOVE_KEYS if model.vector(k) is not None}
    return {
        "game": t.game_id,
        "moves": model.moves_seen,
        "explained": model.moves_explained / model.moves_seen if model.moves_seen else 0.0,
        "first_known_step": first_known,
        "keymap": keymap,
        "pred_checked": checked,
        "pred_correct": consistent,
        "blocked": blocked,
    }


def validate_clicks(t: Trace) -> dict | None:
    if not (t.actions == 6).any():
        return None
    fx = ClickEffects(k=3)
    clicks = predicted = correct = 0
    n = len(t.actions)
    for i in range(1, n):
        if int(t.actions[i]) != 6 or t.states[i - 1] != "NOT_FINISHED" or t.states[i] != "NOT_FINISHED":
            continue
        before, after = t.grids[i - 1], t.grids[i]
        x, y = int(t.xs[i]), int(t.ys[i])
        if not (0 <= y < before.shape[0] and 0 <= x < before.shape[1]):
            continue
        hit = None
        for o in segment_objects(before, background=-1):
            if o.bbox[0] <= y <= o.bbox[2] and o.bbox[1] <= x <= o.bbox[3] and before[y, x] == o.color:
                hit = o
                break
        if hit is None:
            continue
        sig = object_signature(hit)
        clicks += 1
        guess = fx.predict(sig, (y, x), before)
        if guess is not None:
            predicted += 1
            correct += int(np.array_equal(guess, after))
        fx.record(sig, (y, x), before, after)
    globals_ = sum(1 for s in fx.history if fx.global_effect(s) is not None)
    return {"game": t.game_id, "clicks": clicks, "predicted": predicted, "correct": correct,
            "signatures": len(fx.history), "global": globals_}


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "experiments" / "2026-09-18-prior-traces"
    traces = [Trace.load(p) for p in sorted((folder / "traces").glob("*.npz"))]
    print("=== avatar model (keyboard games)")
    print(f"{'game':6} {'moves':>5} {'explained':>9} {'known@':>6} {'consistent':>10} {'blocked':>7}  keymap")
    for t in traces:
        r = validate_avatar(t)
        if r is None:
            continue
        ok = f"{100 * r['pred_correct'] / r['pred_checked']:.0f}% of {r['pred_checked']}" if r["pred_checked"] else "-"
        print(f"{r['game']:6} {r['moves']:>5} {100 * r['explained']:>8.0f}% {str(r['first_known_step']):>6} {ok:>10} {r['blocked']:>7}  {r['keymap']}")
    print("\n=== click effects by signature (click games)")
    print(f"{'game':6} {'clicks':>6} {'predicted':>9} {'correct':>7} {'sigs':>5} {'global':>6}")
    for t in traces:
        r = validate_clicks(t)
        if r is None:
            continue
        print(f"{r['game']:6} {r['clicks']:>6} {r['predicted']:>9} {r['correct']:>7} {r['signatures']:>5} {r['global']:>6}")


if __name__ == "__main__":
    main()
