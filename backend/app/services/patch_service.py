"""Generate a unified-diff patch for safe device-handling fixes.

OWNER: Youssef (backend). This produces patch.diff plus the ROCm artifacts and
returns the list of generated artifacts. The transformation below is intentionally
conservative: it only rewrites clearly-safe hardcoded-cuda device patterns.

NOTE on ROCm + PyTorch: the torch device API still uses the string "cuda" even
when running on AMD ROCm (PyTorch exposes HIP through the cuda namespace). So the
goal of these patches is NOT to rename "cuda" -> "rocm"; it is to remove
NVIDIA-only *assumptions* (base images, nvidia-smi, cuda wheels) and to add a
graceful availability check.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from app.models import Artifact
from app.services import (
    benchmark_service,
    dockerfile_service,
    run_store,
    smoke_test_service,
)

# Safe, mechanical rewrites for Python device handling.
_REWRITES = [
    (re.compile(r'torch\.device\(\s*["\']cuda["\']\s*\)'),
     'torch.device("cuda" if torch.cuda.is_available() else "cpu")'),
]


def _rewrite_python(text: str) -> str:
    for rx, repl in _REWRITES:
        text = rx.sub(repl, text)
    return text


def generate(run_id: str) -> list[Artifact]:
    source = run_store.source_dir(run_id)
    diff_chunks: list[str] = []

    for path in source.rglob("*.py"):
        original = path.read_text(errors="ignore")
        patched = _rewrite_python(original)
        if patched == original:
            continue
        rel = str(path.relative_to(source))
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
        diff_chunks.append("".join(diff))

    patch_text = "\n".join(diff_chunks) if diff_chunks else "# No auto-patchable device patterns found.\n"
    run_store.write_artifact(run_id, "patch.diff", patch_text)

    # Generate the ROCm artifacts alongside the patch.
    dockerfile_service.generate(run_id)
    smoke_test_service.generate(run_id)
    benchmark_service.generate(run_id)

    return [
        Artifact(name="patch.diff", path="patch.diff", language="diff"),
        Artifact(name="Dockerfile.rocm", path="Dockerfile.rocm", language="dockerfile"),
        Artifact(name="smoke_test.py", path="smoke_test.py", language="python"),
        Artifact(name="benchmark.py", path="benchmark.py", language="python"),
    ]
