"""Tests for GET /api/runs/{id} (RunDetail) — the hydrate-any-screen endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _new_run() -> str:
    return client.post("/api/runs", json={"use_sample": True}).json()["run_id"]


def test_get_run_404_for_unknown():
    assert client.get("/api/runs/nope").status_code == 404


def test_get_run_progressively_hydrates():
    rid = _new_run()

    # Freshly created: summary present, step outputs still null.
    d = client.get(f"/api/runs/{rid}").json()
    assert d["stage"] == "created"
    assert d["findings"] is None and d["plan"] is None and d["validation"] is None

    client.post(f"/api/runs/{rid}/scan")
    d = client.get(f"/api/runs/{rid}").json()
    assert d["stage"] == "scanned"
    assert d["findings"] is not None
    assert d["findings_by_category"]  # computed on read
    assert d["plan"] is None

    client.post(f"/api/runs/{rid}/plan")
    d = client.get(f"/api/runs/{rid}").json()
    assert d["plan"] is not None
    assert d["critique"] is not None
    assert d["trace"]  # agent trace cached

    client.post(f"/api/runs/{rid}/patch")
    client.post(f"/api/runs/{rid}/validate")
    d = client.get(f"/api/runs/{rid}").json()
    assert d["artifacts"] and d["validation"] is not None
    assert d["stage"] == "validated"
