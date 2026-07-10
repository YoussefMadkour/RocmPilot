# API Contract

The frontend and backend meet **only** here. If you change a shape, change it in
`backend/app/models.py`, in `frontend/lib/api.ts`, and in this doc — in the same PR.

Base URL: `http://localhost:8000` (set via `NEXT_PUBLIC_API_BASE_URL`).

All bodies are JSON. Errors return `{ "detail": "<message>" }` with a 4xx/5xx
status; the frontend client throws that message.

## Flow

```
GET  /api/runs                 -> list all runs, newest first (RunSummary[])
POST /api/runs                 -> create a run (sample or repo URL)
POST /api/runs/{id}/scan       -> deterministic scan + before/after score
POST /api/runs/{id}/plan       -> orchestrated plan (Planner + Critic) + agent trace
POST /api/runs/{id}/patch      -> generate patch.diff + ROCm artifacts
POST /api/runs/{id}/validate   -> AMD validation (replay or live) + final score
GET  /api/runs/{id}/report     -> final Markdown readiness report
GET  /api/runs/{id}/artifacts  -> list generated artifacts
GET  /api/runs/{id}/artifacts/{name} -> one artifact's content
GET  /api/runs/{id}/artifacts.zip -> all artifacts as a zip download (409 before patch)
GET  /api/health               -> {"status":"ok"}
```

Steps are ordered: `plan`/`patch` require a prior `scan`; `report` requires
`plan` + `patch` + `validate`. Calling out of order returns `409`.

## Key shapes (see `models.py` for the full source of truth)

**ScoreBreakdown** — drives every score card.
```json
{ "before": 37, "after_planned": 72, "final": 86 }
```
`after_planned` and `final` are `null` until their step runs.

**Finding** — one scanner hit; rows in the Scan table.
```json
{
  "file_path": "app.py", "line_number": 6, "severity": "medium",
  "category": "cuda_hardcoding", "matched_text": "device = torch.device(\"cuda\")",
  "explanation": "...", "recommended_action": "...", "action_type": "auto_patch"
}
```
`severity`: low | medium | high | critical.
`action_type`: auto_patch | suggested_patch | manual_review | info.

**Plan response** — `POST /plan` returns `{run_id, plan, critique, trace}`. The plan
is produced by an Orchestrator that runs the Planner then a Critic (which reviews
the plan against the raw findings); `trace` drives the Plan screen's agent-activity
timeline.
```json
{
  "plan": { "summary": "...", "actions": [ ... ], "manual_blockers": [ ... ] },
  "critique": { "approved": true, "issues": [], "notes": "LLM + deterministic review." },
  "trace": [
    { "agent": "orchestrator", "message": "Coordinating migration plan ...", "ok": true },
    { "agent": "planner", "message": "Drafted 5 actions ...", "ok": true },
    { "agent": "critic", "message": "Reviewed the plan — approved ...", "ok": true }
  ]
}
```
`agent`: orchestrator | planner | critic. `ok: false` marks a step that flagged a problem.

**PatchExplanation** — a grounded, per-file note in the `POST /patch` response
(`{run_id, artifacts, explanations, score}`); powers the Patch screen's diff notes.
```json
{
  "file_path": "model.py", "line_number": 42,
  "original": "device = torch.device(\"cuda\")",
  "patched": "device = torch.device(\"cuda\" if torch.cuda.is_available() else \"cpu\")",
  "explanation": "In model.py, the hardcoded CUDA device is replaced with an availability-guarded lookup ..."
}
```

**ValidationResult** — the AMD validation card.
```json
{
  "status": "passed", "mode": "replay", "rocm_detected": true, "hip_available": true,
  "pytorch_rocm_build": "2.4.0+rocm6.2", "gpu_name": "AMD Instinct MI300X",
  "smoke_test_passed": true, "benchmark_passed": true,
  "inference_latency_ms": 12.4, "logs": "...", "diagnosis": null
}
```
`mode`: replay | replay_fail | live (set via `VALIDATION_MODE`). Always show the
`mode` badge — a `replay`/`replay_fail` run must be labeled "Saved AMD run".
`diagnosis` is the Failure Diagnoser agent's analysis; non-null only when
`status == "failed"` (render it in the failure panel).
