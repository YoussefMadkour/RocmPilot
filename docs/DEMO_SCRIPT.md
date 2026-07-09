# 3-Minute Demo Script

One-liner to open with:
> "Most AI repos are CUDA-first. RocmPilot Studio makes them AMD-ready."

| Time | Screen | What you say / show |
|------|--------|---------------------|
| 0:00–0:20 | Intake | "This is a real CUDA-first PyTorch repo — nanoGPT / YOLOv5. Hardcoded `cuda`, an NVIDIA base image, CUDA-only wheels." Paste the GitHub URL. |
| 0:20–0:50 | Scan | Hit scan. "RocmPilot's deterministic scanner found N blockers across M files, with file, line, severity, and category." Point at the **before score ≈ 37**. |
| 0:50–1:20 | Plan | "A Fireworks-powered Migration Planner turns those raw findings into a prioritized plan — what's auto-fixable vs. what needs a human." |
| 1:20–1:50 | Patch | "It generates a `patch.diff`, a ROCm Dockerfile, a smoke test, and a benchmark." Show the diff + `Dockerfile.rocm`. Projected score jumps to **72**. |
| 1:50–2:30 | Validate | "We validate on AMD — ROCm detected, HIP available, smoke test passed on an MI300X, 12.4 ms latency." Show the **Saved AMD run** badge honestly. |
| 2:30–3:00 | Report | "Readiness went **37 → 86**. Here's the exportable report a team uses to move onto AMD." Download `readiness_report.md`. |

## Rules for a clean demo
- Pre-create one run before you present as a fallback (the replay validation makes
  this safe and repeatable).
- Never hide replay mode — judges respect the honesty, and the design is built for
  real AMD validation.
- If Fireworks is slow/down, the deterministic fallback still produces a good plan
  and report. Don't panic.

## Showcase repos (verified CUDA-first — see PROJECT_TRACKER.md for the full list)
- `https://github.com/karpathy/nanoGPT` — primary; small, famous, `device = 'cuda'`.
- `https://github.com/ultralytics/yolov5` — CUDA Docker base + `--gpus all`; visual.
- `https://github.com/xinntao/Real-ESRGAN` — fp16 GPU image upscaling; very visual.
