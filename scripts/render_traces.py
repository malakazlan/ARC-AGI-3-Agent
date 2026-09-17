"""Render recorded traces to PNG contact sheets so a human (or a model) can look at the games.

    .venv/bin/python scripts/render_traces.py experiments/<id> [--out DIR] [--every N]

Per trace: the reset frame, then every N-th frame, plus the frame right before and after each
level-up and each game over. Cells are 6x6 pixels; a 1-pixel dark gutter separates frames.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.traces import Trace  # noqa: E402

# ARC-AGI display palette (index = color value 0..15).
PALETTE = np.array([
    (0, 0, 0), (0, 116, 217), (255, 65, 54), (46, 204, 64), (255, 220, 0), (170, 170, 170),
    (240, 18, 190), (255, 133, 27), (127, 219, 255), (135, 12, 37), (255, 255, 255),
    (85, 85, 85), (0, 128, 128), (128, 0, 128), (128, 128, 0), (200, 100, 50),
], dtype=np.uint8)
SCALE = 6
GUTTER = 4


def frame_image(grid: np.ndarray) -> np.ndarray:
    rgb = PALETTE[np.clip(grid, 0, 15)]
    return rgb.repeat(SCALE, axis=0).repeat(SCALE, axis=1)


def pick_indices(trace: Trace, every: int) -> list[int]:
    n = len(trace.actions)
    wanted = {0, n - 1} | set(range(0, n, every))
    for i in range(1, n):
        if trace.levels[i] > trace.levels[i - 1] or trace.states[i] == "GAME_OVER":
            wanted |= {i - 1, i}
    return sorted(i for i in wanted if 0 <= i < n)


def contact_sheet(trace: Trace, indices: list[int], columns: int = 6) -> Image.Image:
    tiles = [frame_image(trace.grids[i]) for i in indices]
    h, w = tiles[0].shape[:2]
    rows = (len(tiles) + columns - 1) // columns
    sheet = np.full((rows * (h + GUTTER), columns * (w + GUTTER), 3), 30, dtype=np.uint8)
    for k, tile in enumerate(tiles):
        r, c = divmod(k, columns)
        y, x = r * (h + GUTTER), c * (w + GUTTER)
        sheet[y:y + h, x:x + w] = tile
    return Image.fromarray(sheet)


def caption(trace: Trace, indices: list[int]) -> str:
    parts = []
    for i in indices:
        a = int(trace.actions[i])
        tag = f"t{i}:A{a}"
        if a == 6:
            tag += f"({trace.xs[i]},{trace.ys[i]})"
        tag += f" L{trace.levels[i]}"
        if trace.states[i] != "NOT_FINISHED":
            tag += f" {trace.states[i]}"
        parts.append(tag)
    return "\n".join(parts)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("experiment")
    p.add_argument("--out", default=None)
    p.add_argument("--every", type=int, default=100)
    args = p.parse_args()
    folder = Path(args.experiment)
    out = Path(args.out) if args.out else folder / "frames"
    out.mkdir(parents=True, exist_ok=True)
    for path in sorted((folder / "traces").glob("*.npz")):
        trace = Trace.load(path)
        indices = pick_indices(trace, args.every)
        contact_sheet(trace, indices).save(out / f"{path.stem}.png")
        (out / f"{path.stem}.txt").write_text(caption(trace, indices) + "\n")
        print(f"{path.stem}: {len(indices)} frames -> {out / (path.stem + '.png')}")


if __name__ == "__main__":
    main()
