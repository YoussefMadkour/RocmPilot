"""Final Report agent.

OWNER: Youssef (AI). Synthesizes everything into a judge-friendly Markdown report.
"""
from __future__ import annotations

import json

from app.agents import prompts
from app.config import settings
from app.models import Artifact, MigrationPlan, ScoreBreakdown, ValidationResult
from app.services import fireworks_service


def _replay_note(mode: str) -> str:
    if mode in ("replay", "replay_fail"):
        return "> _Saved AMD run (replay) — not executed live during this session._\n"
    return ""


def _diagnosis_section(validation: ValidationResult) -> str:
    if validation.diagnosis:
        return f"\n## Failure diagnosis\n{validation.diagnosis}\n"
    return ""


def _strip_doc_fence(text: str) -> str:
    """Drop a code fence wrapping the WHOLE document (some models add ```markdown)."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            t = "\n".join(lines[1:-1]).strip()
    return t


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
{_replay_note(validation.mode)}
- Status: **{validation.status.value}**
- ROCm detected: {validation.rocm_detected}
- HIP available: {validation.hip_available}
- PyTorch build: {validation.pytorch_rocm_build}
- GPU: {validation.gpu_name}
- Smoke test: {'passed' if validation.smoke_test_passed else 'failed'}
- Benchmark: {'passed' if validation.benchmark_passed else 'failed'}
- Inference latency: {validation.inference_latency_ms} ms
{_diagnosis_section(validation)}
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
        model=settings.report_model,
        max_tokens=2800,
    )
    return _strip_doc_fence(raw) if raw else _fallback(source, plan, artifacts, validation, score)
