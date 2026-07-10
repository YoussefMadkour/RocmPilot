"""AMD/ROCm validation. Three modes:

  replay      : load a saved SUCCESSFUL AMD run (demo-safe). Labeled clearly in UI.
  replay_fail : load a saved FAILED AMD run — shows the Failure Diagnoser in action.
  live        : execute build + smoke test + benchmark in the environment (stub).

OWNER: Youssef (backend). Live mode is a stub for now — replay modes are what the
demo runs on. Capture a REAL validation_log.txt from AMD Developer Cloud and drop
it into app/fixtures/ so replay reflects a genuine run.

On any FAILED result, the Failure Diagnoser agent analyses the log and its output
is attached as `result.diagnosis` for the Validate screen's failure panel.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.agents import failure_diagnoser
from app.config import FIXTURES_DIR, settings
from app.models import ValidationResult, ValidationStatus
from app.services import run_store

FAIL_LOG_NAME = "validation_log_fail.txt"


def _read_text(path: Path, fallback: str) -> str:
    # Always decode UTF-8 — the fixtures contain an em dash; the platform default
    # (cp1252 on Windows) renders it as mojibake in the UI.
    return path.read_text(encoding="utf-8") if path.exists() else fallback


def _replay() -> ValidationResult:
    log_path = Path(settings.amd_validation_log_path)
    if not log_path.is_absolute():
        log_path = FIXTURES_DIR / log_path.name
    logs = _read_text(log_path, "No saved validation log found.\n")

    bench_path = FIXTURES_DIR / "benchmark.json"
    bench = json.loads(bench_path.read_text(encoding="utf-8")) if bench_path.exists() else {}

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


def _replay_fail() -> ValidationResult:
    logs = _read_text(FIXTURES_DIR / FAIL_LOG_NAME, "No saved failure log found.\n")
    return ValidationResult(
        status=ValidationStatus.failed,
        mode="replay_fail",
        rocm_detected=True,
        hip_available=True,
        gpu_name="AMD Instinct MI300X",
        smoke_test_passed=False,
        benchmark_passed=False,
        logs=logs,
    )


def _live(run_id: str) -> ValidationResult:
    # TODO(Youssef): build Dockerfile.rocm, run smoke_test.py + benchmark.py,
    # parse stdout into a ValidationResult. Falls back to replay for now.
    return _replay()


def validate(run_id: str) -> ValidationResult:
    if settings.validation_mode == "live":
        result = _live(run_id)
    elif settings.validation_mode == "replay_fail":
        result = _replay_fail()
    else:
        result = _replay()

    # A failed run is exactly when the Failure Diagnoser earns its keep.
    if result.status == ValidationStatus.failed:
        result.diagnosis = failure_diagnoser.diagnose(result.logs)

    run_store.write_artifact(run_id, "validation_log.txt", result.logs)
    return result
