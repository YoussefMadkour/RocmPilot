"""ROCm/HIP migration knowledge base (RAG) backed by Qdrant Cloud.

OWNER: Youssef (AI). Grounds the agents in authoritative ROCm/HIP/HIPIFY docs.

Fully OPTIONAL and fallback-safe: with no `QDRANT_URL` / Fireworks key, every
call is a no-op (`retrieve()` returns []), so the agents behave exactly as they
do today. It "lights up" once the creds are set and `ingest_docs.py` has run.

  ingest:   ingest.py -> chunk docs -> fireworks embeddings -> Qdrant upsert
  retrieve: embed(query) -> Qdrant search -> KnowledgeChunk[]
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.models import KnowledgeChunk
from app.services import fireworks_service


@lru_cache(maxsize=1)
def _client():
    """Lazily build a Qdrant client. Import is deferred so the dep is optional."""
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


def available() -> bool:
    return settings.knowledge_enabled


def retrieve(query: str, k: int | None = None) -> list[KnowledgeChunk]:
    """Top-k ROCm-doc chunks for a query. [] if the KB is unconfigured/unavailable."""
    if not query or not settings.knowledge_enabled:
        return []
    vectors = fireworks_service.embed([query])
    if not vectors:
        return []
    try:
        hits = _client().search(
            collection_name=settings.knowledge_collection,
            query_vector=vectors[0],
            limit=k or settings.knowledge_top_k,
            with_payload=True,
        )
    except Exception:  # noqa: BLE001 — a KB outage must never break an agent
        return []
    chunks: list[KnowledgeChunk] = []
    for h in hits:
        payload = h.payload or {}
        text = payload.get("text")
        if text:
            chunks.append(KnowledgeChunk(
                text=text, source=payload.get("source", "unknown"),
                score=float(getattr(h, "score", 0.0) or 0.0),
            ))
    return chunks


def as_context(chunks: list[KnowledgeChunk], max_chars: int = 2400) -> str:
    """Render retrieved chunks as a compact prompt block (empty string if none)."""
    if not chunks:
        return ""
    out, used = [], 0
    for i, c in enumerate(chunks, 1):
        block = f"[{i}] ({c.source})\n{c.text.strip()}"
        if used + len(block) > max_chars:
            break
        out.append(block)
        used += len(block)
    return "Relevant ROCm/HIP migration docs:\n" + "\n\n".join(out) if out else ""
