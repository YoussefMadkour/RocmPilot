"""Tests for the RAG knowledge base.

No network: Qdrant + Fireworks embeddings are stubbed. Focus is the fallback-safe
contract (no creds -> no-op) and the retrieve/format path when configured.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.knowledge.corpus import SEED_DOCS
from app.models import KnowledgeChunk
from app.services import knowledge_service


# --------------------------------------------------------------------------- #
# Fallback-safe: unconfigured KB is a silent no-op
# --------------------------------------------------------------------------- #
def test_retrieve_noop_without_qdrant(monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "")
    assert knowledge_service.retrieve("how to port a cuda kernel") == []
    assert knowledge_service.available() is False


def test_retrieve_noop_without_fireworks(monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "https://x.cloud.qdrant.io")
    monkeypatch.setattr(settings, "fireworks_api_key", "")
    assert knowledge_service.retrieve("q") == []


def test_retrieve_empty_query(monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "https://x")
    monkeypatch.setattr(settings, "fireworks_api_key", "k")
    assert knowledge_service.retrieve("") == []


# --------------------------------------------------------------------------- #
# Configured: retrieve maps Qdrant hits -> KnowledgeChunk[]
# --------------------------------------------------------------------------- #
class _Hit:
    def __init__(self, text, source, score):
        self.payload = {"text": text, "source": source}
        self.score = score


class _FakeClient:
    def search(self, **kwargs):
        return [_Hit("Use HIP_VISIBLE_DEVICES on AMD.", "ROCm env", 0.91),
                _Hit("Swap nvidia/cuda for rocm/pytorch.", "ROCm Docker", 0.82)]


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "qdrant_url", "https://x.cloud.qdrant.io")
    monkeypatch.setattr(settings, "fireworks_api_key", "k")
    monkeypatch.setattr(knowledge_service.fireworks_service, "embed", lambda texts: [[0.1] * 8])
    monkeypatch.setattr(knowledge_service, "_client", lambda: _FakeClient())


def test_retrieve_returns_chunks(monkeypatch):
    _configure(monkeypatch)
    chunks = knowledge_service.retrieve("device selection on AMD")
    assert len(chunks) == 2
    assert all(isinstance(c, KnowledgeChunk) for c in chunks)
    assert chunks[0].source == "ROCm env"
    assert chunks[0].score == pytest.approx(0.91)


def test_retrieve_falls_back_if_embed_fails(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(knowledge_service.fireworks_service, "embed", lambda texts: None)
    assert knowledge_service.retrieve("q") == []


def test_retrieve_survives_qdrant_error(monkeypatch):
    _configure(monkeypatch)

    class _Boom:
        def search(self, **kwargs):
            raise RuntimeError("qdrant down")

    monkeypatch.setattr(knowledge_service, "_client", lambda: _Boom())
    assert knowledge_service.retrieve("q") == []  # never raises


# --------------------------------------------------------------------------- #
# as_context formatting + corpus sanity
# --------------------------------------------------------------------------- #
def test_as_context_empty_for_no_chunks():
    assert knowledge_service.as_context([]) == ""


def test_as_context_includes_sources_and_respects_budget():
    chunks = [KnowledgeChunk(text="A" * 100, source="src1", score=0.9),
              KnowledgeChunk(text="B" * 100, source="src2", score=0.8)]
    ctx = knowledge_service.as_context(chunks, max_chars=120)
    assert "src1" in ctx
    assert "ROCm/HIP migration docs" in ctx
    assert "src2" not in ctx  # trimmed by the char budget


def test_seed_corpus_is_wellformed():
    assert len(SEED_DOCS) >= 12
    for d in SEED_DOCS:
        assert d["text"].strip() and d["source"].strip()
