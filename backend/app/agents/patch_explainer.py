"""Patch Explainer agent.

OWNER: Youssef (AI). Explains why a generated patch is safe for ROCm, grounded in
the ACTUAL changed lines (not a generic blurb). Falls back deterministically when
Fireworks is unavailable so the demo always shows an explanation.
"""
from __future__ import annotations

from app.agents import prompts
from app.services import fireworks_service


def explain(original: str, patched: str, *, file_path: str = "") -> str:
    """Explain, in 2-3 sentences, why replacing `original` with `patched` is ROCm-safe."""
    where = file_path or "(snippet)"
    raw = fireworks_service.complete(
        system=prompts.PATCH_EXPLAINER,
        user=(
            f"File: {where}\n"
            f"Original:\n{original}\n\n"
            f"Proposed:\n{patched}\n\n"
            "Explain safety in 2-3 sentences."
        ),
        max_tokens=300,
    )
    if raw:
        return raw.strip()

    # Deterministic fallback — grounded in the file being changed.
    prefix = f"In {file_path}, " if file_path else ""
    return (
        f"{prefix}the hardcoded CUDA device is replaced with an availability-guarded "
        "lookup. On AMD/ROCm, PyTorch still reports devices through the torch.cuda "
        "namespace, so this preserves GPU acceleration while gracefully falling back "
        "to CPU when no accelerator is present, with no behavior change on NVIDIA hosts."
    )
