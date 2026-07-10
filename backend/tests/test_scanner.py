"""Unit tests for the deterministic scanner.

Each new pattern added in Phase 1 gets a dedicated case, plus guards against
obvious false positives and the repo-level missing-artifact findings.
Run from backend/: `pytest`
"""
from __future__ import annotations

import pytest

from app.models import ActionType, FindingCategory, Severity
from app.services import scanner_service


def scan_file(tmp_path, filename: str, content: str):
    """Scan a one-file repo and return only pattern findings (no missing-artifact noise)."""
    (tmp_path / filename).write_text(content)
    findings, _ = scanner_service.scan(tmp_path)
    return [f for f in findings if f.category != FindingCategory.missing_artifact]


# --------------------------------------------------------------------------- #
# New Phase 1 patterns — one case each
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("filename", "line", "category", "severity", "action_type"),
    [
        ("train.py", "loader = DataLoader(ds, pin_memory=True)",
         FindingCategory.cuda_hardcoding, Severity.low, ActionType.info),
        ("train.py", "torch.backends.cudnn.benchmark = True",
         FindingCategory.cuda_hardcoding, Severity.low, ActionType.suggested_patch),
        ("train.py", "torch.backends.cuda.matmul.allow_tf32 = True",
         FindingCategory.cuda_hardcoding, Severity.low, ActionType.suggested_patch),
        ("train.py", "from apex import amp",
         FindingCategory.cuda_dependency, Severity.high, ActionType.manual_review),
        ("requirements.txt", "bitsandbytes==0.43.0",
         FindingCategory.cuda_dependency, Severity.high, ActionType.manual_review),
        ("requirements.txt", "flash-attn==2.5.8",
         FindingCategory.cuda_dependency, Severity.high, ActionType.manual_review),
        ("model.py", "import flash_attn",
         FindingCategory.cuda_dependency, Severity.high, ActionType.manual_review),
    ],
)
def test_new_patterns(tmp_path, filename, line, category, severity, action_type):
    findings = scan_file(tmp_path, filename, line)
    assert len(findings) == 1, f"expected exactly one finding for {line!r}"
    f = findings[0]
    assert f.category == category
    assert f.severity == severity
    assert f.action_type == action_type
    assert f.file_path == filename
    assert f.line_number == 1


def test_apex_does_not_match_unrelated_words(tmp_path):
    findings = scan_file(tmp_path, "game.py", "apexes = compute_apex_points()\n")
    assert findings == []


# --------------------------------------------------------------------------- #
# Existing patterns — sanity checks
# --------------------------------------------------------------------------- #
def test_hardcoded_torch_device(tmp_path):
    findings = scan_file(tmp_path, "app.py", 'device = torch.device("cuda")\n')
    assert len(findings) == 1
    assert findings[0].category == FindingCategory.cuda_hardcoding
    assert findings[0].action_type == ActionType.auto_patch


def test_nvidia_base_image(tmp_path):
    findings = scan_file(tmp_path, "Dockerfile", "FROM nvidia/cuda:12.1.0-runtime\n")
    assert any(
        f.category == FindingCategory.nvidia_docker and f.severity == Severity.high
        for f in findings
    )


def test_cuda_pinned_wheel(tmp_path):
    findings = scan_file(tmp_path, "requirements.txt", "torch==2.4.0+cu121\n")
    assert len(findings) == 1
    assert findings[0].category == FindingCategory.cuda_dependency


# --------------------------------------------------------------------------- #
# Repo-level behavior
# --------------------------------------------------------------------------- #
def test_missing_artifacts_flagged(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    findings, files_scanned = scanner_service.scan(tmp_path)
    missing = {f.matched_text for f in findings if f.category == FindingCategory.missing_artifact}
    assert missing == {"Dockerfile.rocm", "smoke_test.py", "benchmark.py"}
    assert files_scanned == 1


def test_present_artifact_not_flagged(tmp_path):
    (tmp_path / "Dockerfile.rocm").write_text("FROM rocm/pytorch\n")
    findings, _ = scanner_service.scan(tmp_path)
    missing = {f.matched_text for f in findings if f.category == FindingCategory.missing_artifact}
    assert "Dockerfile.rocm" not in missing


def test_skip_dirs_ignored(tmp_path):
    hidden = tmp_path / ".venv" / "lib"
    hidden.mkdir(parents=True)
    (hidden / "cuda_stuff.py").write_text('device = "cuda"\n')
    findings = [
        f for f in scanner_service.scan(tmp_path)[0]
        if f.category != FindingCategory.missing_artifact
    ]
    assert findings == []


def test_count_by_category(tmp_path):
    (tmp_path / "a.py").write_text('device = "cuda"\nfrom apex import amp\n')
    findings, _ = scanner_service.scan(tmp_path)
    counts = scanner_service.count_by_category(findings)
    assert counts["cuda_hardcoding"] == 1
    assert counts["cuda_dependency"] == 1
    assert counts["missing_artifact"] == 3
