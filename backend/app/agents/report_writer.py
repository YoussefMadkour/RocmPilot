"""Final Report agent.

OWNER: Youssef (AI). Synthesizes everything into a judge-friendly Markdown report.
"""
from __future__ import annotations

import json

from app.agents import prompts
from app.models import Artifact, MigrationPlan, ScoreBreakdown, ValidationResult
from app.services import fireworks_service


def _fallback(
    source: str,
    plan: MigrationPlan,
    artifacts: list[Artifact],
    validation: ValidationResult,
    score: ScoreBreakdown,
) -> str:
    artifact_list = "\n".join(f"- `{a.name}`" for a in artifacts)
    blockers = "\n".join(f"- {b}" for b in plan.manual_blockers) or "- None"
    return f"""# RocmPilot Readiness Report

**Source:** {source}

## Executive summary
{plan.summary}

## ROCm Readiness Score
- Before: **{score.before}/100**
- After planned patches: **{score.after_planned}/100**
- Final (validated): **{score.final}/100**

## AMD validation evidence ({validation.mode} mode)
- Status: **{validation.status.value}**
- ROCm detected: {validation.rocm_detected}
- HIP available: {validation.hip_available}
- PyTorch build: {validation.pytorch_rocm_build}
- GPU: {validation.gpu_name}
- Smoke test: {'passed' if validation.smoke_test_passed else 'failed'}
- Benchmark: {'passed' if validation.benchmark_passed else 'failed'}
- Inference latency: {validation.inference_latency_ms} ms

## Generated artifacts
{artifact_list}

## Manual blockers
{blockers}

## Next steps
Apply `patch.diff`, build with `Dockerfile.rocm`, and run `smoke_test.py` on AMD
Developer Cloud to confirm the readiness score on your own hardware.
"""


def write(
    source: str,
    plan: MigrationPlan,
    artifacts: list[Artifact],
    validation: ValidationResult,
    score: ScoreBreakdown,
) -> str:
    payload = {
        "source": source,
        "plan": plan.model_dump(mode="json"),
        "artifacts": [a.model_dump(mode="json") for a in artifacts],
        "validation": validation.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
    }
    raw = fireworks_service.complete(
        system=prompts.REPORT_WRITER,
        user="Data:\n" + json.dumps(payload, indent=2) + "\n\nReturn Markdown only.",
        max_tokens=1500,
    )
    return raw.strip() if raw else _fallback(source, plan, artifacts, validation, score)
