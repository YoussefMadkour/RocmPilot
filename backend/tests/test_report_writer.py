"""Tests for the Report Writer agent + report-in-zip wiring.

No network: Fireworks is stubbed. Focus is a grounded, honest fallback (replay
labeled, failure diagnosis included) and that the LLM path strips a whole-doc
code fence.
"""
from __future__ import annotations

from app.agents import report_writer
from app.models import (
    Artifact, MigrationPlan, PlanAction, ScoreBreakdown, Severity, ActionType,
    ValidationResult, ValidationStatus,
)


def _plan():
    return MigrationPlan(
        summary="Mostly ready; one Docker blocker.",
        actions=[PlanAction(title="Swap base image", detail="Use rocm/pytorch.",
                            severity=Severity.high, action_type=ActionType.auto_patch)],
        manual_blockers=["kernel.cu:1 — custom CUDA kernel"],
    )


def _artifacts():
    return [Artifact(name="patch.diff", path="patch.diff", language="diff"),
            Artifact(name="Dockerfile.rocm", path="Dockerfile.rocm", language="dockerfile")]


def _validation(status=ValidationStatus.passed, mode="replay", diagnosis=None):
    return ValidationResult(status=status, mode=mode, rocm_detected=True, hip_available=True,
                            gpu_name="AMD Instinct MI300X", pytorch_rocm_build="2.4.0+rocm6.2",
                            smoke_test_passed=status == ValidationStatus.passed,
                            benchmark_passed=status == ValidationStatus.passed,
                            inference_latency_ms=12.4, logs="...", diagnosis=diagnosis)


def _score():
    return ScoreBreakdown(before=37, after_planned=72, final=86)


def test_fallback_is_grounded_markdown(monkeypatch):
    monkeypatch.setattr(report_writer.fireworks_service, "complete", lambda **k: None)
    md = report_writer.write("sample:demo", _plan(), _artifacts(), _validation(), _score())
    assert "# RocmPilot Readiness Report" in md
    assert "37/100" in md and "72/100" in md and "86/100" in md
    assert "patch.diff" in md and "Dockerfile.rocm" in md
    assert "kernel.cu:1" in md               # manual blocker surfaced
    assert "Saved AMD run (replay)" in md     # replay honestly labeled


def test_fallback_includes_diagnosis_on_failure(monkeypatch):
    monkeypatch.setattr(report_writer.fireworks_service, "complete", lambda **k: None)
    v = _validation(status=ValidationStatus.failed, mode="replay_fail",
                    diagnosis="Root cause: no HIP device.")
    md = report_writer.write("sample:demo", _plan(), _artifacts(), v, _score())
    assert "Failure diagnosis" in md
    assert "no HIP device" in md


def test_llm_path_strips_whole_doc_fence(monkeypatch):
    monkeypatch.setattr(report_writer.fireworks_service, "complete",
                        lambda **k: "```markdown\n# Report\nbody\n```")
    md = report_writer.write("s", _plan(), _artifacts(), _validation(), _score())
    assert md == "# Report\nbody"


def test_strip_doc_fence_leaves_inline_fences_alone():
    md = "# Report\n\n```bash\ndocker build .\n```\n"
    assert report_writer._strip_doc_fence(md) == md.strip()


def test_report_is_included_in_artifacts_and_zip():
    """GET /report must register readiness_report.md so artifacts.zip includes it."""
    import zipfile, io
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    rid = c.post("/api/runs", json={"use_sample": True}).json()["run_id"]
    c.post(f"/api/runs/{rid}/scan")
    c.post(f"/api/runs/{rid}/plan")
    c.post(f"/api/runs/{rid}/patch")
    c.post(f"/api/runs/{rid}/validate")
    rep = c.get(f"/api/runs/{rid}/report").json()
    assert any(a["name"] == "readiness_report.md" for a in rep["artifacts"])

    # And it's really in the zip.
    z = c.get(f"/api/runs/{rid}/artifacts.zip")
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "readiness_report.md" in names
    # Idempotent: a second GET must not duplicate the artifact.
    rep2 = c.get(f"/api/runs/{rid}/report").json()
    assert sum(a["name"] == "readiness_report.md" for a in rep2["artifacts"]) == 1
