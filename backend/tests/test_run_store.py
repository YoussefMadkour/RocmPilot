"""Unit tests for run_store.list_runs (Phase 1 [J] backend task)."""
from __future__ import annotations

import json
import os
import time

from app.services import run_store


def _write_run(runs_dir, run_id: str, mtime: float, **extra) -> None:
    d = runs_dir / run_id
    d.mkdir(parents=True)
    state = {"run_id": run_id, "source": "sample:demo", "stage": "created", **extra}
    path = d / "state.json"
    path.write_text(json.dumps(state))
    os.utime(path, (mtime, mtime))


def test_list_runs_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path / "nope")
    assert run_store.list_runs() == []


def test_list_runs_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
    now = time.time()
    _write_run(tmp_path, "older", now - 100)
    _write_run(tmp_path, "newer", now)
    assert [s["run_id"] for s in run_store.list_runs()] == ["newer", "older"]


def test_list_runs_skips_corrupt_state(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
    _write_run(tmp_path, "good", time.time())
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "state.json").write_text("{not json")
    assert [s["run_id"] for s in run_store.list_runs()] == ["good"]
