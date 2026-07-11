# RocmPilot Studio

**AI migration & validation cockpit for AMD GPU readiness.**

[![CI](https://github.com/YoussefMadkour/RocmPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/YoussefMadkour/RocmPilot/actions/workflows/ci.yml)

> Most AI repos are CUDA-first. RocmPilot Studio takes a CUDA-first PyTorch repo
> and makes it AMD-ready — scan blockers, generate safe patches and a ROCm
> container, validate on AMD, and score readiness before → after.

Built for the **AMD Developer Hackathon: ACT II**, Track 3 (Unicorn). Uses the
**Fireworks AI API** for the reasoning agents and **AMD Developer Cloud / ROCm**
for validation. Fully containerized; runs completely offline with zero API keys.

---

## The problem

Most AI projects are built CUDA-first. Moving them to AMD GPUs means fighting
hardcoded `cuda` device logic, `nvidia/cuda` base images, CUDA-only wheels
(`+cu121`), missing ROCm setup, and confusing errors — with no clear signal on
whether a repo can even run on AMD. RocmPilot removes that friction and replaces
guesswork with a measured, evidence-backed readiness score.

## The six-stage flight

Every run moves through the same enforced pipeline (calling a stage out of order
returns `409`):

| # | Stage | What happens | What you get |
|---|-------|--------------|--------------|
| 01 | **Intake** | Point it at a GitHub URL or the bundled sample; the repo is cloned (hardened: scheme/host allowlist, SSRF guard, size/time limits, token redaction) | a run id |
| 02 | **Scan** | Deterministic scanner (21+ regex patterns, per-line deduped, zero LLM) finds CUDA/NVIDIA blockers | findings with file, line, severity, category, recommended fix + the **before** score |
| 03 | **Plan** | The Orchestrator runs the **Migration Planner**, then a **Critic** agent reviews the plan against the raw findings | prioritized plan, critique (approved / issues), agent-activity trace |
| 04 | **Patch** | Conservative, idempotent transforms guard `torch.device("cuda")`, `.cuda()`, `.to("cuda")`; ROCm artifacts are generated from templates | `patch.diff`, `Dockerfile.rocm`, `smoke_test.py`, `benchmark.py` + per-change **Patch Explainer** notes |
| 05 | **Validate** | Runs (or replays a saved) AMD/ROCm smoke test + benchmark; on failure, the **Failure Diagnoser** analyzes the logs | pass/fail, GPU name, HIP/ROCm status, latency + the **final** score |
| 06 | **Report** | The **Report Writer** turns everything into a judge-ready Markdown report | `readiness_report.md`, downloadable alone or in `artifacts.zip` |

## The cockpit

| | |
|---|---|
| ![Scan — findings table with severity/category filters](docs/screenshots/02-scan.png) | ![Plan — multi-agent plan with Critic review](docs/screenshots/03-plan.png) |
| **Scan** — deterministic findings, filterable | **Plan** — Planner + Critic, real agent trace |
| ![Validate — AMD validation card with replay badge](docs/screenshots/04-validate.png) | ![Report — score journey and readiness report](docs/screenshots/05-report.png) |
| **Validate** — MI300X evidence, honestly labeled | **Report** — 37 → 72 → 86 and the exportable debrief |

---

## Quick start

### Docker (verified from a fresh clone)

```bash
git clone https://github.com/YoussefMadkour/RocmPilot.git && cd RocmPilot
docker compose up --build     # backend :8000, frontend :3000
```

Open http://localhost:3000 and click **Scan the bundled CUDA-first sample repo**.
No `.env` needed: with no `FIREWORKS_API_KEY` every agent falls back to a
deterministic response, and the full flow completes end to end in seconds.
Add keys later (`cp .env.example .env`) to make the prose smarter.

### Without Docker

Backend:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload           # http://localhost:8000/docs
```

Frontend (Node 22+):
```bash
cd frontend
npm install
npm run dev                             # http://localhost:3000
```

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                        # 124 tests, all deterministic (no network, no LLM)
```

---

## Architecture

```
┌─────────────────────────┐      HTTP (JSON)      ┌───────────────────────────────┐
│  frontend (Next.js 16)  │ ───────────────────▶  │  backend (FastAPI, py3.12)    │
│  app/   6 cockpit       │ ◀───────────────────  │  app/main.py — 10 endpoints   │
│  lib/api.ts typed client│                       │                               │
└─────────────────────────┘                       │  services/  (deterministic)   │
                                                  │   scanner · scoring · repo    │
                                                  │   patch · dockerfile · smoke  │
                                                  │   benchmark · validation      │
                                                  │   report · run_store          │
                                                  │                               │
                                                  │  agents/    (Fireworks AI)    │
                                                  │   orchestrator → planner      │
                                                  │              → critic         │
                                                  │   patch_explainer             │
                                                  │   failure_diagnoser           │
                                                  │   report_writer               │
                                                  │                               │
                                                  │  knowledge/ (optional RAG)    │
                                                  │   Qdrant + Fireworks embeds   │
                                                  └──────────┬────────────────────┘
                                                             │
                                     ┌───────────────────────┼──────────────────────┐
                                     ▼                       ▼                      ▼
                              Fireworks AI API       backend/runs/<id>/       AMD Dev Cloud
                              (reasoning only)       state.json + artifacts   (validation)
```

**State is a file.** Each run lives at `backend/runs/<id>/` — a `state.json`
carrying stage, findings, plan, critique, trace, artifacts, and scores, plus the
generated artifact files and the cloned `source/`. No database; every endpoint is
independently callable and the frontend can resume any run.

### Design rules (what makes it credible)

1. **The scanner is deterministic. The LLM only explains.** Every finding, score,
   and artifact comes from plain Python in `services/`. Fireworks agents reason
   *about* that factual output — an LLM is never the thing that "detects a CUDA
   string", so findings are reproducible and trustworthy.
2. **Agents degrade gracefully.** `fireworks_service.complete()` returns `None`
   with no API key or on any error, and **every** agent has a deterministic
   fallback. The full demo runs offline; keys only upgrade the prose.
3. **`torch.cuda` is not NVIDIA.** On ROCm, PyTorch exposes AMD GPUs through the
   `torch.cuda` namespace. RocmPilot does **not** rewrite `"cuda"` → `"rocm"`; it
   removes NVIDIA-only *assumptions* (base images, `nvidia-smi`, `+cuXXX` wheels)
   and adds graceful availability checks. This nuance is the difference between a
   real tool and a naive find-and-replace.
4. **Honesty is part of the UI.** A replayed validation always shows the ember
   **"Saved AMD run"** badge, and the readiness score is calibrated to reality,
   not demo drama (see below).

## The agent system

Six cooperating agents, all Fireworks-powered, all with deterministic fallbacks:

| Agent | Stage | Job |
|-------|-------|-----|
| **Orchestrator** | Plan | Code-first coordinator: runs Planner → Critic, records an `AgentEvent` trace the UI renders as the activity timeline |
| **Migration Planner** | Plan | Turns raw findings into a prioritized plan (JSON-validity hardened: fenced/prose recovery, enum guards) |
| **Critic** | Plan | Reviews the plan *against the raw findings* — approves or raises issues; also runs a deterministic cross-check with no key |
| **Patch Explainer** | Patch | For each real changed snippet: why the change is safe on AMD/ROCm (before/after grounded, never invented) |
| **Failure Diagnoser** | Validate | On failure only: root cause, suggested fix, confidence, next command (try `VALIDATION_MODE=replay_fail`) |
| **Report Writer** | Report | Six-section judge-ready Markdown with honest replay labeling |

**Optional RAG knowledge base:** a curated ROCm/HIP/HIPIFY corpus embedded via
Fireworks and stored in Qdrant grounds the agents in migration documentation.
Fully optional and fallback-safe — with no `QDRANT_URL` every retrieval is a
no-op. Set the vars and run `python -m app.knowledge.ingest` to light it up.

## The readiness score (0–100, honest by design)

Deterministic, count-sensitive, calibrated against real repos:

- Start at 100. Subtract a **blocker penalty** — weighted by category and
  severity, sensitive to finding *count* with diminishing returns (twelve
  hardcoded devices hurt more than three, but not 4× more).
- Subtract an **unvalidated penalty (−12)**: a repo never proven on AMD can't
  score 100, no matter how clean.
- **After patches** the score is capped at **72** — patched is not proven.
- **Validation** on AMD lifts the cap: **+10** for a passing smoke test, **+4**
  for a passing benchmark; a failed run costs **−25**.

The bundled sample repo tells the demo story **37 → 72 → 86**. Real repos score
honestly (locked by tests so weights can't silently drift):

| Tier | Repo | before | Why |
|------|------|-------:|-----|
| 1 — ROCm-transparent apps | nanoGPT ~67 · Real-ESRGAN ~65 · YOLOv5 ~55 | high | ROCm maps `'cuda'` transparently; the job is containerize → validate |
| 2 — custom-kernel libraries | detectron2 ~12 · mmcv ~16 · flash-attention ~17 | low | hand-written CUDA kernels; flagged `manual_blocker` for HIPIFY, not auto-solved |

Full tier list and rationale: [docs/BENCHMARK_REPOS.md](docs/BENCHMARK_REPOS.md).

## Validation modes

Set `VALIDATION_MODE`:

| Mode | What it does | When |
|------|--------------|------|
| `replay` *(default)* | Loads a saved successful AMD Developer Cloud run (MI300X, ROCm 6.2) — demo-safe, always labeled **"Saved AMD run"** in the UI | demos, CI |
| `replay_fail` | Loads a saved *failing* run so the Failure Diagnoser's analysis can be shown in seconds | demoing the diagnoser |
| `live` | Builds `Dockerfile.rocm`, runs `smoke_test.py` + `benchmark.py`, parses their PASS/FAIL markers into the result; falls back to replay if Docker/AMD hardware is unavailable | on an AMD host |

## API at a glance

Full wire contract with JSON shapes: [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

```
GET  /api/health                       liveness
GET  /api/runs                         list runs, newest first
POST /api/runs                         create run (repo URL or sample)
POST /api/runs/{id}/scan               deterministic scan + before/after score
POST /api/runs/{id}/plan               orchestrated plan + critique + agent trace
POST /api/runs/{id}/patch              patch.diff + ROCm artifacts + explanations
POST /api/runs/{id}/validate           AMD validation (replay/live) + final score
GET  /api/runs/{id}/report             judge-ready Markdown report
GET  /api/runs/{id}/artifacts          list artifacts
GET  /api/runs/{id}/artifacts/{name}   one artifact's content
GET  /api/runs/{id}/artifacts.zip      everything as one zip
```

## The frontend cockpit

Six screens on a persistent **flight-check rail** — numbered stages with LED
status dots driven by the real persisted run state (the numbering is honest: the
backend enforces the order). Design system — red-warmed "engine-bay" dark, AMD
signal red for interactive elements only, Chakra Petch HUD headings, IBM Plex
body/mono — is documented in [frontend/DESIGN.md](frontend/DESIGN.md); keep new
UI consistent with it. Responsive to 375px; findings table stress-tested against
real repos with a sticky header.

## Repository layout

```
backend/
  app/main.py            FastAPI endpoints (order mirrors the demo flow)
  app/models.py          Pydantic models — THE frontend/backend contract
  app/services/          deterministic: scanner, scoring, repo, patch,
                         dockerfile, smoke_test, benchmark, validation,
                         report, run_store
  app/agents/            Fireworks: orchestrator, migration_planner, critic,
                         patch_explainer, failure_diagnoser, report_writer,
                         prompts, json_utils
  app/knowledge/         optional RAG corpus + ingest (Qdrant)
  app/templates/         Dockerfile.rocm / smoke_test.py / benchmark.py
  app/fixtures/          saved AMD validation logs (pass + fail) + benchmark
  tests/                 124 pytest cases — scanner, scoring bands, patches,
                         agents, repo hardening, validation parser, zip
frontend/
  app/                   Next.js 16 App Router — 6 cockpit screens
  components/            flight-check rail, badges
  lib/api.ts             typed API client (mirrors models.py)
  DESIGN.md              design direction — read before touching UI
docs/
  ARCHITECTURE.md        diagram + design rules
  API_CONTRACT.md        wire contract (change models.py + api.ts + this together)
  BENCHMARK_REPOS.md     calibration repos + tier list
  DEMO_SCRIPT.md         the 3-minute demo
  screenshots/           README gallery
PROJECT_TRACKER.md       phases, owners, acceptance criteria
FOR_JITHENDRA.md         onboarding (frontend + backend ramp-up split)
FOR_YOUSSEF.md           status handoff + improvement roadmap
```

## Testing & CI

- `backend/tests` — 124 deterministic cases: every scanner pattern, scoring
  property tests + locked score bands (so weight changes can't silently drift the
  calibrated curve), patch idempotency, agent JSON recovery, clone hardening,
  validation log parsing, artifacts.zip.
- **GitHub Actions** ([ci.yml](.github/workflows/ci.yml)) runs pytest (Python
  3.12) and the production frontend build (Node 22) on every push/PR to `dev`
  and `main`.

## Environment variables

Everything is optional — blank values mean deterministic fallbacks, never crashes.

| Var | Purpose | Default |
|-----|---------|---------|
| `FIREWORKS_API_KEY` | Enables the reasoning agents | — (offline fallbacks) |
| `FIREWORKS_MODEL` | Chat model id | `llama-v3p1-70b-instruct` |
| `FIREWORKS_EMBEDDING_MODEL` | Embedding model for the knowledge base | `nomic-embed-text-v1.5` |
| `QDRANT_URL` / `QDRANT_API_KEY` | RAG knowledge base (no-op if blank) | — |
| `KNOWLEDGE_COLLECTION` / `KNOWLEDGE_TOP_K` | RAG collection + retrieval depth | `rocm_migration_docs` / 5 |
| `TAVILY_API_KEY` | Reserved for the planned self-heal agent's web research | — |
| `VALIDATION_MODE` | `replay` (default) · `replay_fail` · `live` | `replay` |
| `AMD_VALIDATION_LOG_PATH` | Saved AMD run for replay | bundled fixture |
| `GITHUB_TOKEN` | Clone private repos (redacted from errors/logs) | — |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL | `http://localhost:8000` |

## Team & workflow

- **Youssef** ([@YoussefMadkour](https://github.com/YoussefMadkour)) — backend
  intelligence: scanner core, scoring, the six agents, prompts, validation,
  product/demo direction.
- **Jithendra** ([@jithendra-10](https://github.com/jithendra-10)) — the entire
  frontend cockpit (Next.js + design system), plus scoped backend work: scanner
  patterns, ROCm templates, list/zip endpoints, the test harness, Docker/CI.

Git workflow: `main` is protected, `dev` is integration. Every change goes on a
`feat/*` branch and lands via PR into `dev`; `dev` → `main` ships as a release PR.
One PR = one thing. API-shape changes touch `models.py` + `lib/api.ts` +
`docs/API_CONTRACT.md` in the same PR.

## What it does **not** do (yet)

Not a full CUDA→ROCm compiler. v1 targets common PyTorch / Hugging Face
**inference** repos. Custom CUDA kernels (`.cu`/`.cuh`), native extensions, and
unsupported operators are **flagged for manual review** with HIPIFY guidance —
not auto-solved.

**Roadmap:** live validation exercised on a real AMD host · self-heal agent
(diagnose → re-patch → re-validate loop) · automatic GitHub PR with `patch.diff` ·
Tier 2 kernel repos (HIPIFY-assisted porting) · SQLite run history · streaming
agent output.
