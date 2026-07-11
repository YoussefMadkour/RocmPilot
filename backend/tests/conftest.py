"""Test-wide defaults.

Force OFFLINE/deterministic behavior regardless of a populated .env: tests must
not make real Fireworks/Qdrant/web calls. Individual tests opt into the "live"
path by monkeypatching these settings back on AND stubbing the network layer.
"""
from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _offline_by_default(monkeypatch):
    monkeypatch.setattr(settings, "fireworks_api_key", "", raising=False)
    monkeypatch.setattr(settings, "qdrant_url", "", raising=False)
    monkeypatch.setattr(settings, "tavily_api_key", "", raising=False)
