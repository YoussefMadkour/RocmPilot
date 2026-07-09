"""ROCm Readiness Score (0-100). Deterministic; no LLM.

OWNER: Youssef (backend). Tune the weights below with the demo in mind:
target is a believable ~35-45 "before" and ~80-90 "after".
"""
from __future__ import annotations

from app.models import ActionType, Finding, FindingCategory, ValidationResult, ValidationStatus

# Per-finding penalties, applied against a starting score of 100.
CATEGORY_PENALTY = {
    FindingCategory.nvidia_docker: 18,
    FindingCategory.cuda_dependency: 15,
    FindingCategory.cuda_hardcoding: 10,
    FindingCategory.manual_blocker: 25,
    FindingCategory.missing_artifact: 8,
}
# Cap how much any single category can drain, so many small hits don't zero the
# score out. Tuned so a heavily CUDA-first repo lands in the believable 35-45 band.
CATEGORY_CAP = {
    FindingCategory.nvidia_docker: 18,
    FindingCategory.cuda_dependency: 15,
    FindingCategory.cuda_hardcoding: 18,
    FindingCategory.manual_blocker: 25,
    FindingCategory.missing_artifact: 12,
}

# Applying auto/suggested patches gets you *ready to test*, not *proven*. Until an
# AMD validation run passes, the projected score is capped here.
AFTER_PLANNED_CEILING = 72

VALIDATION_PASS_BONUS = 10
BENCHMARK_PASS_BONUS = 4
VALIDATION_FAIL_PENALTY = 25


def _clamp(v: int) -> int:
    return max(0, min(100, v))


def score_before(findings: list[Finding]) -> int:
    """Raw readiness given the scan, before any patching."""
    per_category: dict[FindingCategory, int] = {}
    for f in findings:
        pen = CATEGORY_PENALTY.get(f.category, 0)
        per_category[f.category] = per_category.get(f.category, 0) + pen

    total_penalty = 0
    for cat, pen in per_category.items():
        cap = CATEGORY_CAP.get(cat)
        total_penalty += min(pen, cap) if cap else pen
    return _clamp(100 - total_penalty)


def score_after_planned(findings: list[Finding]) -> int:
    """Projected score assuming all auto/suggested patches are applied.

    Manual-review findings still count against us — we can't auto-fix those.
    """
    remaining = [
        f for f in findings
        if f.action_type in (ActionType.manual_review,)
    ]
    return min(AFTER_PLANNED_CEILING, score_before(remaining))


def score_final(after_planned: int, validation: ValidationResult) -> int:
    score = after_planned
    if validation.status == ValidationStatus.passed:
        score += VALIDATION_PASS_BONUS
        if validation.benchmark_passed:
            score += BENCHMARK_PASS_BONUS
    elif validation.status == ValidationStatus.failed:
        score -= VALIDATION_FAIL_PENALTY
    return _clamp(score)
