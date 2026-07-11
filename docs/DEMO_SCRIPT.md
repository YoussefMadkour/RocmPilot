# 3-Minute Demo Script

**Open with the altitude, not a feature:**
> "Moving an AI codebase to AMD isn't one problem — it's a hundred small ones, and
> nobody can tell you up front how hard it'll be. RocmPilot answers that: point it
> at a repo, and it triages, patches, containerizes, validates on real AMD, and
> scores readiness — end to end."

| Time | Screen | What you say / show |
|------|--------|---------------------|
| 0:00–0:20 | Intake | "A real CUDA-first PyTorch repo — nanoGPT. Hardcoded `cuda`, an NVIDIA base image, CUDA-only wheels." Paste the GitHub URL, create the run. |
| 0:20–0:55 | Scan | "Our deterministic scanner — no LLM, so it can't hallucinate a finding — flags N blockers with file, line, severity, category. And it names the **hard 20%** most tooling misses: warp/wavefront-64 hazards, tensor-core intrinsics, and CUDA libraries mapped to their ROCm twins." Point at the **honest before score** + category breakdown. |
| 0:55–1:25 | Plan | "A multi-model agent orchestra — all AMD-hosted on Fireworks. DeepSeek plans; then **a different model, GLM, critiques the plan** before you see it — an independent reviewer, not a self-check." Show the **agent-activity timeline** and manual-blockers list. |
| 1:25–1:55 | Patch | "It generates a `patch.diff`, a ROCm Dockerfile, a smoke test, and a benchmark — each patch explained from the real changed lines." Show the diff + `Dockerfile.rocm`. Projected score jumps. |
| 1:55–2:35 | Validate | "We validate on **real AMD — MI300X on AMD Developer Cloud.** ROCm detected, HIP available, smoke test passed, latency measured." The **saved-run badge** is always honest. *(Optional wow:* flip to a failed run — "when it breaks, a research agent grounded in a ROCm knowledge base returns a **cited** root cause and fix.") |
| 2:35–3:00 | Report | "Readiness went **before → 72 → 86**, and here's the exportable report — the artifact a team uses to commit to AMD." Download `readiness_report.md` (it's in `artifacts.zip` too). |

## The differentiators to land (say them as positive facts)
- **Whole repo, one verdict** — from a URL to an AMD-ready, validated deployment.
- **Honest score** — ROCm maps `torch.cuda` transparently, so clean repos score
  high and we *say so*; the number tracks real difficulty. Trust beats drama.
- **The hard 20%, named** — wavefront64, `__shfl`/ballot, WMMA→rocWMMA,
  CUTLASS→Composable Kernel, cuBLAS→hipBLAS — at repository scale.
- **Multi-model + RAG** — best-fit model per role, an independent-model critic, and
  cited diagnoses from a ROCm/HIP knowledge base.

## Rules for a clean demo
- Pre-create one run before presenting as a fallback (replay validation makes this
  safe and repeatable).
- Never hide replay mode — judges respect the honesty, and the pipeline runs real
  AMD hardware when a live host is attached.
- If Fireworks is slow/down, every agent has a deterministic fallback — the plan,
  patches, diagnosis, and report still render. Don't panic.
- Reasoning models take a few seconds to think; have a pre-warmed run ready if you
  want the plan instant on stage.

## Showcase repos
- `https://github.com/karpathy/nanoGPT` — primary; clean, famous, believable jump.
- `https://github.com/ultralytics/yolov5` — NVIDIA Docker base + `--gpus all`; visual.
- `https://github.com/xinntao/Real-ESRGAN` — fp16 GPU upscaling; very visual.
- *(Hard-mode backup:* a kernel-heavy repo lights up the warp/library classifier at
  scale — dramatic proof the hard 20% is actually detected.)*
