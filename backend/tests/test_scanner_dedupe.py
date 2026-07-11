"""Tests for scanner dedupe + HIPIFY vocabulary."""
from __future__ import annotations

from app.models import ActionType, Finding, FindingCategory, Severity
from app.services import scanner_service


def _f(cat, sev, line, matched):
    return Finding(file_path="a.py", line_number=line, severity=sev, category=cat,
                   matched_text=matched, explanation="x", recommended_action="x",
                   action_type=ActionType.auto_patch)


def test_dedupe_collapses_same_line_same_category_keeps_most_severe():
    dup = [
        _f(FindingCategory.cuda_hardcoding, Severity.low, 5, "device = 'cuda:0'"),
        _f(FindingCategory.cuda_hardcoding, Severity.medium, 5, "device = 'cuda:0'"),
    ]
    out = scanner_service._dedupe(dup)
    assert len(out) == 1
    assert out[0].severity == Severity.medium


def test_dedupe_keeps_distinct_categories_on_one_line():
    multi = [
        _f(FindingCategory.cuda_hardcoding, Severity.medium, 5, "x"),
        _f(FindingCategory.nvidia_docker, Severity.high, 5, "x"),
    ]
    assert len(scanner_service._dedupe(multi)) == 2


def test_dedupe_preserves_distinct_missing_artifacts():
    missing = [
        _f(FindingCategory.missing_artifact, Severity.high, 0, "Dockerfile.rocm"),
        _f(FindingCategory.missing_artifact, Severity.medium, 0, "smoke_test.py"),
        _f(FindingCategory.missing_artifact, Severity.low, 0, "benchmark.py"),
    ]
    assert len(scanner_service._dedupe(missing)) == 3


def test_cu_kernel_action_points_at_hipify():
    cu = next(p for p in scanner_service.PATTERNS
              if p.category == FindingCategory.manual_blocker and p.regex.search("kernel.cu "))
    assert "hipify" in cu.recommended_action.lower()
