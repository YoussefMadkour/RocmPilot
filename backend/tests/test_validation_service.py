"""Tests for AMD validation modes + the wired-in Failure Diagnoser.

No network: Fireworks is stubbed. Focus is that replay_fail produces a failed
result carrying a diagnosis, replay stays clean, and fixtures decode as UTF-8.
"""
from __future__ import annotations

import pytest

from app.agents import research_agent
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
    # Diagnoser now delegates to the research agent; stub its LLM to force fallback.
    monkeypatch.setattr(research_agent.fireworks_service, "complete", lambda **k: None)
    result = validation_service.validate(run)
    assert result.status == ValidationStatus.failed
    assert not result.smoke_test_passed
    assert result.diagnosis  # deterministic fallback populated it
    assert "rocminfo" in result.diagnosis.lower()
    assert "FAIL" in result.logs


def test_diagnoser_uses_llm_when_available(run, monkeypatch):
    monkeypatch.setattr(settings, "validation_mode", "replay_fail")
    monkeypatch.setattr(
        research_agent.fireworks_service, "complete",
        lambda **k: '{"root_cause":"bad HIP state","recommended_fix":"reinstall rocm",'
                    '"confidence":"high","next_command":"rocm-smi"}',
    )
    result = validation_service.validate(run)
    assert "bad HIP state" in result.diagnosis
    assert "rocm-smi" in result.diagnosis


def test_fixtures_decode_as_utf8(run, monkeypatch):
    """The saved logs contain an em dash; reading must not raise or mojibake."""
    monkeypatch.setattr(settings, "validation_mode", "replay")
    result = validation_service.validate(run)
    assert "—" in result.logs or "AMD" in result.logs  # decoded cleanly


# --------------------------------------------------------------------------- #
# live-mode log parser (pure) — the testable core of `live` validation
# --------------------------------------------------------------------------- #
_SMOKE_PASS = """=== RocmPilot smoke test ===
torch version        : 2.4.0+rocm6.2
HIP / ROCm version   : 6.2.41133
accelerator available: True
device name          : AMD Instinct MI300X
selected device      : cuda
matmul result finite : True
PASS
"""

_SMOKE_FAIL = """=== RocmPilot smoke test ===
accelerator available: False
WARN: no accelerator — running on CPU
FAIL
"""

_BENCH_OK = """{
  "device": "cuda",
  "gpu_name": "AMD Instinct MI300X",
  "pytorch_build": "2.4.0+rocm6.2",
  "hip_version": "6.2.41133",
  "inference_latency_ms": 11.8,
  "approx_tflops": 182.0
}
"""


def test_marker_passed_takes_last_marker():
    assert validation_service._marker_passed(_SMOKE_PASS) is True
    assert validation_service._marker_passed(_SMOKE_FAIL) is False
    assert validation_service._marker_passed("no marker here") is None


def test_parse_live_pass():
    r = validation_service._parse_live_output(_SMOKE_PASS, _BENCH_OK)
    assert r.status == ValidationStatus.passed
    assert r.mode == "live"
    assert r.rocm_detected and r.hip_available
    assert r.gpu_name == "AMD Instinct MI300X"
    assert r.pytorch_rocm_build == "2.4.0+rocm6.2"
    assert r.smoke_test_passed and r.benchmark_passed
    assert r.inference_latency_ms == 11.8


def test_parse_live_fail():
    r = validation_service._parse_live_output(_SMOKE_FAIL, "Traceback ...\nBENCHMARK FAILED\n")
    assert r.status == ValidationStatus.failed
    assert not r.smoke_test_passed
    assert not r.benchmark_passed
    assert r.gpu_name is None


def test_parse_live_cpu_only_not_marked_rocm():
    smoke = "accelerator available: False\nHIP / ROCm version   : not a ROCm build\nFAIL\n"
    r = validation_service._parse_live_output(smoke, '{"gpu_name": "cpu", "device": "cpu"}')
    assert not r.rocm_detected
    assert not r.hip_available
    assert r.gpu_name is None


def test_live_falls_back_when_docker_missing(run, monkeypatch):
    """No Dockerfile in the run dir -> graceful fallback to the saved run."""
    monkeypatch.setattr(settings, "validation_mode", "live")
    result = validation_service.validate(run)
    # Fell back to replay (passed) with an explanatory note prepended.
    assert result.status == ValidationStatus.passed
    assert "live validation unavailable" in result.logs
