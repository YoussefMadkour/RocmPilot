# RocmPilot Studio
### The migration command center that takes a CUDA-first repo to an AMD-ready, validated deployment — in minutes.

*AMD Developer Hackathon: ACT II — Track 3 (Unicorn)*

---

## The problem

AMD's MI300X wins on price/performance. The thing standing between an enterprise
and that hardware isn't silicon — it's **software migration friction**. A typical
AI codebase is CUDA-first from top to bottom: hardcoded `cuda` device logic,
`nvidia/cuda` base images, CUDA-pinned wheels, NVIDIA-only libraries, and — the
part everyone fears — hand-written CUDA kernels with warp-level assumptions.

Tooling like `hipify` translates the *easy* majority of that automatically. But
two things are still missing, and they're exactly what stalls real migrations:

1. **Nobody can tell you, up front, how ready a whole codebase actually is** — or
   *where* the hard work hides.
2. **The hard tail** — warp/wavefront divergence, tensor-core intrinsics, template
   GEMM libraries — gets discovered one painful compile error at a time.

Teams stay on CUDA because the *uncertainty* is expensive, not just the work.

## What RocmPilot is

**Point it at a repository URL. It returns an honest AMD-readiness verdict, a
prioritized migration plan, safe auto-patches, a ready-to-run ROCm container, a
real validation on AMD hardware, and a before→after readiness score — end to end,
in one cockpit.**

It's not a single-purpose translator. It's the **command center** for the whole
migration: triage → plan → fix the easy 80% → precisely scope the hard 20% →
containerize → validate on AMD → score → report.

## How it works

```
Repo URL ─▶ SCAN ─▶ PLAN ─▶ PATCH ─▶ VALIDATE ─▶ REPORT
          (deterministic  (multi-agent  (auto-fix +   (real MI300X   (readiness
           + kernel-risk    orchestra +   ROCm         run, or        score +
           classifier)      RAG)          container)   labeled replay) export)
```

- **Scan** — a deterministic engine (no LLM, so it never hallucinates a finding)
  detects CUDA/NVIDIA blockers with file, line, severity and category. A dedicated
  **kernel-risk classifier** flags the hard tail with AMD vocabulary: warp shuffles
  and ballots that assume 32-lane warps (AMD wavefronts are **64**), `warpSize`
  hazards, cooperative groups, WMMA tensor cores → rocWMMA/MFMA, texture memory,
  CUTLASS → Composable Kernel, and every CUDA library mapped to its ROCm twin
  (cuBLAS→hipBLAS, cuDNN→MIOpen, cuFFT→rocFFT, NCCL→RCCL, Thrust→rocThrust). At
  **repository scale**, not one kernel at a time.
- **Plan** — a **multi-model agent orchestra** turns raw findings into a grouped,
  prioritized plan, then a **second, different model reviews it** before you ever
  see it.
- **Patch** — generates a `patch.diff` (safe device-handling rewrites), a
  `Dockerfile.rocm`, a ROCm smoke test, and a benchmark — each patch explained in
  plain English, grounded in the exact changed lines.
- **Validate** — builds and runs the smoke test + benchmark on **real AMD (MI300X)
  hardware**; when a run fails, a **research agent** investigates and returns a
  *cited* root cause and fix.
- **Report** — a judge-ready Markdown report and a single readiness number that
  actually means something.

## The tech, and why we chose it

| Decision | Why |
|---|---|
| **Deterministic scan + scoring core; the LLM only reasons** | Findings and scores must be trustworthy and reproducible. The model explains and plans; it never invents a blocker or a number. Also means the whole product runs offline. |
| **Multi-model orchestra, best-fit per role** (all AMD-hosted via Fireworks): DeepSeek-v4-pro plans, **GLM-5.2 critiques**, Kimi-k2.6 researches, nomic-embed retrieves | Different jobs reward different models. Crucially, the **Critic runs on a *different* model than the Planner** — an independent reviewer catches the correlated mistakes a same-model self-check would miss. |
| **Honest, blocker-weighted readiness score** | ROCm maps the `torch.cuda` namespace transparently, so a clean PyTorch repo genuinely *is* close to ready — and we say so. The score tracks real porting difficulty (custom kernels, NVIDIA base images, CUDA wheels dominate), so it's defensible to an engineer who knows ROCm. A number you can trust beats a dramatic one. |
| **RAG over a curated ROCm/HIP knowledge base** (Qdrant + embeddings) | The agents cite authoritative ROCm/HIPIFY/wavefront guidance instead of guessing. Retrieval is sharp on the topics that matter (a warp-shuffle query returns the warp-shuffle doc at 0.82 similarity). Diagnoses come with sources. |
| **Fallback-safe at every layer** | No API key → deterministic plan. No knowledge base → agents still run. No AMD host → clearly-labeled saved run. The demo *cannot* break, and honesty is never sacrificed for a live call. |

## Results

- **Real AMD validation** on MI300X via AMD Developer Cloud (smoke test + benchmark;
  replay is always labeled as a saved run — never faked).
- **Honest readiness across a spectrum** we measured on real repos:

  | Repo | "before" | Why |
  |---|---:|---|
  | flash-attention | ~17 | ~2,900 kernel hazards + 123 CUDA-library calls flagged |
  | detectron2 | ~12 | custom kernels across every category |
  | bundled sample | **37 → 72 → 86** | the full journey, headline demo |
  | YOLOv5 | ~55 | NVIDIA Docker + device hardcoding |
  | nanoGPT | ~67 | clean PyTorch — genuinely close, and we say so |

- **Live agent quality:** on a failed warp-reduction kernel, the research agent
  correctly identified the 32→64 wavefront divergence, recommended a 64-lane
  rewrite (or rocPRIM/hipCUB), and cited its ROCm sources — high confidence, ~26s.
- **152 automated tests**, deterministic and offline; the live path verified end
  to end.

## Why it wins

RocmPilot answers the question enterprises actually start with — *"can my codebase
move to AMD, how hard is it, and can you get it running?"* — and then does the
getting-it-running. It combines **repo-scale triage**, a **precisely-scoped hard
20%**, a **multi-model, RAG-grounded agent orchestra**, **one-stop ROCm
packaging**, and **real MI300X validation** into a single, honest cockpit.

It doesn't just port code. It removes the *uncertainty* that keeps enterprises on
CUDA — which is the actual blocker to AMD adoption.

> **From a repo URL to an AMD-ready, validated deployment — with a readiness score
> you can trust.**
