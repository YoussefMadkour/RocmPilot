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
import io
import re
import zipfile

from app.agents import patch_explainer
from app.models import Artifact, PatchExplanation
from app.services import (
    benchmark_service,
    dockerfile_service,
    run_store,
    scanner_service,
    smoke_test_service,
)

# Cap how many patches we ask the explainer about, to bound LLM calls per run.
MAX_EXPLANATIONS = 12

# Safe, mechanical rewrites for Python device handling. All are in-place line
# substitutions (line counts stay aligned, so _changed_lines can zip them) and
# each is idempotent — the guarded replacement no longer matches its own pattern.
# We deliberately only touch the *unambiguous* forms:
#   torch.device("cuda")  -> guarded lookup
#   x.to("cuda")          -> guarded lookup   (bare literal only)
#   x.cuda()              -> x.to(guarded)     (no-arg only; .cuda(0) left alone)
#   device = "cuda"       -> guarded lookup   (assignment to a device var; matches
#                                              the scanner's auto_patch classification)
_GUARD = '"cuda" if torch.cuda.is_available() else "cpu"'
_REWRITES = [
    (re.compile(r'torch\.device\(\s*["\']cuda["\']\s*\)'), f'torch.device({_GUARD})'),
    (re.compile(r'\.to\(\s*["\']cuda["\']\s*\)'), f'.to({_GUARD})'),
    (re.compile(r'\.cuda\(\s*\)'), f'.to({_GUARD})'),
    (re.compile(r'(\bdevice\s*=\s*)["\']cuda["\']'), rf'\g<1>{_GUARD}'),
]


def _rewrite_python(text: str) -> str:
    for rx, repl in _REWRITES:
        text = rx.sub(repl, text)
    return text


def _changed_lines(original: str, patched: str) -> list[tuple[int, str, str]]:
    """(lineno, before, after) for each line the rewrite changed.

    The rewrites are in-place line substitutions, so line counts stay aligned and
    a positional zip captures exactly the changed lines — a tight, real snippet to
    feed the explainer (not the whole file).
    """
    o, p = original.splitlines(), patched.splitlines()
    return [(i, a, b) for i, (a, b) in enumerate(zip(o, p), start=1) if a != b]


def generate_events(run_id: str):
    """Generator: yields ('status', msg) progress lines while patching, then a final
    ('result', (artifacts, explanations)). Lets the UI stream patch progress."""
    source = run_store.source_dir(run_id)
    diff_chunks: list[str] = []
    explanations: list[PatchExplanation] = []

    yield ("status", "Rewriting hardcoded device handling…")
    for path in sorted(source.rglob("*.py")):
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

        # Explain the real change, grounded in the exact changed lines.
        changed = _changed_lines(original, patched)
        if changed and len(explanations) < MAX_EXPLANATIONS:
            before = "\n".join(line for _, line, _ in changed)
            after = "\n".join(line for _, _, line in changed)
            yield ("status", f"Explaining the change in {rel}…")
            explanations.append(PatchExplanation(
                file_path=rel,
                line_number=changed[0][0],
                original=before,
                patched=after,
                explanation=patch_explainer.explain(before, after, file_path=rel),
            ))

    patch_text = "\n".join(diff_chunks) if diff_chunks else "# No auto-patchable device patterns found.\n"
    run_store.write_artifact(run_id, "patch.diff", patch_text)

    yield ("status", "Generating Dockerfile.rocm…")
    dockerfile_service.generate(run_id)
    yield ("status", "Generating smoke_test.py…")
    smoke_test_service.generate(run_id)
    yield ("status", "Generating benchmark.py…")
    benchmark_service.generate(run_id)

    artifacts = [
        Artifact(name="patch.diff", path="patch.diff", language="diff"),
        Artifact(name="Dockerfile.rocm", path="Dockerfile.rocm", language="dockerfile"),
        Artifact(name="smoke_test.py", path="smoke_test.py", language="python"),
        Artifact(name="benchmark.py", path="benchmark.py", language="python"),
    ]
    yield ("result", (artifacts, explanations))


def generate(run_id: str) -> tuple[list[Artifact], list[PatchExplanation]]:
    """Batch version: drain the progress stream and return the final result."""
    artifacts: list[Artifact] = []
    explanations: list[PatchExplanation] = []
    for kind, payload in generate_events(run_id):
        if kind == "result":
            artifacts, explanations = payload
    return artifacts, explanations


# ROCm artifacts to drop into the patched repo root (generated at the patch step).
_ROCM_ARTIFACTS = ("Dockerfile.rocm", "smoke_test.py", "benchmark.py")


def patched_repo_zip(run_id: str) -> bytes:
    """A ready-to-run copy of the repo: source with the device patches APPLIED,
    plus the generated ROCm Dockerfile / smoke test / benchmark at the root.

    Unlike patch.diff (which the user applies themselves), this is the fixed repo
    they can build and run directly on AMD.
    """
    source = run_store.source_dir(run_id)
    buf = io.BytesIO()
    written: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source.rglob("*")):
            if path.is_dir() or any(part in scanner_service.SKIP_DIRS for part in path.parts):
                continue
            rel = str(path.relative_to(source))
            if path.suffix == ".py":
                # Apply the same safe device-handling rewrites as patch.diff.
                zf.writestr(f"patched_repo/{rel}", _rewrite_python(path.read_text(errors="ignore")))
            else:
                zf.writestr(f"patched_repo/{rel}", path.read_bytes())
            written.add(rel)
        # Add the generated ROCm artifacts at the repo root (skip if the repo
        # already ships a file by that name).
        for name in _ROCM_ARTIFACTS:
            if name in written:
                continue
            content = run_store.read_artifact(run_id, name)
            if content is not None:
                zf.writestr(f"patched_repo/{name}", content)
    return buf.getvalue()
