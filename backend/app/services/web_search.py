"""Optional web search for the research agent (Tavily).

OWNER: Youssef (AI). Fully optional: with no TAVILY_API_KEY, `search()` returns []
so the research agent falls back to RAG-only. Never raises.
"""
from __future__ import annotations

import httpx

from app.config import settings

_TAVILY_URL = "https://api.tavily.com/search"


def available() -> bool:
    return bool(settings.tavily_api_key)


def search(query: str, max_results: int = 4) -> list[dict]:
    """Return [{title, url, snippet}] for a query, or [] if unavailable."""
    if not query or not settings.tavily_api_key:
        return []
    try:
        resp = httpx.post(
            _TAVILY_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""),
         "snippet": (r.get("content") or "")[:500]}
        for r in results if r.get("url")
    ]
