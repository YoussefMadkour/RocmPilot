"""Shared helper for recovering a JSON object from a messy LLM reply.

OWNER: Youssef (AI). LLMs often wrap JSON in ```json fences or add prose around
it; a bare json.loads/model_validate on that fails. Recover the object instead.
"""
from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(raw: str) -> str:
    """Return the JSON substring of an LLM reply that may be fenced or prose-wrapped."""
    text = raw.strip()
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text
