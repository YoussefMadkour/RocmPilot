"""Render a ROCm-ready Dockerfile from a template.

OWNER: Jithendra (templates) + Youssef (wiring). Keep the base image simple and
demo-reliable. The template lives in app/templates/Dockerfile.rocm.template.
"""
from __future__ import annotations

from app.config import TEMPLATES_DIR
from app.services import run_store


def generate(run_id: str) -> str:
    template = (TEMPLATES_DIR / "Dockerfile.rocm.template").read_text(encoding="utf-8")
    run_store.write_artifact(run_id, "Dockerfile.rocm", template)
    return template
