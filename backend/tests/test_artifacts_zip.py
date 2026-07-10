"""End-to-end test for GET /api/runs/{id}/artifacts.zip (Phase 3 [J] task)."""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import run_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_runs_dir(tmp_path, monkeypatch):
    """Keep test runs out of the real backend/runs directory."""
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)


def _create_sample_run() -> str:
    res = client.post("/api/runs", json={"use_sample": True})
    assert res.status_code == 200
    return res.json()["run_id"]


def test_zip_requires_patch_step_first():
    run_id = _create_sample_run()
    res = client.get(f"/api/runs/{run_id}/artifacts.zip")
    assert res.status_code == 409


def test_zip_bundles_all_artifacts():
    run_id = _create_sample_run()
    assert client.post(f"/api/runs/{run_id}/scan").status_code == 200
    assert client.post(f"/api/runs/{run_id}/patch").status_code == 200

    res = client.get(f"/api/runs/{run_id}/artifacts.zip")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "attachment" in res.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    assert set(zf.namelist()) == {
        "patch.diff",
        "Dockerfile.rocm",
        "smoke_test.py",
        "benchmark.py",
    }
    # Spot-check content actually made it into the zip.
    assert b"rocm/pytorch" in zf.read("Dockerfile.rocm")


def test_zip_unknown_run_is_404():
    assert client.get("/api/runs/nope/artifacts.zip").status_code == 404
