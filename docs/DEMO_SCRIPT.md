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
| 1:55–2:35 | Validate | "We validate on **real AMD GPU — Radeon gfx1100 on AMD Developer Cloud.** ROCm detected, HIP available, smoke test passed, latency measured." The **saved-run badge** is always honest. *(Optional wow:* flip to a failed run — "when it breaks, a research agent grounded in a ROCm knowledge base returns a **cited** root cause and fix.") |
| 2:35–3:00 | Report | "Readiness went **before → 72 → 86**, and here's the exportable report — the artifact a team uses to commit to AMD." Download `readiness_report.md` (it's in `artifacts.zip` too). |

## The differentiators to land (say them as positive facts)
- **Whole repo, one verdict** — from a URL to an AMD-ready, validated deployment.
- **Honest score** — ROCm maps `torch.cuda` transparently, so clean repos score
  high and we *say so*; the number tracks real difficulty. Trust beats drama.
- **The hard 20%, named** — wavefront64, `__shfl`/ballot, WMMA→rocWMMA,
  CUTLASS→Composable Kernel, cuBLAS→hipBLAS — at repository scale.
- **Multi-model + RAG** — best-fit model per role, an independent-model critic, and
  cited diagnoses from a ROCm/HIP knowledge base.

## ⚠️ Pre-warm the run (do this before you present)
Measured cold latency with live models: **scan ~0s · plan ~40s · patch ~10s ·
validate ~0s · report ~13s**. The reasoning models are worth it, but **40s of
Plan spinner will kill a live demo.**

The fix is built in: **pre-warm one run, then present off the cache.**
1. Before you go on: create the demo run and click through all six screens once
   (this runs every agent and caches the output).
2. On stage, open the run by its URL (or from **Recent runs** on Intake) and walk
   the screens — each hydrates instantly from `GET /api/runs/{id}` (no re-running).
3. Only run a stage *live* if you specifically want to show the agents working
   (e.g. a fresh Scan, which is instant anyway).

## Shot list (what's on screen at each beat)
- **Scan:** honest before-score; category filter chips; the **kernel-risk callout**
  ("N kernel-level hazards hipify can't auto-port") → click *Show them* to reveal
  the warp/wavefront/CUTLASS findings.
- **Plan:** agent summary; prioritized actions; **Critic review** badge
  (approved/issues); **Agent activity** timeline with **model badges**
  (`deepseek-v4-pro` on planner, `glm-5p2` on critic).
- **Patch:** diff viewer + artifact tabs + **Patch Explainer** per-change notes.
- **Validate:** AMD card, **"Saved AMD run · replay"** badge, GPU/latency stats.
  *(Optional wow:* set `VALIDATION_MODE=replay_fail` on a second run — the failure
  panel shows a **cited diagnosis with a `kimi-k2p6` badge`.)*
- **Report:** before→72→86 journey; rendered report with a **`glm-5p2`** badge;
  Download report / Download all (.zip).

## Rules for a clean demo
- Never hide replay mode — judges respect the honesty, and the pipeline runs real
  AMD hardware when a live host is attached (see `docs/AMD_SETUP.md`).
- If Fireworks is slow/down, every agent has a deterministic fallback — the plan,
  patches, diagnosis, and report still render. Don't panic.
- Have the pre-warmed run's URL on a sticky note; a second `replay_fail` run ready
  for the diagnosis moment.

## Showcase repos
- `https://github.com/karpathy/nanoGPT` — primary; clean, famous, believable jump.
- `https://github.com/ultralytics/yolov5` — NVIDIA Docker base + `--gpus all`; visual.
- `https://github.com/xinntao/Real-ESRGAN` — fp16 GPU upscaling; very visual.
- *(Hard-mode backup:* a kernel-heavy repo lights up the warp/library classifier at
  scale — dramatic proof the hard 20% is actually detected.)*
