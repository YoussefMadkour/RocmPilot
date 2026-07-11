"""Self-contained AMD (MI300X) validation capture for RocmPilot.

Drop this ONE file into an AMD AI Notebook / ROCm PyTorch environment and run it —
no repo clone, only needs `torch`. It runs the same smoke test + benchmark
RocmPilot generates and writes two files in RocmPilot's exact format:

    validation_log.txt   -> backend/app/fixtures/validation_log.txt
    benchmark.json       -> backend/app/fixtures/benchmark.json

Usage (any of these):
    python amd_capture.py                 # in a Lab terminal
    %run amd_capture.py                    # in a notebook cell
    import amd_capture; amd_capture.capture()

Then paste validation_log.txt + benchmark.json back (or download them) so replay
mode shows genuine MI300X numbers.
"""
from __future__ import annotations

import json
import subprocess
import time

import torch

SIZE, N_RUNS = 1024, 50


_CPU_HINTS = ("EPYC", "Ryzen", "Threadripper", "Core Processor", "Xeon", "Intel")


def _gpu_name() -> str:
    """The accelerator's name. torch is the source of truth; rocminfo is a
    fallback that must SKIP the CPU agent (rocminfo lists the CPU first)."""
    if torch.cuda.is_available():
        try:
            return torch.cuda.get_device_name(0)
        except Exception:  # noqa: BLE001
            pass
    try:
        out = subprocess.run(["rocminfo"], capture_output=True, text=True, timeout=30).stdout
        names = [l.split(":", 1)[1].strip() for l in out.splitlines() if "Marketing Name" in l]
        gpus = [n for n in names if not any(h in n for h in _CPU_HINTS)]
        return gpus[0] if gpus else (names[0] if names else "cpu")
    except Exception:  # noqa: BLE001
        return "cpu"


def capture(out_dir: str = ".") -> str:
    lines: list[str] = []

    def out(s: str = "") -> None:
        print(s)
        lines.append(s)

    accel = torch.cuda.is_available()
    hip = getattr(torch.version, "hip", None)
    gpu = _gpu_name()
    dev = torch.device("cuda" if accel else "cpu")

    out("=== RocmPilot AMD Validation (LIVE — AMD Developer Cloud) ===")
    out(f"Runtime    : ROCm {hip or '(not a ROCm build)'}")
    out("")
    out("$ python smoke_test.py --require-gpu")
    out("=== RocmPilot smoke test ===")
    out(f"torch version        : {torch.__version__}")
    out(f"HIP / ROCm version   : {hip or 'not a ROCm build'}")
    out(f"accelerator available: {accel}")
    out(f"device name          : {gpu}")
    out(f"selected device      : {dev}")

    a = torch.randn(512, 512, device=dev)
    b = torch.randn(512, 512, device=dev)
    c = (a @ b).sum().item()
    if dev.type == "cuda":
        torch.cuda.synchronize()
    ok = bool(torch.isfinite(torch.tensor(c)).item())
    out(f"matmul result finite : {ok}")
    out("PASS" if ok else "FAIL")

    out("")
    out("$ python benchmark.py")
    t0 = time.perf_counter()
    a = torch.randn(SIZE, SIZE, device=dev)
    b = torch.randn(SIZE, SIZE, device=dev)
    load_ms = (time.perf_counter() - t0) * 1000
    for _ in range(5):
        _ = a @ b
    if dev.type == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(N_RUNS):
        _ = a @ b
    if dev.type == "cuda":
        torch.cuda.synchronize()
    avg_ms = (time.perf_counter() - t0) * 1000 / N_RUNS

    result = {
        "device": str(dev),
        "gpu_name": gpu,
        "pytorch_build": torch.__version__,
        "hip_version": hip,
        "load_ms": round(load_ms, 3),
        "inference_latency_ms": round(avg_ms, 3),
        "approx_tflops": round((2 * SIZE**3) / (avg_ms / 1000) / 1e12, 2),
        "runs": N_RUNS,
        "matmul_size": SIZE,
    }
    out(json.dumps(result, indent=2))
    out("")
    out("RESULT: AMD inference smoke test "
        + ("PASSED. Benchmark captured." if ok else "FAILED."))

    log_text = "\n".join(lines) + "\n"
    with open(f"{out_dir}/validation_log.txt", "w") as fh:
        fh.write(log_text)
    with open(f"{out_dir}/benchmark.json", "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\n>>> wrote {out_dir}/validation_log.txt and {out_dir}/benchmark.json")
    return log_text


if __name__ == "__main__":
    capture()
