# RocmPilot Studio

**AI migration & validation cockpit for AMD GPU readiness.**

> Most AI repos are CUDA-first. RocmPilot Studio helps developers take a CUDA-first
> PyTorch inference repo and turn it into an AMD/ROCm-ready container — by scanning
> blockers, generating safe patches, validating on AMD infrastructure, and
> producing a ROCm readiness score.

Built for the **AMD Developer Hackathon: ACT II**, Track 3 (Unicorn). Uses the
**Fireworks AI API** for reasoning agents and **AMD Developer Cloud / ROCm** for
validation. Fully containerized.

---

## The problem

Most AI projects are built CUDA-first. Moving them to AMD GPUs means fighting
hardcoded `cuda` device logic, `nvidia/cuda` base images, CUDA-only wheels, missing
ROCm setup, and confusing errors — with no clear signal on whether a repo can even
run on AMD. RocmPilot removes that friction.

## What it does

1. **Scan** a repo (GitHub URL or the bundled sample) — deterministic detection of
   CUDA/NVIDIA blockers with file, line, severity, and category.
2. **Plan** — a Fireworks agent turns findings into a prioritized migration plan.
3. **Patch** — generates `patch.diff`, `Dockerfile.rocm`, `smoke_test.py`,
   `benchmark.py`.
4. **Validate** — runs (or replays a saved) AMD/ROCm smoke test + benchmark.
5. **Report** — a ROCm readiness score (before → after) and an exportable report.

## Where AMD & Fireworks show up

- **AMD/ROCm:** generated ROCm Dockerfile, smoke test, benchmark, and a real
  validation run on AMD Developer Cloud (replayable for demo safety, always
  labeled). See the AMD validation card in the UI.
- **Fireworks AI:** powers the four reasoning agents (planner, patch explainer,
  failure diagnoser, report writer). Deterministic detection stays in Python — the
  LLM only reasons and explains. See `docs/ARCHITECTURE.md`.

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
| `FIREWORKS_API_KEY` | Enables the reasoning agents (falls back offline if unset) | — |
| `FIREWORKS_MODEL` | Fireworks model id | llama-v3p1-70b-instruct |
| `VALIDATION_MODE` | `replay` (demo-safe) or `live` | replay |
| `AMD_VALIDATION_LOG_PATH` | Saved AMD run for replay mode | fixtures/validation_log.txt |
| `GITHUB_TOKEN` | Clone private repos (optional) | — |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL | http://localhost:8000 |

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
pytest                        # 32 tests, all deterministic (no network, no LLM)
```

## Team

- **Youssef** — backend intelligence: scanner, scoring, Fireworks agents, prompts,
  validation, product/demo direction.
- **Jithendra** — frontend cockpit (Next.js + design), plus scoped backend work to
  ramp up. See `PROJECT_TRACKER.md`.

## Limitations & roadmap

See `PROJECT_TRACKER.md` → *Limitations & future work*. Short version: inference
repos only in v1; live AMD validation is scaffolded (replay-first); no auto PR yet.
