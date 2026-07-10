"""Render the AMD/ROCm smoke test from a template.

OWNER: Jithendra (template) + Youssef (wiring).
"""
from __future__ import annotations

from app.config import TEMPLATES_DIR
from app.services import run_store


def generate(run_id: str) -> str:
    template = (TEMPLATES_DIR / "smoke_test.py.template").read_text()
    run_store.write_artifact(run_id, "smoke_test.py", template)
    return template
