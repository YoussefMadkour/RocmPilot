"""Failure Diagnoser agent.

OWNER: Youssef (AI). Reads failed build/smoke-test logs, suggests a root cause + fix.
Wired into the validate endpoint only when validation fails.
"""
from __future__ import annotations

from app.agents import prompts
from app.services import fireworks_service


def diagnose(logs: str) -> str:
    raw = fireworks_service.complete(
        system=prompts.FAILURE_DIAGNOSER,
        user=f"Logs:\n{logs}\n\nGive root cause, suggested fix, confidence, next command.",
        max_tokens=500,
    )
    if raw:
        return raw.strip()
    return (
        "Root cause: unable to reach the AMD/ROCm runtime (no HIP device visible).\n"
        "Suggested fix: ensure /dev/kfd and /dev/dri are mounted and a ROCm PyTorch "
        "wheel is installed.\nConfidence: medium.\nNext command: `rocminfo`."
    )
