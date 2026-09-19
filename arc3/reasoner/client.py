"""Minimal OpenAI-compatible chat client for a local vLLM server, plus a mock for tests.

Standard library only. Used by the offline Track B harness, never by the Kaggle agent.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_MOCK_ANSWER: dict = {
    "template": "reach",
    "goal": "Bring the avatar to the marked target.",
    "progress": "Distance from the avatar to the target.",
    "next": "Move toward the target.",
}


class VLLMClient:
    def __init__(self, base_url: str, model: str, timeout_s: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def chat(self, messages: list[dict], max_tokens: int = 300, temperature: float = 0.0) -> str:
        body = json.dumps({"model": self.model, "messages": messages, "max_tokens": max_tokens,
                           "temperature": temperature}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/v1/chat/completions", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"vLLM HTTP {exc.code} from {request.full_url}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"vLLM unreachable at {request.full_url}: {exc}") from exc
        return _assistant_text(raw)


class MockClient:
    """Same interface as VLLMClient; returns a fixed JSON answer and counts calls."""

    def __init__(self, answer: dict | None = None) -> None:
        self.answer = dict(DEFAULT_MOCK_ANSWER if answer is None else answer)
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], max_tokens: int = 300, temperature: float = 0.0) -> str:
        self.calls.append(messages)
        return json.dumps(self.answer)


def _assistant_text(raw: str) -> str:
    try:
        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"vLLM response is not a chat completion: {raw[:300]}") from exc
    if isinstance(content, list):  # some servers return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)
