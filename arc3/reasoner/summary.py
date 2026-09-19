"""World-model summary as compact English, for the offline VLM goal-naming experiment (Track B).

Pure: takes what perception and the rule store already know and returns text. Nothing here
talks to a model or to the game.
"""
from __future__ import annotations

from typing import Any

import numpy as np

MAX_OBJECTS = 8
MAX_CHARS = 1200

TEMPLATE_MEANINGS: dict[str, str] = {
    "match_display": "make a changeable display equal a static one",
    "reach": "bring the avatar onto a target cell or object",
    "collect": "touch or gather every object of one kind",
    "count_to_zero": "drive the count of one object class to zero",
    "make_uniform": "make a region a single colour or shape",
}


def world_summary(
    grid: np.ndarray,
    *,
    objects: list,
    avatar_cells: Any,
    key_vectors: dict[int, tuple[int, int]],
    tools: dict,
    bar: dict | None,
    deaths: int,
    level: int,
    templates: list[str],
) -> str:
    """English description of the current frame and what the world model has learned so far."""
    h, w = int(grid.shape[0]), int(grid.shape[1])
    lines = [f"Level {level}. Grid {h}x{w}, {len(objects)} objects on a non-background colour."]
    lines.extend(_object_lines(objects))
    lines.append(_avatar_line(avatar_cells))
    lines.extend(_key_lines(key_vectors))
    lines.extend(_tool_lines(tools))
    lines.append(_bar_line(bar))
    lines.append(f"Deaths so far: {int(deaths)}.")
    lines.append("Known goal templates: " + "; ".join(
        f"{name} = {TEMPLATE_MEANINGS.get(name, 'unknown meaning')}" for name in templates) + ".")
    return _truncate("\n".join(line for line in lines if line), MAX_CHARS)


def _object_lines(objects: list) -> list[str]:
    if not objects:
        return ["No objects."]
    shown = objects[:MAX_OBJECTS]
    parts = [f"colour {o.color}, size {o.size}, at ({o.bbox[0]}, {o.bbox[1]})" for o in shown]
    tail = f" (+{len(objects) - len(shown)} more)" if len(objects) > len(shown) else ""
    return [f"Most salient objects (row, col of top-left): " + "; ".join(parts) + tail + "."]


def _avatar_line(avatar_cells: Any) -> str:
    cells = list(avatar_cells) if avatar_cells else []
    if not cells:
        return "Avatar: unknown."
    row = min(int(c[0]) for c in cells)
    col = min(int(c[1]) for c in cells)
    return f"Avatar: {len(cells)} cells, top-left at ({row}, {col})."


def _key_lines(key_vectors: dict[int, tuple[int, int]]) -> list[str]:
    return [f"Key {k} moves the avatar by ({int(v[0])}, {int(v[1])}) (rows, cols)."
            for k, v in sorted(key_vectors.items())]


def _tool_lines(tools: dict) -> list[str]:
    lines = []
    for signature, tool in tools.items():
        colour = signature[0] if isinstance(signature, tuple) and signature else signature
        kind = tool if isinstance(tool, str) else getattr(tool, "kind", str(tool))
        lines.append(f"Touching colour {colour} does {kind}.")
    return lines


def _bar_line(bar: dict | None) -> str:
    if not bar:
        return ""
    return (f"Energy bar: capacity {bar.get('capacity', '?')}, remaining {bar.get('remaining', '?')}, "
            f"rate {bar.get('rate', '?')} per action.")


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."
