"""RocmPilot Studio — FastAPI backend.

Endpoint order mirrors the demo flow:
  create -> scan -> plan -> patch -> validate -> report

State is persisted per-run in backend/runs/<id>/state.json so the frontend can
call the steps independently. See docs/API_CONTRACT.md for the wire contract.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents import migration_planner
from app.models import (
    Artifact,
    CreateRunRequest,
    Finding,
    MigrationPlan,
    PatchResponse,
    PlanResponse,
    ReportResponse,
    RunStage,
    RunSummary,
    ScanResponse,
    ScoreBreakdown,
    ValidationResponse,
    ValidationResult,
)
from app.services import (
    patch_service,
    repo_service,
    report_service,
    run_store,
    scanner_service,
    scoring_service,
    validation_service,
)

app = FastAPI(title="RocmPilot Studio API", version="0.1.0")

# The frontend runs on a different origin (localhost:3000). Wide-open CORS is fine
# for a hackathon; tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_run(run_id: str) -> dict:
    if not run_store.exists(run_id):
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run_store.load_state(run_id)


def _score_from_state(state: dict) -> ScoreBreakdown:
    return ScoreBreakdown(**state.get("score", {"before": 0}))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# GET /api/runs — list all runs, newest first
# --------------------------------------------------------------------------- #
@app.get("/api/runs", response_model=list[RunSummary])
def list_runs() -> list[RunSummary]:
    return [
        RunSummary(
            run_id=state["run_id"],
            stage=RunStage(state.get("stage", "created")),
            source=state.get("source", "unknown"),
            score=ScoreBreakdown(**state.get("score", {"before": 0})),
        )
        for state in run_store.list_runs()
    ]


# --------------------------------------------------------------------------- #
# POST /api/runs — create a run from a sample or a repo URL
# --------------------------------------------------------------------------- #
@app.post("/api/runs", response_model=RunSummary)
def create_run(req: CreateRunRequest) -> RunSummary:
    if req.use_sample:
        source = f"sample:{repo_service.DEFAULT_SAMPLE}"
    elif req.repo_url:
        source = req.repo_url
    else:
        raise HTTPException(status_code=400, detail="Provide repo_url or set use_sample=true")

    run_id = run_store.create(source)
    try:
        if req.use_sample:
            repo_service.load_sample(run_id)
        else:
            repo_service.clone_repo(run_id, req.repo_url)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001 — surface any ingest failure to the client
        raise HTTPException(status_code=400, detail=f"Failed to load source: {exc}") from exc

    run_store.update_state(run_id, stage=RunStage.created.value, score={"before": 0})
    return RunSummary(
        run_id=run_id, stage=RunStage.created, source=source, score=ScoreBreakdown(before=0)
    )


# --------------------------------------------------------------------------- #
# POST /api/runs/{id}/scan — deterministic scanner
# --------------------------------------------------------------------------- #
@app.post("/api/runs/{run_id}/scan", response_model=ScanResponse)
def scan_run(run_id: str) -> ScanResponse:
    _require_run(run_id)
    findings, files_scanned = scanner_service.scan(run_store.source_dir(run_id))

    before = scoring_service.score_before(findings)
    after_planned = scoring_service.score_after_planned(findings)
    score = ScoreBreakdown(before=before, after_planned=after_planned)

    run_store.update_state(
        run_id,
        stage=RunStage.scanned.value,
        findings=[f.model_dump(mode="json") for f in findings],
        files_scanned=files_scanned,
        score=score.model_dump(mode="json"),
    )
    return ScanResponse(
        run_id=run_id,
        findings=findings,
        findings_by_category=scanner_service.count_by_category(findings),
        files_scanned=files_scanned,
        score=score,
    )


# --------------------------------------------------------------------------- #
# POST /api/runs/{id}/plan — Fireworks migration planner
# --------------------------------------------------------------------------- #
@app.post("/api/runs/{run_id}/plan", response_model=PlanResponse)
def plan_run(run_id: str) -> PlanResponse:
    state = _require_run(run_id)
    if "findings" not in state:
        raise HTTPException(status_code=409, detail="Run must be scanned before planning")

    findings = [Finding.model_validate(f) for f in state["findings"]]
    plan = migration_planner.plan(findings)
    run_store.update_state(run_id, stage=RunStage.planned.value, plan=plan.model_dump(mode="json"))
    return PlanResponse(run_id=run_id, plan=plan)


# --------------------------------------------------------------------------- #
# POST /api/runs/{id}/patch — generate diff + ROCm artifacts
# --------------------------------------------------------------------------- #
@app.post("/api/runs/{run_id}/patch", response_model=PatchResponse)
def patch_run(run_id: str) -> PatchResponse:
    state = _require_run(run_id)
    if "findings" not in state:
        raise HTTPException(status_code=409, detail="Run must be scanned before patching")

    artifacts = patch_service.generate(run_id)
    score = _score_from_state(state)  # after_planned already computed at scan time
    run_store.update_state(
        run_id,
        stage=RunStage.patched.value,
        artifacts=[a.model_dump(mode="json") for a in artifacts],
    )
    return PatchResponse(run_id=run_id, artifacts=artifacts, score=score)


# --------------------------------------------------------------------------- #
# POST /api/runs/{id}/validate — AMD validation (live or replay)
# --------------------------------------------------------------------------- #
@app.post("/api/runs/{run_id}/validate", response_model=ValidationResponse)
def validate_run(run_id: str) -> ValidationResponse:
    state = _require_run(run_id)
    validation = validation_service.validate(run_id)

    base = _score_from_state(state)
    final = scoring_service.score_final(base.after_planned or base.before, validation)
    score = ScoreBreakdown(before=base.before, after_planned=base.after_planned, final=final)

    run_store.update_state(
        run_id,
        stage=RunStage.validated.value,
        validation=validation.model_dump(mode="json"),
        score=score.model_dump(mode="json"),
    )
    return ValidationResponse(run_id=run_id, validation=validation, score=score)


# --------------------------------------------------------------------------- #
# GET /api/runs/{id}/report — final readiness report
# --------------------------------------------------------------------------- #
@app.get("/api/runs/{run_id}/report", response_model=ReportResponse)
def get_report(run_id: str) -> ReportResponse:
    state = _require_run(run_id)
    for key in ("plan", "artifacts", "validation"):
        if key not in state:
            raise HTTPException(status_code=409, detail=f"Run missing '{key}'; complete earlier steps first")

    plan = MigrationPlan.model_validate(state["plan"])
    artifacts = [Artifact.model_validate(a) for a in state["artifacts"]]
    validation = ValidationResult.model_validate(state["validation"])
    score = _score_from_state(state)

    markdown = report_service.build(run_id, state["source"], plan, artifacts, validation, score)
    run_store.update_state(run_id, stage=RunStage.reported.value)
    return ReportResponse(run_id=run_id, markdown=markdown, score=score, artifacts=artifacts)


# --------------------------------------------------------------------------- #
# GET /api/runs/{id}/artifacts — list generated artifacts
# --------------------------------------------------------------------------- #
@app.get("/api/runs/{run_id}/artifacts")
def get_artifacts(run_id: str) -> dict:
    state = _require_run(run_id)
    return {"run_id": run_id, "artifacts": state.get("artifacts", [])}


@app.get("/api/runs/{run_id}/artifacts/{name}")
def get_artifact_content(run_id: str, name: str) -> dict:
    _require_run(run_id)
    content = run_store.read_artifact(run_id, name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Artifact {name} not found")
    return {"run_id": run_id, "name": name, "content": content}
