"""ROCm Readiness Score (0-100). Deterministic; no LLM.

OWNER: Youssef (backend).

Design philosophy — HONEST, not demo-inflated (see decision log / memory):
ROCm's PyTorch build maps ``'cuda'`` / ``.cuda()`` transparently, so a clean
pure-PyTorch repo with no NVIDIA base image, no CUDA-pinned wheels and no custom
kernels is *genuinely* close to AMD-ready. The score reflects real porting
difficulty, so:

  * HARD blockers dominate  -> nvidia_docker, cuda_dependency, manual_blocker
    (NVIDIA base images, ``+cuXXX`` wheels, ``cudatoolkit``, custom ``.cu`` kernels)
  * SOFT issues barely move it -> cuda_hardcoding (usually a no-op on ROCm),
    missing ROCm artifacts.

Two properties the old cap-only model lacked and this one has:
  1. Severity- and count-sensitive: each finding contributes by severity, so 16
     hardcodings hurt more than 6 (but with diminishing returns — the same
     pattern applied repeatedly is one fix, so marginal impact tapers).
  2. An "unvalidated on AMD" penalty: until a repo is actually proven on AMD it
     cannot be fully ready, so every un-validated repo carries a flat penalty
     that the validation-pass bonus later removes.

Calibrated 2026-07-10 against real repos (bands pinned in tests/test_scoring.py):
    SAMPLE(synthetic) ~37 · yolov5 ~56 · Real-ESRGAN ~65 · nanoGPT ~68  (before)
    all -> 72 after planned patches -> 86 after a passing AMD validation+benchmark.
"""
from __future__ import annotations

import math

from app.models import ActionType, Finding, FindingCategory, ValidationResult, ValidationStatus

# Per-finding penalty weight by severity. Blockers show up as high/critical; a
# lone hardcoded `.cuda()` is low. Weights are what make the score honest.
SEVERITY_WEIGHT = {
    "critical": 26,
    "high": 13,
    "medium": 5,
    "low": 2,
}

# Diminishing-returns ceiling per category. Blocker categories get the biggest
# ceilings; soft categories the smallest. The effective penalty for a category is
#   cap * (1 - exp(-raw / cap))
# which is ~linear for the first finding and saturates toward `cap` — repeated
# instances of the same issue keep hurting, but less each time (one fix pattern).
CATEGORY_CAP = {
    FindingCategory.nvidia_docker: 16,
    FindingCategory.cuda_dependency: 13,
    FindingCategory.cuda_hardcoding: 17,
    FindingCategory.manual_blocker: 30,
    FindingCategory.missing_artifact: 10,
}

# "Not yet validated on AMD" — genuinely lower readiness until proven. Applied to
# the pre-validation score; the validation-pass bonus below effectively removes it.
UNVALIDATED_PENALTY = 12

# Applying auto/suggested patches gets you *ready to test*, not *proven*. Until an
# AMD validation run passes, the projected score is capped here.
AFTER_PLANNED_CEILING = 72

VALIDATION_PASS_BONUS = 10
BENCHMARK_PASS_BONUS = 4
VALIDATION_FAIL_PENALTY = 25


def _clamp(v: float) -> int:
    return max(0, min(100, round(v)))


def _blocker_penalty(findings: list[Finding]) -> float:
    """Severity-weighted, count-sensitive penalty with per-category diminishing returns."""
    raw_by_category: dict[FindingCategory, float] = {}
    for f in findings:
        raw_by_category[f.category] = (
            raw_by_category.get(f.category, 0.0) + SEVERITY_WEIGHT.get(f.severity.value, 0)
        )
    total = 0.0
    for category, raw in raw_by_category.items():
        cap = CATEGORY_CAP.get(category)
        if not cap:
            continue
        total += cap * (1 - math.exp(-raw / cap))
    return total


def score_before(findings: list[Finding]) -> int:
    """Raw readiness given the scan, before any patching or validation."""
    return _clamp(100 - _blocker_penalty(findings) - UNVALIDATED_PENALTY)


def score_after_planned(findings: list[Finding]) -> int:
    """Projected score assuming all auto/suggested patches are applied.

    Manual-review findings still count against us — we can't auto-fix those. The
    result stays capped at AFTER_PLANNED_CEILING because patched != proven-on-AMD.
    """
    remaining = [f for f in findings if f.action_type == ActionType.manual_review]
    return min(AFTER_PLANNED_CEILING, score_before(remaining))


def score_final(after_planned: int, validation: ValidationResult) -> int:
    score = after_planned
    if validation.status == ValidationStatus.passed:
        # A passing AMD run removes the "unvalidated" doubt (and then some).
        score += VALIDATION_PASS_BONUS
        if validation.benchmark_passed:
            score += BENCHMARK_PASS_BONUS
    elif validation.status == ValidationStatus.failed:
        score -= VALIDATION_FAIL_PENALTY
    return _clamp(score)
