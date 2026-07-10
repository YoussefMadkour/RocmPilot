"""Tests for the ROCm readiness score.

Two layers:
  * Property tests: honesty invariants of the scoring model (blockers > soft
    issues, count sensitivity, diminishing returns, clamping, validation math).
  * Locked bands: the demo curve on the committed SAMPLE repo, plus the real
    showcase repos' finding *profiles* (captured 2026-07-10) so pattern/weight
    changes can't silently drift the calibrated curve.
"""
from __future__ import annotations

import pytest

from app.config import SAMPLE_PROJECTS_DIR
from app.models import (
    ActionType, Finding, FindingCategory, Severity, ValidationResult, ValidationStatus,
)
from app.services import scanner_service, scoring_service


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _finding(category: FindingCategory, severity: Severity,
             action_type: ActionType = ActionType.auto_patch) -> Finding:
    return Finding(
        file_path="f.py", line_number=1, severity=severity, category=category,
        matched_text="x", explanation="x", recommended_action="x", action_type=action_type,
    )


def _profile(spec: dict[tuple[FindingCategory, Severity], int],
             action_type: ActionType = ActionType.suggested_patch) -> list[Finding]:
    out: list[Finding] = []
    for (cat, sev), n in spec.items():
        out.extend(_finding(cat, sev, action_type) for _ in range(n))
    return out


def _validation(status: ValidationStatus, benchmark: bool = False) -> ValidationResult:
    return ValidationResult(status=status, mode="replay", benchmark_passed=benchmark)


# --------------------------------------------------------------------------- #
# Property tests — honesty invariants
# --------------------------------------------------------------------------- #
def test_pristine_repo_only_pays_unvalidated_penalty():
    assert scoring_service.score_before([]) == 100 - scoring_service.UNVALIDATED_PENALTY


def test_score_is_clamped():
    huge = [_finding(FindingCategory.manual_blocker, Severity.critical) for _ in range(50)]
    assert 0 <= scoring_service.score_before(huge) <= 100


def test_blocker_hurts_more_than_soft_issue():
    blocker = [_finding(FindingCategory.cuda_dependency, Severity.high)]
    soft = [_finding(FindingCategory.cuda_hardcoding, Severity.low)]
    assert scoring_service.score_before(blocker) < scoring_service.score_before(soft)


def test_more_findings_never_raise_score():
    few = [_finding(FindingCategory.cuda_hardcoding, Severity.medium) for _ in range(3)]
    many = [_finding(FindingCategory.cuda_hardcoding, Severity.medium) for _ in range(12)]
    assert scoring_service.score_before(many) <= scoring_service.score_before(few)


def test_count_sensitivity_is_real():
    """The old cap-only model tied these; the new model must separate them."""
    six = [_finding(FindingCategory.cuda_hardcoding, Severity.low) for _ in range(6)]
    sixteen = [_finding(FindingCategory.cuda_hardcoding, Severity.low) for _ in range(16)]
    assert scoring_service.score_before(sixteen) < scoring_service.score_before(six)


def test_diminishing_returns():
    """Doubling identical findings must add < 2x the penalty (same-pattern fix)."""
    base = [_finding(FindingCategory.cuda_hardcoding, Severity.medium) for _ in range(4)]
    dbl = [_finding(FindingCategory.cuda_hardcoding, Severity.medium) for _ in range(8)]
    pen_base = 100 - scoring_service.UNVALIDATED_PENALTY - scoring_service.score_before(base)
    pen_dbl = 100 - scoring_service.UNVALIDATED_PENALTY - scoring_service.score_before(dbl)
    assert pen_dbl < 2 * pen_base


# --------------------------------------------------------------------------- #
# after_planned / final math
# --------------------------------------------------------------------------- #
def test_after_planned_capped():
    findings = [_finding(FindingCategory.nvidia_docker, Severity.high) for _ in range(4)]
    assert scoring_service.score_after_planned(findings) <= scoring_service.AFTER_PLANNED_CEILING


def test_manual_review_still_counts_after_planning():
    manual = [_finding(FindingCategory.manual_blocker, Severity.critical, ActionType.manual_review)]
    auto = [_finding(FindingCategory.cuda_hardcoding, Severity.medium, ActionType.auto_patch)]
    # Auto-fixable issues vanish after planning (-> ceiling); manual ones do not.
    assert scoring_service.score_after_planned(auto) == scoring_service.AFTER_PLANNED_CEILING
    assert scoring_service.score_after_planned(manual) < scoring_service.AFTER_PLANNED_CEILING


def test_final_pass_and_benchmark_bonus():
    base = 72
    assert scoring_service.score_final(base, _validation(ValidationStatus.passed)) == \
        base + scoring_service.VALIDATION_PASS_BONUS
    assert scoring_service.score_final(base, _validation(ValidationStatus.passed, True)) == \
        base + scoring_service.VALIDATION_PASS_BONUS + scoring_service.BENCHMARK_PASS_BONUS


def test_final_failure_penalized():
    assert scoring_service.score_final(72, _validation(ValidationStatus.failed)) == \
        72 - scoring_service.VALIDATION_FAIL_PENALTY


def test_final_not_run_is_noop():
    assert scoring_service.score_final(72, _validation(ValidationStatus.not_run)) == 72


# --------------------------------------------------------------------------- #
# Locked demo curve — committed SAMPLE repo
# --------------------------------------------------------------------------- #
def test_sample_repo_hits_demo_curve():
    findings, _ = scanner_service.scan(SAMPLE_PROJECTS_DIR / "cuda_first_transformers_demo")
    before = scoring_service.score_before(findings)
    after = scoring_service.score_after_planned(findings)
    final = scoring_service.score_final(after, _validation(ValidationStatus.passed, True))
    assert 34 <= before <= 40, f"SAMPLE before drifted: {before}"
    assert after == 72
    assert final == 86


# --------------------------------------------------------------------------- #
# Locked bands — real showcase repo profiles (captured from live scans 2026-07-10)
# Guards the honest calibration: clean pure-PyTorch repos score higher than the
# blocker-laden sample, and count sensitivity keeps Real-ESRGAN below nanoGPT.
# --------------------------------------------------------------------------- #
CH, MA, ND = (FindingCategory.cuda_hardcoding, FindingCategory.missing_artifact,
              FindingCategory.nvidia_docker)
LO, ME, HI = Severity.low, Severity.medium, Severity.high

REAL_REPO_PROFILES = {
    # name: (finding profile, expected before-band)
    "nanoGPT": ({(CH, LO): 3, (CH, ME): 3, (MA, HI): 1, (MA, ME): 1, (MA, LO): 1}, (63, 71)),
    "yolov5": ({(CH, LO): 7, (CH, ME): 9, (ND, ME): 2,
                (MA, HI): 1, (MA, ME): 1, (MA, LO): 1}, (50, 60)),
    "Real-ESRGAN": ({(CH, LO): 15, (CH, ME): 1, (MA, HI): 1, (MA, ME): 1, (MA, LO): 1}, (60, 69)),
}


@pytest.mark.parametrize("name", list(REAL_REPO_PROFILES))
def test_real_repo_before_band(name):
    spec, (lo, hi) = REAL_REPO_PROFILES[name]
    before = scoring_service.score_before(_profile(spec))
    assert lo <= before <= hi, f"{name} before {before} outside [{lo},{hi}]"


def test_ordering_sample_below_real_repos():
    """Honest ordering: the blocker-laden synthetic sample scores below clean repos."""
    sample_findings, _ = scanner_service.scan(
        SAMPLE_PROJECTS_DIR / "cuda_first_transformers_demo")
    sample_before = scoring_service.score_before(sample_findings)
    for name, (spec, _band) in REAL_REPO_PROFILES.items():
        assert sample_before < scoring_service.score_before(_profile(spec)), name


def test_count_sensitivity_across_real_repos():
    """Real-ESRGAN (16 hardcodings) must score <= nanoGPT (6) — old model tied them."""
    nano = _profile(REAL_REPO_PROFILES["nanoGPT"][0])
    esrgan = _profile(REAL_REPO_PROFILES["Real-ESRGAN"][0])
    assert scoring_service.score_before(esrgan) <= scoring_service.score_before(nano)
