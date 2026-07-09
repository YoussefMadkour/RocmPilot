"""Get project source into a run's source/ dir: from a sample or a git clone.

OWNER: Youssef (backend). The git-clone path is intentionally minimal; harden
input validation before pointing it at arbitrary user URLs.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import SAMPLE_PROJECTS_DIR
from app.services import run_store

DEFAULT_SAMPLE = "cuda_first_transformers_demo"


def load_sample(run_id: str, sample_name: str = DEFAULT_SAMPLE) -> Path:
    src = SAMPLE_PROJECTS_DIR / sample_name
    if not src.exists():
        raise FileNotFoundError(f"Sample project not found: {sample_name}")
    dst = run_store.source_dir(run_id)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return dst


def clone_repo(run_id: str, repo_url: str) -> Path:
    dst = run_store.source_dir(run_id)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)
    # --depth 1 keeps it fast; we only need a snapshot to scan.
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(dst)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return dst
