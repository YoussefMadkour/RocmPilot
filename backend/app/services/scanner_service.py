"""Deterministic CUDA/NVIDIA scanner. NO LLM here — pure pattern matching.

OWNER: Youssef (backend). This is the factual backbone of the whole product;
the Fireworks agents only *explain* what this finds. Keep it deterministic and
unit-tested. Add patterns to PATTERNS below.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.models import ActionType, Finding, FindingCategory, Severity

# Files worth scanning by extension / name.
SCANNABLE_SUFFIXES = {".py", ".sh", ".md", ".txt", ".toml", ".yml", ".yaml", ".cu", ".cuh", ".cpp"}
SCANNABLE_NAMES = {"Dockerfile", "requirements.txt", "environment.yml", "pyproject.toml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next"}


@dataclass(frozen=True)
class Pattern:
    regex: re.Pattern[str]
    category: FindingCategory
    severity: Severity
    action_type: ActionType
    explanation: str
    recommended_action: str


def _p(rx: str, category, severity, action_type, explanation, recommended_action) -> Pattern:
    return Pattern(re.compile(rx), category, severity, action_type, explanation, recommended_action)


# --------------------------------------------------------------------------- #
# Pattern catalogue
# --------------------------------------------------------------------------- #
PATTERNS: list[Pattern] = [
    # ---- CUDA hardcoding ----
    _p(r'torch\.device\(\s*["\']cuda', FindingCategory.cuda_hardcoding, Severity.medium,
       ActionType.auto_patch,
       "Hardcoded CUDA device; will not fall back gracefully on non-NVIDIA hosts.",
       'Use torch.device("cuda" if torch.cuda.is_available() else "cpu").'),
    _p(r'\.to\(\s*["\']cuda', FindingCategory.cuda_hardcoding, Severity.medium,
       ActionType.auto_patch,
       "Tensor/model moved to a hardcoded CUDA device.",
       "Move to a resolved `device` variable instead of the literal string."),
    _p(r'device\s*=\s*["\']cuda', FindingCategory.cuda_hardcoding, Severity.medium,
       ActionType.auto_patch,
       "Device string hardcoded to cuda.",
       "Resolve the device dynamically from availability."),
    _p(r'torch\.cuda\.get_device_name', FindingCategory.cuda_hardcoding, Severity.low,
       ActionType.suggested_patch,
       "Assumes a named CUDA device is present.",
       "Guard with torch.cuda.is_available() and handle the CPU/ROCm case."),
    _p(r'cuda:\d', FindingCategory.cuda_hardcoding, Severity.low,
       ActionType.suggested_patch,
       "Hardcoded CUDA device ordinal.",
       "Avoid pinning a device index unless multi-GPU placement is required."),
    _p(r'CUDA_VISIBLE_DEVICES', FindingCategory.cuda_hardcoding, Severity.low,
       ActionType.info,
       "Uses CUDA_VISIBLE_DEVICES; ROCm uses HIP_VISIBLE_DEVICES.",
       "Document/translate to HIP_VISIBLE_DEVICES for AMD hosts."),

    # ---- NVIDIA Docker assumptions ----
    _p(r'FROM\s+nvidia/cuda', FindingCategory.nvidia_docker, Severity.high,
       ActionType.auto_patch,
       "Base image is an NVIDIA CUDA image; unusable on ROCm.",
       "Swap to a ROCm/PyTorch base image (see generated Dockerfile.rocm)."),
    _p(r'nvidia-smi', FindingCategory.nvidia_docker, Severity.medium,
       ActionType.suggested_patch,
       "Calls nvidia-smi; not available on AMD.",
       "Use rocm-smi / rocminfo on AMD hosts."),
    _p(r'--gpus\s+all', FindingCategory.nvidia_docker, Severity.medium,
       ActionType.suggested_patch,
       "Docker --gpus all is NVIDIA runtime specific.",
       "For ROCm, expose /dev/kfd and /dev/dri devices instead."),
    _p(r'NVIDIA_VISIBLE_DEVICES', FindingCategory.nvidia_docker, Severity.low,
       ActionType.info,
       "NVIDIA container runtime variable.",
       "Not needed on ROCm; use HIP_VISIBLE_DEVICES."),
    _p(r'nvidia-container-runtime', FindingCategory.nvidia_docker, Severity.medium,
       ActionType.suggested_patch,
       "Depends on the NVIDIA container runtime.",
       "Remove; ROCm uses standard runtime with device mounts."),

    # ---- CUDA dependencies ----
    _p(r'cudatoolkit', FindingCategory.cuda_dependency, Severity.high,
       ActionType.suggested_patch,
       "Depends on cudatoolkit (NVIDIA-only).",
       "Remove and install a ROCm PyTorch wheel instead."),
    _p(r'cupy[-_]cuda', FindingCategory.cuda_dependency, Severity.high,
       ActionType.manual_review,
       "cupy-cuda is NVIDIA-only.",
       "Evaluate cupy ROCm build or remove the dependency."),
    _p(r'\+cu\d{2,3}', FindingCategory.cuda_dependency, Severity.high,
       ActionType.suggested_patch,
       "Pinned CUDA-specific PyTorch wheel (e.g. +cu121).",
       "Install from the ROCm PyTorch index instead of the CUDA index."),

    # ---- Manual blockers ----
    _p(r'\.cu[h]?["\'\s)]', FindingCategory.manual_blocker, Severity.critical,
       ActionType.manual_review,
       "References a custom CUDA kernel source (.cu/.cuh).",
       "Requires HIPify/manual porting; flag for a human."),
    _p(r'load_inline|CUDAExtension|cpp_extension', FindingCategory.manual_blocker, Severity.critical,
       ActionType.manual_review,
       "Builds a custom native CUDA extension.",
       "Custom kernels must be HIPified and rebuilt for ROCm."),
]

# Artifacts we expect an AMD-ready repo to have. Absence => a "missing_artifact" finding.
EXPECTED_ARTIFACTS = {
    "Dockerfile.rocm": ("No ROCm-ready Dockerfile present.", Severity.high),
    "smoke_test.py": ("No AMD/ROCm smoke test present.", Severity.medium),
    "benchmark.py": ("No benchmark script present.", Severity.low),
}


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SCANNABLE_NAMES or path.suffix in SCANNABLE_SUFFIXES:
            yield path


def scan(root: Path) -> tuple[list[Finding], int]:
    """Return (findings, files_scanned)."""
    findings: list[Finding] = []
    files_scanned = 0

    for path in _iter_files(root):
        files_scanned += 1
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in PATTERNS:
                m = pat.regex.search(line)
                if not m:
                    continue
                findings.append(Finding(
                    file_path=rel,
                    line_number=lineno,
                    severity=pat.severity,
                    category=pat.category,
                    matched_text=line.strip()[:200],
                    explanation=pat.explanation,
                    recommended_action=pat.recommended_action,
                    action_type=pat.action_type,
                ))

    # Missing-artifact findings (line 0 = repo-level).
    existing = {p.name for p in root.rglob("*") if p.is_file()}
    for name, (explanation, severity) in EXPECTED_ARTIFACTS.items():
        if name not in existing:
            findings.append(Finding(
                file_path=".",
                line_number=0,
                severity=severity,
                category=FindingCategory.missing_artifact,
                matched_text=name,
                explanation=explanation,
                recommended_action=f"Generate {name} (RocmPilot can create this for you).",
                action_type=ActionType.auto_patch,
            ))

    return findings, files_scanned


def count_by_category(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category.value] = counts.get(f.category.value, 0) + 1
    return counts
