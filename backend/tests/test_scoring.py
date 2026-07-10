"""Unit tests for the deterministic ROCm readiness score.

These pin the scoring behavior (penalties, caps, ceiling, validation bonuses)
so weight tuning is a conscious act, not an accident.
"""
from __future__ import annotations

from app.models import ActionType, Finding, FindingCategory, Severity, ValidationResult, ValidationStatus
from app.services import scoring_service


def make_finding(
    category: FindingCategory,
    action_type: ActionType = ActionType.auto_patch,
    severity: Severity = Severity.medium,
) -> Finding:
    return Finding(
        file_path="app.py",
        line_number=1,
        severity=severity,
        category=category,
        matched_text="x",
        explanation="x",
        recommended_action="x",
        action_type=action_type,
    )


def make_validation(status: ValidationStatus, benchmark_passed: bool = False) -> ValidationResult:
    return ValidationResult(status=status, mode="replay", benchmark_passed=benchmark_passed)


# --------------------------------------------------------------------------- #
# score_before
# --------------------------------------------------------------------------- #
def test_clean_repo_scores_100():
    assert scoring_service.score_before([]) == 100


def test_single_finding_applies_category_penalty():
    findings = [make_finding(FindingCategory.nvidia_docker)]
    assert scoring_service.score_before(findings) == 100 - 18


def test_category_penalty_is_capped():
    # 5 hardcoding findings would be -50 uncapped; the cap keeps it at -18.
    findings = [make_finding(FindingCategory.cuda_hardcoding)] * 5
    assert scoring_service.score_before(findings) == 100 - 18


def test_penalties_sum_across_categories():
    findings = [
        make_finding(FindingCategory.nvidia_docker),     # -18
        make_finding(FindingCategory.cuda_dependency),   # -15
    ]
    assert scoring_service.score_before(findings) == 100 - 18 - 15


# --------------------------------------------------------------------------- #
# score_after_planned
# --------------------------------------------------------------------------- #
def test_after_planned_hits_ceiling_when_everything_is_patchable():
    findings = [
        make_finding(FindingCategory.cuda_hardcoding, ActionType.auto_patch),
        make_finding(FindingCategory.nvidia_docker, ActionType.suggested_patch),
    ]
    assert scoring_service.score_after_planned(findings) == scoring_service.AFTER_PLANNED_CEILING


def test_after_planned_still_penalizes_manual_review():
    findings = [
        make_finding(FindingCategory.manual_blocker, ActionType.manual_review),   # -25
        make_finding(FindingCategory.cuda_dependency, ActionType.manual_review),  # -15
        make_finding(FindingCategory.cuda_hardcoding, ActionType.auto_patch),     # patched away
    ]
    assert scoring_service.score_after_planned(findings) == 100 - 25 - 15  # = 60 < ceiling


# --------------------------------------------------------------------------- #
# score_final
# --------------------------------------------------------------------------- #
def test_final_demo_curve():
    # The advertised 72 -> 86 jump: validation pass +10, benchmark pass +4.
    validation = make_validation(ValidationStatus.passed, benchmark_passed=True)
    assert scoring_service.score_final(72, validation) == 86


def test_final_pass_without_benchmark():
    validation = make_validation(ValidationStatus.passed, benchmark_passed=False)
    assert scoring_service.score_final(72, validation) == 82


def test_final_failed_validation_penalizes():
    validation = make_validation(ValidationStatus.failed)
    assert scoring_service.score_final(72, validation) == 72 - 25


def test_final_not_run_leaves_score_unchanged():
    validation = make_validation(ValidationStatus.not_run)
    assert scoring_service.score_final(72, validation) == 72


def test_final_clamps_to_bounds():
    assert scoring_service.score_final(10, make_validation(ValidationStatus.failed)) == 0
    assert scoring_service.score_final(95, make_validation(ValidationStatus.passed, True)) == 100
