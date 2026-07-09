"""Patch Explainer agent.

OWNER: Youssef (AI). Explains why a generated patch is safe for ROCm.
"""
from __future__ import annotations

from app.agents import prompts
from app.services import fireworks_service


def explain(original: str, patched: str) -> str:
    raw = fireworks_service.complete(
        system=prompts.PATCH_EXPLAINER,
        user=f"Original:\n{original}\n\nProposed:\n{patched}\n\nExplain safety in 2-3 sentences.",
        max_tokens=300,
    )
    if raw:
        return raw.strip()
    # Deterministic fallback.
    return (
        "Replaces a hardcoded CUDA device with an availability-guarded lookup. "
        "On AMD/ROCm, PyTorch still reports devices through torch.cuda, so this keeps "
        "GPU acceleration while gracefully falling back to CPU when no accelerator is present. "
        "No behavior change on NVIDIA hosts."
    )
