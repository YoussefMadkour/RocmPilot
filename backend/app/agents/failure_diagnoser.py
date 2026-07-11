"""Failure Diagnoser agent.

OWNER: Youssef (AI). Reads failed build/smoke-test logs and returns a root cause +
fix. Now delegates to the Research Agent so the diagnosis is GROUNDED in the
ROCm/HIP knowledge base (RAG) and optional web search, with cited sources. Wired
into the validate endpoint when validation fails. Never raises.
"""
from __future__ import annotations

from app.agents import research_agent


def diagnose(logs: str) -> str:
    """Return a Markdown diagnosis (root cause, fix, confidence, next command, sources)."""
    problem = "AMD/ROCm validation failed. Diagnose from this log:\n" + (logs or "")
    return research_agent.investigate(problem).to_markdown()
