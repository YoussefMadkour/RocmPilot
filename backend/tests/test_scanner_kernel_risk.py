"""Tests for the kernel-level hazard classifier — the hard '20%' hipify can't do.

This is our answer to pattern-aware warp/wavefront + CUDA-library detection.
"""
from __future__ import annotations

import pytest

from app.models import ActionType, FindingCategory, Severity
from app.services import scanner_service


def _findings_for(line: str, name: str = "kernel.cu"):
    return [f for f in _scan_text(line, name)]


def _scan_text(line: str, name: str):
    """Run the pattern list over a single line (mirrors scanner_service.scan)."""
    from app.models import Finding
    out = []
    for pat in scanner_service.PATTERNS:
        if pat.regex.search(line):
            out.append(Finding(
                file_path=name, line_number=1, severity=pat.severity, category=pat.category,
                matched_text=line, explanation=pat.explanation,
                recommended_action=pat.recommended_action, action_type=pat.action_type))
    return scanner_service._dedupe(out)


@pytest.mark.parametrize("line,vocab", [
    ("int v = __shfl_down_sync(0xffffffff, val, 16);", "wavefront64"),
    ("unsigned m = __ballot_sync(0xffffffff, pred);", "wavefront"),
    ("if (threadIdx.x < warpSize) {", "64 on AMD"),
    ("auto block = cooperative_groups::this_thread_block();", "Cooperative Groups"),
    ("nvcuda::wmma::fragment<...> a;", "rocWMMA"),
    ("cudaTextureObject_t tex;", "texture"),
    ("using cutlass::gemm::device::Gemm;", "Composable Kernel"),
])
def test_kernel_hazards_flagged_as_manual_blocker(line, vocab):
    findings = _scan_text(line, "kernel.cu")
    assert any(f.category == FindingCategory.manual_blocker
               and f.action_type == ActionType.manual_review for f in findings), line
    assert any(vocab.lower() in f.recommended_action.lower() for f in findings), line


@pytest.mark.parametrize("line,vocab", [
    ("status = cublasSgemm(handle, ...);", "hipblas"),
    ("cudnnConvolutionForward(h, ...);", "miopen"),
    ("cufftPlan1d(&plan, n, CUFFT_C2C, 1);", "rocfft"),
    ("ncclAllReduce(sbuf, rbuf, n, ncclFloat, ncclSum, comm, stream);", "rccl"),
    ("thrust::sort(d.begin(), d.end());", "rocthrust"),
])
def test_cuda_libraries_mapped_to_rocm(line, vocab):
    findings = _scan_text(line, "kernel.cu")
    assert any(f.category == FindingCategory.cuda_dependency for f in findings), line
    assert any(vocab.lower() in f.recommended_action.lower() for f in findings), line


def test_torch_backends_cudnn_is_not_a_cudnn_library_hit():
    """The PyTorch flag must NOT be misclassified as a cuDNN C-API dependency."""
    findings = _scan_text("torch.backends.cudnn.benchmark = True", "train.py")
    assert len(findings) == 1
    assert findings[0].category == FindingCategory.cuda_hardcoding


def test_warp_hazards_detected_in_real_tier2_repo():
    """flash-attention is warp-heavy; if cached locally, we should catch hazards."""
    from pathlib import Path
    repo = Path("/Users/youssefmadkour/Desktop/RocmPilot/benchmark_repos/flash-attention")
    if not repo.exists():
        pytest.skip("benchmark repo not cached locally")
    findings, _ = scanner_service.scan(repo)
    actions = " ".join(f.recommended_action.lower() for f in findings)
    assert "wavefront" in actions or "rocwmma" in actions or "composable kernel" in actions
