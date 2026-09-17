"""Trajectory recording and offline analysis.

A Trace holds one run of one game: the reset frame, then the last frame after every action.
`TraceRecorder` wraps an EnvironmentWrapper so the framework agent needs no changes.
`analyze` turns a trace into the numbers the research protocol asks for before any hypothesis:
no-op rate, volatile cells, state counts raw vs masked, per-action effects, level-ups, game overs.

    .venv/bin/python eval/traces.py experiments/<id>      # table over all recorded traces
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

GAME_OVER = "GAME_OVER"
NOT_FINISHED = "NOT_FINISHED"


@dataclass
class Trace:
    game_id: str
    seed: int
    grids: np.ndarray     # (N, H, W) int8; grids[0] is the reset frame, grids[i] follows actions[i]
    actions: np.ndarray   # (N,) int16; actions[0] == 0 (the reset)
    xs: np.ndarray        # (N,) int16, -1 when not a click
    ys: np.ndarray        # (N,) int16
    levels: np.ndarray    # (N,) int16 levels_completed after the step
    states: np.ndarray    # (N,) str state name after the step
    n_frames: np.ndarray  # (N,) int16 frames in the response

    def save(self, path: Path) -> None:
        np.savez_compressed(path, game_id=self.game_id, seed=self.seed, grids=self.grids,
                            actions=self.actions, xs=self.xs, ys=self.ys, levels=self.levels,
                            states=self.states, n_frames=self.n_frames)

    @classmethod
    def load(cls, path: Path) -> "Trace":
        z = np.load(path, allow_pickle=False)
        return cls(str(z["game_id"]), int(z["seed"]), z["grids"], z["actions"], z["xs"], z["ys"],
                   z["levels"], z["states"], z["n_frames"])


class TraceRecorder:
    """Drop-in for the framework's `arc_env`: forwards step/observation_space and records."""

    def __init__(self, env: Any, game_id: str, seed: int) -> None:
        self._env = env
        self.game_id = game_id
        self.seed = seed
        self._rows: list[tuple[np.ndarray, int, int, int, int, str, int]] = []
        first = env.observation_space
        if first is not None:
            self._record(first, action_id=0, x=-1, y=-1)

    @property
    def observation_space(self) -> Any:
        return self._env.observation_space

    def step(self, action: Any, data: dict | None = None, reasoning: Any = None) -> Any:
        raw = self._env.step(action, data=data, reasoning=reasoning)
        data = data or {}
        if raw is not None:
            self._record(raw, int(action.value), int(data.get("x", -1)), int(data.get("y", -1)))
        return raw

    def _record(self, raw: Any, action_id: int, x: int, y: int) -> None:
        frames = raw.frame or []
        if frames:
            grid = np.asarray(frames[-1], dtype=np.int8)
        elif self._rows:
            grid = self._rows[-1][0]  # game over: the engine sends no frame; keep the last one
        else:
            grid = np.zeros((64, 64), dtype=np.int8)
        state = getattr(raw.state, "name", str(raw.state))
        self._rows.append((grid, action_id, x, y, int(raw.levels_completed), state, len(frames)))

    def to_trace(self) -> Trace:
        rows = self._rows
        return Trace(
            game_id=self.game_id, seed=self.seed,
            grids=np.stack([r[0] for r in rows]).astype(np.int8),
            actions=np.array([r[1] for r in rows], dtype=np.int16),
            xs=np.array([r[2] for r in rows], dtype=np.int16),
            ys=np.array([r[3] for r in rows], dtype=np.int16),
            levels=np.array([r[4] for r in rows], dtype=np.int16),
            states=np.array([r[5] for r in rows]),
            n_frames=np.array([r[6] for r in rows], dtype=np.int16),
        )


def analyze(trace: Trace, volatile_threshold: float = 0.5) -> dict:
    """Numbers about one run. Steps are indices 1..N-1 (index 0 is the reset frame)."""
    n = len(trace.actions)
    steps = list(range(1, n))
    playing = [i for i in steps if trace.states[i] == NOT_FINISHED and trace.levels[i] == trace.levels[i - 1]
               and trace.actions[i] != 0]
    changed = {i: not np.array_equal(trace.grids[i - 1], trace.grids[i]) for i in steps}
    noops = [i for i in playing if not changed[i]]

    freq = np.zeros(trace.grids.shape[1:], dtype=np.float64)
    if playing:
        for i in playing:
            freq += trace.grids[i - 1] != trace.grids[i]
        freq /= len(playing)
    volatile = freq >= volatile_threshold if playing else np.zeros_like(freq, dtype=bool)

    live = [i for i in range(n) if trace.states[i] == NOT_FINISHED]
    raw_keys = [trace.grids[i].tobytes() for i in live]
    masked = trace.grids.copy()
    masked[:, volatile] = -1
    masked_keys = [masked[i].tobytes() for i in live]

    per_action: dict[int, dict[str, int]] = {}
    for i in steps:
        a = int(trace.actions[i])
        if a == 0:
            continue
        entry = per_action.setdefault(a, {"count": 0, "changed": 0})
        entry["count"] += 1
        entry["changed"] += int(changed[i])

    changed_cells = [int((trace.grids[i - 1] != trace.grids[i]).sum()) for i in playing if changed[i]]
    return {
        "game_id": trace.game_id,
        "seed": trace.seed,
        "steps": len(steps),
        "playing_steps": len(playing),
        "noop_rate": len(noops) / len(playing) if playing else 0.0,
        "mean_changed_cells": float(np.mean(changed_cells)) if changed_cells else 0.0,
        "volatile_cells": [tuple(map(int, c)) for c in np.argwhere(volatile)],
        "unique_states_raw": len(set(raw_keys)),
        "unique_states_masked": len(set(masked_keys)),
        "revisit_rate": 1 - len(set(masked_keys)) / len(masked_keys) if masked_keys else 0.0,
        "per_action": per_action,
        "click_hit_rate": _hit_rate(per_action.get(6)),
        "level_up_steps": [i for i in steps if trace.levels[i] > trace.levels[i - 1]],
        "game_over_steps": [i for i in steps if trace.states[i] == GAME_OVER],
        "max_frames_per_response": int(trace.n_frames.max()) if n else 0,
        "resets": int((trace.actions[1:] == 0).sum()),
    }


def _hit_rate(entry: dict[str, int] | None) -> float | None:
    if not entry or not entry["count"]:
        return None
    return entry["changed"] / entry["count"]


def format_table(reports: list[dict]) -> str:
    head = (f"{'game':6} {'seed':>4} {'steps':>5} {'noop%':>6} {'cells':>6} {'volat':>5} "
            f"{'raw':>5} {'mask':>5} {'revis%':>6} {'click%':>6} {'lvups':>5} {'over':>4} {'maxfr':>5}")
    lines = [head]
    for r in reports:
        click = "-" if r["click_hit_rate"] is None else f"{100 * r['click_hit_rate']:.0f}"
        lines.append(
            f"{r['game_id']:6} {r['seed']:>4} {r['steps']:>5} {100 * r['noop_rate']:>6.0f} "
            f"{r['mean_changed_cells']:>6.0f} {len(r['volatile_cells']):>5} {r['unique_states_raw']:>5} "
            f"{r['unique_states_masked']:>5} {100 * r['revisit_rate']:>6.0f} {click:>6} "
            f"{len(r['level_up_steps']):>5} {len(r['game_over_steps']):>4} {r['max_frames_per_response']:>5}")
    return "\n".join(lines)


def load_all(folder: Path) -> list[Trace]:
    return [Trace.load(p) for p in sorted(Path(folder).glob("traces/*.npz"))]


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("experiments")
    reports = [analyze(t) for t in load_all(folder)]
    if not reports:
        raise SystemExit(f"no traces under {folder}/traces")
    print(format_table(reports))
    by_action: Counter = Counter()
    for r in reports:
        for a, e in r["per_action"].items():
            by_action[(a, "count")] += e["count"]
            by_action[(a, "changed")] += e["changed"]
    print("\nper action over all traces: " + ", ".join(
        f"A{a}: {by_action[(a, 'changed')]}/{by_action[(a, 'count')]} changed"
        for a in sorted({k[0] for k in by_action})))


if __name__ == "__main__":
    main()
