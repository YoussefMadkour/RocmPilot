"""Dead-simple filesystem-backed run store.

Each run lives at backend/runs/<run_id>/ and its state is a single state.json.
Good enough for a hackathon; swap for SQLite later if you want history/queries.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from app.config import RUNS_DIR


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def source_dir(run_id: str) -> Path:
    return run_dir(run_id) / "source"


def _state_path(run_id: str) -> Path:
    return run_dir(run_id) / "state.json"


def create(source: str) -> str:
    run_id = new_run_id()
    source_dir(run_id).mkdir(parents=True, exist_ok=True)
    save_state(run_id, {"run_id": run_id, "source": source, "stage": "created"})
    return run_id


def list_runs() -> list[dict[str, Any]]:
    """All run states, newest first (by state.json mtime). Skips corrupt runs."""
    if not RUNS_DIR.exists():
        return []
    states: list[dict[str, Any]] = []
    for path in sorted(
        RUNS_DIR.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            states.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return states


def exists(run_id: str) -> bool:
    return _state_path(run_id).exists()


def load_state(run_id: str) -> dict[str, Any]:
    return json.loads(_state_path(run_id).read_text())


def save_state(run_id: str, state: dict[str, Any]) -> None:
    _state_path(run_id).write_text(json.dumps(state, indent=2, default=str))


def update_state(run_id: str, **fields: Any) -> dict[str, Any]:
    state = load_state(run_id) if exists(run_id) else {"run_id": run_id}
    state.update(fields)
    save_state(run_id, state)
    return state


def write_artifact(run_id: str, name: str, content: str) -> Path:
    path = run_dir(run_id) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def read_artifact(run_id: str, name: str) -> Optional[str]:
    path = run_dir(run_id) / name
    return path.read_text() if path.exists() else None
