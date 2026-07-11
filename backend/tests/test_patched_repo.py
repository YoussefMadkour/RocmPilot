"""Tests for the patched-repo zip (source with fixes applied + ROCm artifacts)."""
from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _patched_run() -> str:
    rid = client.post("/api/runs", json={"use_sample": True}).json()["run_id"]
    client.post(f"/api/runs/{rid}/scan")
    client.post(f"/api/runs/{rid}/patch")
    return rid


def test_patched_repo_zip_has_fixes_and_artifacts():
    rid = _patched_run()
    r = client.get(f"/api/runs/{rid}/patched_repo.zip")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    # ROCm artifacts included at the repo root.
    assert "patched_repo/Dockerfile.rocm" in names
    assert "patched_repo/smoke_test.py" in names
    assert "patched_repo/benchmark.py" in names
    # At least one .py carries the applied guard (device fix), not a raw 'cuda'.
    py = [n for n in names if n.endswith(".py")]
    blob = "\n".join(zf.read(n).decode("utf-8", "ignore") for n in py)
    assert "torch.cuda.is_available()" in blob


def test_patched_repo_zip_409_before_patch():
    rid = client.post("/api/runs", json={"use_sample": True}).json()["run_id"]
    client.post(f"/api/runs/{rid}/scan")
    assert client.get(f"/api/runs/{rid}/patched_repo.zip").status_code == 409
