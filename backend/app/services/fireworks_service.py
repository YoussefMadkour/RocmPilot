"""Thin Fireworks AI chat-completions client.

OWNER: Youssef (backend / AI). Agents call `complete()`. If no API key is set,
`complete()` returns None so agents can fall back to a deterministic response and
the demo still runs offline. Keep prompt engineering in the agents/ modules, not
here.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings

_BASE_URL = "https://api.fireworks.ai/inference/v1/chat/completions"


def complete(
    system: str,
    user: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    """Return the assistant message content, or None if Fireworks is unavailable."""
    if not settings.fireworks_enabled:
        return None

    payload = {
        "model": settings.fireworks_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        resp = httpx.post(
            _BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.fireworks_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError):
        # Never let a flaky API break the demo — fall back deterministically.
        return None
