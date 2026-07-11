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
_EMBED_URL = "https://api.fireworks.ai/inference/v1/embeddings"


def complete(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    """Return the assistant message content, or None if Fireworks is unavailable.

    `model` overrides the default so each agent can run on its best-fit model.
    """
    if not settings.fireworks_enabled:
        return None

    payload = {
        "model": model or settings.fireworks_model,
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


def embed(texts: list[str]) -> Optional[list[list[float]]]:
    """Return one embedding vector per input text, or None if unavailable.

    Used by the knowledge base (ingestion + retrieval). Returns None when there's
    no key or the API errors, so callers degrade to no-retrieval gracefully.
    """
    if not settings.fireworks_enabled or not texts:
        return None
    try:
        resp = httpx.post(
            _EMBED_URL,
            headers={
                "Authorization": f"Bearer {settings.fireworks_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.fireworks_embedding_model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        # Preserve input order (the API returns an index per item).
        return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None
