# Architecture

```
┌────────────────────────┐        HTTP (JSON)        ┌──────────────────────────┐
│   frontend (Next.js)    │  ───────────────────────▶ │   backend (FastAPI)       │
│  app/  lib/api.ts       │  ◀───────────────────────  │  app/main.py (endpoints)  │
│  6 cockpit screens      │                            │                          │
└────────────────────────┘                            │  services/  (deterministic)
                                                       │   scanner, scoring, repo, │
                                                       │   patch, dockerfile,      │
                                                       │   smoke_test, benchmark,  │
                                                       │   validation, report      │
                                                       │                          │
                                                       │  agents/   (Fireworks AI) │
                                                       │   migration_planner,      │
                                                       │   patch_explainer,        │
                                                       │   failure_diagnoser,      │
                                                       │   report_writer           │
                                                       └──────────┬───────────────┘
                                                                  │
                                        ┌─────────────────────────┼────────────────────┐
                                        ▼                         ▼                    ▼
                                 Fireworks AI API        backend/runs/<id>/     AMD Dev Cloud
                                 (reasoning only)         (artifacts + state)    (validation)
```

## Design rules (don't break these — they're what makes the project credible)

1. **The scanner is deterministic. The LLM only explains.** Every finding, score,
   and artifact comes from plain Python in `services/`. Fireworks agents in
   `agents/` take that factual output and reason about it. An LLM must never be
   the thing that "detects a CUDA string" — otherwise findings aren't trustworthy.

2. **Agents degrade gracefully.** `fireworks_service.complete()` returns `None`
   with no API key or on any error, and every agent has a deterministic fallback.
   The full demo runs offline. Add an API key to make the prose smarter.

3. **`torch.cuda` is not NVIDIA.** On ROCm, PyTorch exposes AMD GPUs through the
   `torch.cuda` namespace. We do NOT rewrite `"cuda"` → `"rocm"`. We remove
   NVIDIA-only *assumptions* (base images, `nvidia-smi`, `+cuXXX` wheels) and add
   graceful availability checks. This nuance is the difference between a real tool
   and a naive find-and-replace.

4. **State is a file.** Each run is `backend/runs/<id>/` with a `state.json` plus
   generated artifacts. No database. Swap for SQLite only if you need history.

## Runtime

- `docker compose up --build` → backend on `:8000`, frontend on `:3000`.
- Backend Python 3.12 / FastAPI / uvicorn. Frontend Next.js 14 (standalone).
