"""Tests for the research agent + web search tool.

No network: Fireworks, Qdrant retrieval, and web search are all stubbed. Focus is
that research is grounded when context exists, cites sources, and degrades safely
at every layer.
"""
from __future__ import annotations

from app.agents import research_agent
from app.config import settings
from app.models import KnowledgeChunk
from app.services import web_search


_LLM_JSON = ('{"root_cause":"No HIP device visible","recommended_fix":"mount /dev/kfd",'
             '"confidence":"high","next_command":"rocminfo"}')


# --------------------------------------------------------------------------- #
# web search — optional, no-op without a key
# --------------------------------------------------------------------------- #
def test_web_search_noop_without_key(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "")
    assert web_search.search("rocm hip error") == []
    assert web_search.available() is False


# --------------------------------------------------------------------------- #
# research agent
# --------------------------------------------------------------------------- #
def test_investigate_fallback_when_no_llm(monkeypatch):
    monkeypatch.setattr(research_agent.fireworks_service, "complete", lambda **k: None)
    monkeypatch.setattr(research_agent.knowledge_service, "retrieve", lambda q, k=None: [])
    monkeypatch.setattr(research_agent.web_search, "search", lambda q, **k: [])
    r = research_agent.investigate("validation failed")
    assert r.confidence == "medium"
    assert "rocminfo" in r.next_command
    assert r.sources == []


def test_investigate_parses_llm_and_attaches_sources(monkeypatch):
    monkeypatch.setattr(research_agent.fireworks_service, "complete", lambda **k: _LLM_JSON)
    monkeypatch.setattr(research_agent.knowledge_service, "retrieve",
                        lambda q, k=None: [KnowledgeChunk(text="Mount /dev/kfd.",
                                                          source="ROCm troubleshooting", score=0.9)])
    monkeypatch.setattr(research_agent.web_search, "search",
                        lambda q, **k: [{"title": "HIP no device", "url": "https://ex.com/x",
                                         "snippet": "check groups"}])
    r = research_agent.investigate("HIP error: no device")
    assert r.root_cause == "No HIP device visible"
    assert r.next_command == "rocminfo"
    assert "ROCm troubleshooting" in r.sources
    assert "https://ex.com/x" in r.sources


def test_investigate_grounds_prompt_with_retrieved_context(monkeypatch):
    captured = {}

    def _spy(**kwargs):
        captured["user"] = kwargs.get("user", "")
        return _LLM_JSON

    monkeypatch.setattr(research_agent.fireworks_service, "complete", _spy)
    monkeypatch.setattr(research_agent.knowledge_service, "retrieve",
                        lambda q, k=None: [KnowledgeChunk(text="Use HIP_VISIBLE_DEVICES.",
                                                          source="ROCm env", score=0.8)])
    monkeypatch.setattr(research_agent.web_search, "search", lambda q, **k: [])
    research_agent.investigate("device selection")
    assert "HIP_VISIBLE_DEVICES" in captured["user"]  # retrieved doc fed to the LLM


def test_result_to_markdown_lists_sources():
    r = research_agent.ResearchResult(
        root_cause="rc", recommended_fix="fix", confidence="high",
        next_command="rocminfo", sources=["ROCm docs", "https://ex.com"])
    md = r.to_markdown()
    assert "**Root cause:** rc" in md
    assert "`rocminfo`" in md
    assert "ROCm docs" in md and "https://ex.com" in md
