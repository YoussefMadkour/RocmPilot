# RocmPilot Studio

**The migration command center that takes a CUDA-first repo to an AMD-ready,
validated deployment — in minutes.**

> Point it at a repository URL. It returns an honest AMD-readiness verdict, a
> prioritized migration plan, safe auto-patches, a ready-to-run ROCm container, a
> real validation on AMD hardware, and a before→after readiness score — end to end.

📄 **Read [`PITCH.md`](PITCH.md) for the story, the tech decisions, and the results.**

Built for the **AMD Developer Hackathon: ACT II**, Track 3 (Unicorn). A
**multi-model agent orchestra** (all AMD-hosted via **Fireworks AI**) plus a
ROCm/HIP **knowledge base (RAG)**, validated on **AMD Developer Cloud (Radeon gfx1100 / MI300-class)**.
Fully containerized.

---

## The problem

Most AI projects are built CUDA-first. Moving them to AMD GPUs means fighting
hardcoded `cuda` device logic, `nvidia/cuda` base images, CUDA-only wheels, missing
ROCm setup, and confusing errors — with no clear signal on whether a repo can even
run on AMD. RocmPilot removes that friction.

## What it does

1. **Scan** a repo (GitHub URL or the bundled sample) — deterministic detection of
   CUDA/NVIDIA blockers with file, line, severity, and category, plus a
   **kernel-risk classifier** for the hard tail: warp/wavefront-64 hazards
   (`__shfl`, `__ballot`, `warpSize`), WMMA tensor cores, CUTLASS, texture memory,
   and CUDA libraries mapped to their ROCm twins (cuBLAS→hipBLAS, NCCL→RCCL, …).
2. **Plan** — a multi-agent orchestra drafts a prioritized plan, then a **second,
   different model critiques it** before you see it (independent review).
3. **Patch** — generates `patch.diff`, `Dockerfile.rocm`, `smoke_test.py`,
   `benchmark.py`, each patch explained in plain English from the real diff.
4. **Validate** — runs (or replays a labeled saved) AMD/ROCm smoke test +
   benchmark on the AMD GPU; on failure a **research agent** returns a *cited* fix.
5. **Report** — an honest ROCm readiness score (before → after → validated) and an
   exportable report.

## Where AMD & Fireworks show up

- **AMD/ROCm:** generated ROCm Dockerfile, smoke test, benchmark, and a real
  validation run on AMD Developer Cloud (Radeon gfx1100 / MI300-class) (replayable for demo safety,
  always labeled). The kernel-risk classifier speaks AMD (wavefront64, rocWMMA,
  Composable Kernel, hipBLAS/MIOpen/rocFFT/RCCL).
- **Fireworks AI (multi-model, all AMD-hosted):** DeepSeek-v4-pro plans, GLM-5.2
  critiques and writes, Kimi-k2.6 researches failures, `nomic-embed-text` powers
  the RAG knowledge base. Deterministic detection stays in Python — the LLM only
  reasons and explains, always with a deterministic fallback. See
  `docs/ARCHITECTURE.md`.

## What it does **not** do

Not a full CUDA→ROCm compiler. It targets common PyTorch / Hugging Face inference
repos. Custom CUDA kernels (`.cu`/`.cuh`), native extensions, and unsupported
operators are **flagged for manual review**, not auto-solved.

---

## Quick start

```bash
cp .env.example .env          # add FIREWORKS_API_KEY (optional — runs without it)
docker compose up --build     # backend :8000, frontend :3000
```
Open http://localhost:3000 and click **Scan sample CUDA-first repo**.

### Run the pieces without Docker

Backend:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload           # http://localhost:8000/docs
```
Frontend:
```bash
cd frontend
npm install
npm run dev                             # http://localhost:3000
```

## Environment variables

| Var | Purpose | Default |
|-----|---------|---------|
| `FIREWORKS_API_KEY` | Enables the reasoning agents + embeddings (falls back offline if unset) | — |
| `FIREWORKS_MODEL` | Default Fireworks model id | deepseek-v4-pro |
| `PLANNER/CRITIC/RESEARCH/REPORT/EXPLAINER_MODEL` | Per-agent model overrides | see `config.py` |
| `FIREWORKS_EMBEDDING_MODEL` | Embedding model for RAG | nomic-embed-text-v1.5 |
| `QDRANT_URL` / `QDRANT_API_KEY` | ROCm/HIP knowledge base (RAG). Blank → agents run without retrieval | — |
| `TAVILY_API_KEY` | Optional web research for the self-heal agent | — |
| `VALIDATION_MODE` | `replay` / `replay_fail` (demo modes) or `live` | replay |
| `AMD_VALIDATION_LOG_PATH` | Saved AMD run for replay mode | fixtures/validation_log.txt |
| `GITHUB_TOKEN` | Clone private repos (optional) | — |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL | http://localhost:8000 |

> After setting `FIREWORKS_API_KEY` + Qdrant, build the knowledge base once:
> `cd backend && python -m app.knowledge.ingest`

## Repository layout

```
backend/    FastAPI app — services/ (deterministic) + agents/ (Fireworks)
backend/tests/       pytest suite (scanner, scoring, run store, artifacts.zip)
frontend/   Next.js cockpit UI + typed API client (lib/api.ts)
frontend/DESIGN.md   design direction ("engine-bay cockpit") — keep screens consistent
docs/       ARCHITECTURE, API_CONTRACT, DEMO_SCRIPT
PROJECT_TRACKER.md   phases, acceptance criteria, who-owns-what
FOR_JITHENDRA.md     onboarding for the frontend/backend split
FOR_YOUSSEF.md       status handoff + open [Y] work + improvement ideas
```

## Tests

```bash
cd backend
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pytest                        # 152 tests, all deterministic (no network, no LLM)
```

## Team

- **Youssef** — backend intelligence: scanner, scoring, Fireworks agents, prompts,
  validation, product/demo direction.
- **Jithendra** — frontend cockpit (Next.js + design), plus scoped backend work to
  ramp up. See `PROJECT_TRACKER.md`.

## Limitations & roadmap

See `PROJECT_TRACKER.md` → *Limitations & future work*. Short version: inference
repos only in v1; live AMD validation is scaffolded (replay-first); no auto PR yet.
