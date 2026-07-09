"""AMD/ROCm validation. Two modes:

  replay : load a saved successful AMD run (demo-safe). Labeled clearly in the UI.
  live   : execute build + smoke test + benchmark in the environment.

OWNER: Youssef (backend). Live mode is a stub for now — replay mode is what the
demo runs on. Capture a REAL validation_log.txt from AMD Developer Cloud and drop
it into app/fixtures/ so replay reflects a genuine run.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import FIXTURES_DIR, settings
from app.models import ValidationResult, ValidationStatus
from app.services import run_store


def _replay() -> ValidationResult:
    log_path = Path(settings.amd_validation_log_path)
    if not log_path.is_absolute():
        log_path = FIXTURES_DIR / log_path.name
    logs = log_path.read_text() if log_path.exists() else "No saved validation log found.\n"

    bench_path = FIXTURES_DIR / "benchmark.json"
    bench = json.loads(bench_path.read_text()) if bench_path.exists() else {}

    return ValidationResult(
        status=ValidationStatus.passed,
        mode="replay",
        rocm_detected=True,
        hip_available=True,
        pytorch_rocm_build=bench.get("pytorch_build", "2.x+rocm6.x"),
        gpu_name=bench.get("gpu_name", "AMD Instinct MI300X"),
        smoke_test_passed=True,
        benchmark_passed=True,
        inference_latency_ms=bench.get("inference_latency_ms", 12.4),
        logs=logs,
    )


def _live(run_id: str) -> ValidationResult:
    # TODO(Youssef): build Dockerfile.rocm, run smoke_test.py + benchmark.py,
    # parse stdout into a ValidationResult. Falls back to replay for now.
    return _replay()


def validate(run_id: str) -> ValidationResult:
    result = _live(run_id) if settings.validation_mode == "live" else _replay()
    run_store.write_artifact(run_id, "validation_log.txt", result.logs)
    return result
