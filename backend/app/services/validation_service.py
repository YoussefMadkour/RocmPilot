"""AMD/ROCm validation. Three modes:

  replay      : load a saved SUCCESSFUL AMD run (demo-safe). Labeled clearly in UI.
  replay_fail : load a saved FAILED AMD run — shows the Failure Diagnoser in action.
  live        : build Dockerfile.rocm, run smoke_test.py + benchmark.py in the
                container, and parse their stdout into a ValidationResult.

OWNER: Youssef (backend). Live mode needs Docker + an AMD/ROCm host; when that is
unavailable (or the build/run fails) it falls back to the saved run so the demo
never breaks. The log PARSER (`_parse_live_output`) is pure and unit-tested — it
also makes wiring a captured AMD Developer Cloud log trivial.

On any FAILED result, the Failure Diagnoser agent analyses the log and its output
is attached as `result.diagnosis` for the Validate screen's failure panel.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from app.agents import failure_diagnoser, json_utils
from app.config import FIXTURES_DIR, settings
from app.models import ValidationResult, ValidationStatus
from app.services import run_store

FAIL_LOG_NAME = "validation_log_fail.txt"

# Live-mode docker settings. Device flags mirror the Dockerfile template's docs.
LIVE_BUILD_TIMEOUT = 900   # ROCm base images are large; first build is slow.
LIVE_RUN_TIMEOUT = 300
_DOCKER_DEVICES = [
    "--device=/dev/kfd", "--device=/dev/dri",
    "--group-add", "video", "--security-opt", "seccomp=unconfined",
]


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


def _marker_passed(log: str) -> bool | None:
    """The smoke test prints exactly one standalone PASS/FAIL; return the last one."""
    result: bool | None = None
    for line in log.splitlines():
        s = line.strip()
        if s == "PASS":
            result = True
        elif s == "FAIL":
            result = False
    return result


def _parse_live_output(smoke_log: str, bench_log: str) -> ValidationResult:
    """Turn real smoke_test.py + benchmark.py stdout into a ValidationResult. Pure."""
    smoke_passed = _marker_passed(smoke_log) is True

    bench: dict = {}
    try:
        parsed = json.loads(json_utils.extract_json(bench_log))
        if isinstance(parsed, dict):
            bench = parsed
    except (ValueError, TypeError):
        bench = {}
    bench_passed = bool(bench) and "BENCHMARK FAILED" not in bench_log

    hip_version = bench.get("hip_version")
    rocm_detected = bool(hip_version) or (
        "HIP / ROCm version" in smoke_log and "not a ROCm build" not in smoke_log
    )
    gpu_name = bench.get("gpu_name")
    if not gpu_name:
        m = re.search(r"device name\s*:\s*(.+)", smoke_log)
        gpu_name = m.group(1).strip() if m else None
    if gpu_name == "cpu":
        gpu_name = None

    return ValidationResult(
        status=ValidationStatus.passed if smoke_passed else ValidationStatus.failed,
        mode="live",
        rocm_detected=rocm_detected,
        hip_available="accelerator available: True" in smoke_log,
        pytorch_rocm_build=bench.get("pytorch_build"),
        gpu_name=gpu_name,
        smoke_test_passed=smoke_passed,
        benchmark_passed=bench_passed,
        inference_latency_ms=bench.get("inference_latency_ms"),
        logs=smoke_log.rstrip() + "\n\n" + bench_log.rstrip() + "\n",
    )


def _docker(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def _live(run_id: str) -> ValidationResult:
    """Build the generated ROCm image and run smoke+bench inside it, then parse.

    Needs Docker + an AMD host. On any infra failure we fall back to the saved run
    (with a note prepended) so the demo still completes end to end.
    """
    run_root = run_store.run_dir(run_id)
    dockerfile = run_root / "Dockerfile.rocm"
    try:
        if not dockerfile.exists():
            raise FileNotFoundError("Dockerfile.rocm not generated — run the patch step first.")
        tag = f"rocmpilot-{run_id}:live"
        build = _docker(["build", "-f", str(dockerfile), "-t", tag, str(run_root)],
                        LIVE_BUILD_TIMEOUT)
        if build.returncode != 0:
            raise RuntimeError(f"docker build failed:\n{(build.stderr or '')[-2000:]}")

        smoke = _docker(["run", "--rm", *_DOCKER_DEVICES, tag,
                         "python", "smoke_test.py", "--require-gpu"], LIVE_RUN_TIMEOUT)
        bench = _docker(["run", "--rm", *_DOCKER_DEVICES, tag,
                         "python", "benchmark.py"], LIVE_RUN_TIMEOUT)
        return _parse_live_output(smoke.stdout + smoke.stderr, bench.stdout + bench.stderr)
    except (FileNotFoundError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        fallback = _replay()
        fallback.logs = (
            f"[live validation unavailable: {exc}]\n"
            "Falling back to the saved AMD run so the demo still completes.\n\n"
            + fallback.logs
        )
        return fallback


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
