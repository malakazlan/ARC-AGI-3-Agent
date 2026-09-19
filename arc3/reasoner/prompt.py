"""Chat messages for a vision model that names a game's goal, and a tolerant answer parser."""
from __future__ import annotations

import json
import re

TEMPLATE_NAMES = ("match_display", "reach", "collect", "count_to_zero", "make_uniform")

SYSTEM_PROMPT = (
    "You are watching an unseen grid puzzle game. Nobody has told the player the rules. "
    "You see the last few frames (oldest first) and a summary of what the player has learned. "
    "Your job is to name the GOAL of the current level, not to pick actions. "
    "Be concrete: which object must end up where, or which display must match which."
)

ANSWER_FORMAT = (
    "Answer ONLY with one JSON object, no prose, of the form "
    '{"template": one of ' + ", ".join(f'"{t}"' for t in TEMPLATE_NAMES) + ' or "other", '
    '"goal": one sentence naming the goal, '
    '"progress": one sentence describing what to measure to see progress, '
    '"next": one sentence naming the next sub-goal}.'
)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def build_messages(png_b64: list[str], summary: str) -> list[dict]:
    """OpenAI chat-format messages: system task statement, then frames + summary + answer format."""
    content: list[dict] = [{"type": "text", "text": f"The last {len(png_b64)} frame(s), oldest first:"}]
    content.extend(_image_part(b64) for b64 in png_b64)
    content.append({"type": "text", "text": "What the player has learned so far:\n" + summary})
    content.append({"type": "text", "text": ANSWER_FORMAT})
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def parse_answer(text: str) -> dict | None:
    """First JSON object in the model text, or None. Tolerates code fences and leading prose."""
    if not text:
        return None
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    decoder = json.JSONDecoder()
    for chunk in candidates:
        for start in (i for i, ch in enumerate(chunk) if ch == "{"):
            try:
                value, _ = decoder.raw_decode(chunk[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _image_part(b64: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
