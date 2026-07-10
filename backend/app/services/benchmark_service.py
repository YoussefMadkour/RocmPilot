"""Render the benchmark script from a template.

OWNER: Jithendra (template) + Youssef (wiring).
"""
from __future__ import annotations

from app.config import TEMPLATES_DIR
from app.services import run_store


def generate(run_id: str) -> str:
    template = (TEMPLATES_DIR / "benchmark.py.template").read_text()
    run_store.write_artifact(run_id, "benchmark.py", template)
    return template
