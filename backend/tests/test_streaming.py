"""Tests for the SSE streaming endpoints (plan + patch)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _scanned_run() -> str:
    rid = client.post("/api/runs", json={"use_sample": True}).json()["run_id"]
    client.post(f"/api/runs/{rid}/scan")
    return rid


def test_plan_stream_emits_trace_and_done():
    rid = _scanned_run()
    r = client.get(f"/api/runs/{rid}/plan/stream")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text
    assert "event: trace" in body       # agent-trace steps streamed
    assert "event: done" in body        # final payload
    assert '"agent": "planner"' in body
    # And the plan is now persisted (hydratable).
    assert client.get(f"/api/runs/{rid}").json()["plan"] is not None


def test_patch_stream_emits_status_and_done():
    rid = _scanned_run()
    r = client.get(f"/api/runs/{rid}/patch/stream")
    assert r.status_code == 200
    body = r.text
    assert "event: status" in body      # progress lines streamed
    assert "event: done" in body
    assert "Dockerfile.rocm" in body
    assert client.get(f"/api/runs/{rid}").json()["artifacts"] is not None


def test_plan_stream_409_before_scan():
    rid = client.post("/api/runs", json={"use_sample": True}).json()["run_id"]
    assert client.get(f"/api/runs/{rid}/plan/stream").status_code == 409
