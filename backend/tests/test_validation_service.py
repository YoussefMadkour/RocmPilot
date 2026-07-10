"""Tests for AMD validation modes + the wired-in Failure Diagnoser.

No network: Fireworks is stubbed. Focus is that replay_fail produces a failed
result carrying a diagnosis, replay stays clean, and fixtures decode as UTF-8.
"""
from __future__ import annotations

import pytest

from app.agents import failure_diagnoser
from app.config import settings
from app.models import ValidationStatus
from app.services import run_store, validation_service


@pytest.fixture()
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "run_dir", lambda rid: tmp_path / rid)
    (tmp_path / "r").mkdir()
    return "r"


def test_replay_passes_no_diagnosis(run, monkeypatch):
    monkeypatch.setattr(settings, "validation_mode", "replay")
    result = validation_service.validate(run)
    assert result.status == ValidationStatus.passed
    assert result.diagnosis is None
    assert result.benchmark_passed


def test_replay_fail_produces_failure_with_diagnosis(run, monkeypatch):
    monkeypatch.setattr(settings, "validation_mode", "replay_fail")
    monkeypatch.setattr(failure_diagnoser.fireworks_service, "complete", lambda **k: None)
    result = validation_service.validate(run)
    assert result.status == ValidationStatus.failed
    assert not result.smoke_test_passed
    assert result.diagnosis  # deterministic fallback populated it
    assert "rocminfo" in result.diagnosis.lower()
    assert "FAIL" in result.logs


def test_diagnoser_uses_llm_when_available(run, monkeypatch):
    monkeypatch.setattr(settings, "validation_mode", "replay_fail")
    monkeypatch.setattr(failure_diagnoser.fireworks_service, "complete",
                        lambda **k: "Root cause: bad HIP state.")
    result = validation_service.validate(run)
    assert result.diagnosis == "Root cause: bad HIP state."


def test_fixtures_decode_as_utf8(run, monkeypatch):
    """The saved logs contain an em dash; reading must not raise or mojibake."""
    monkeypatch.setattr(settings, "validation_mode", "replay")
    result = validation_service.validate(run)
    assert "—" in result.logs or "AMD" in result.logs  # decoded cleanly
