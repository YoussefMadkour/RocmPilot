"""Pydantic models shared across the API. This IS the frontend/backend contract.

Keep these in sync with docs/API_CONTRACT.md. When you change a field here,
update the contract doc and tell whoever owns the other side of the wire.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ActionType(str, Enum):
    auto_patch = "auto_patch"
    suggested_patch = "suggested_patch"
    manual_review = "manual_review"
    info = "info"


class FindingCategory(str, Enum):
    cuda_hardcoding = "cuda_hardcoding"
    nvidia_docker = "nvidia_docker"
    cuda_dependency = "cuda_dependency"
    manual_blocker = "manual_blocker"
    missing_artifact = "missing_artifact"


class RunStage(str, Enum):
    created = "created"
    scanned = "scanned"
    planned = "planned"
    patched = "patched"
    validated = "validated"
    reported = "reported"


class ValidationStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    not_run = "not_run"


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class CreateRunRequest(BaseModel):
    repo_url: Optional[str] = None
    use_sample: bool = False


# --------------------------------------------------------------------------- #
# Core domain objects
# --------------------------------------------------------------------------- #
class Finding(BaseModel):
    file_path: str
    line_number: int
    severity: Severity
    category: FindingCategory
    matched_text: str
    explanation: str
    recommended_action: str
    action_type: ActionType


class ScoreBreakdown(BaseModel):
    """Before / after / final readiness scores, 0-100."""
    before: int = Field(ge=0, le=100)
    after_planned: Optional[int] = Field(default=None, ge=0, le=100)
    final: Optional[int] = Field(default=None, ge=0, le=100)


class PlanAction(BaseModel):
    title: str
    detail: str
    severity: Severity
    action_type: ActionType


class MigrationPlan(BaseModel):
    summary: str
    actions: list[PlanAction]
    manual_blockers: list[str] = []


class Critique(BaseModel):
    """The Critic agent's review of a migration plan against the raw findings."""
    approved: bool
    issues: list[str] = []
    notes: str = ""


class AgentEvent(BaseModel):
    """One step in the multi-agent trace — powers the Plan screen's activity timeline."""
    agent: str            # "orchestrator" | "planner" | "critic"
    message: str
    ok: bool = True       # False = this step flagged a problem
    model: Optional[str] = None   # which model ran this step (short name), if any


class KnowledgeChunk(BaseModel):
    """A retrieved ROCm/HIP migration doc snippet (RAG grounding for the agents)."""
    text: str
    source: str          # url or doc title
    score: float = 0.0   # retrieval similarity


class Artifact(BaseModel):
    name: str            # e.g. "Dockerfile.rocm"
    path: str            # relative to the run dir
    language: str        # "dockerfile" | "python" | "diff" | "json" | "markdown"


class ValidationResult(BaseModel):
    status: ValidationStatus
    mode: Literal["live", "replay", "replay_fail"]
    rocm_detected: bool = False
    hip_available: bool = False
    pytorch_rocm_build: Optional[str] = None
    gpu_name: Optional[str] = None
    smoke_test_passed: bool = False
    benchmark_passed: bool = False
    inference_latency_ms: Optional[float] = None
    logs: str = ""
    diagnosis: Optional[str] = None        # Failure Diagnoser output; set only on failure
    diagnosis_model: Optional[str] = None  # which model produced the diagnosis


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
class RunSummary(BaseModel):
    run_id: str
    stage: RunStage
    source: str          # repo url or "sample:<name>"
    score: ScoreBreakdown


class ScanResponse(BaseModel):
    run_id: str
    findings: list[Finding]
    findings_by_category: dict[str, int]
    files_scanned: int
    score: ScoreBreakdown


class RunDetail(BaseModel):
    """Read-only snapshot of a run — lets the UI hydrate any screen without re-running a step."""
    run_id: str
    stage: RunStage
    source: str
    score: ScoreBreakdown
    findings: Optional[list[Finding]] = None
    findings_by_category: Optional[dict[str, int]] = None
    files_scanned: Optional[int] = None
    plan: Optional[MigrationPlan] = None
    critique: Optional[Critique] = None
    trace: Optional[list[AgentEvent]] = None
    artifacts: Optional[list[Artifact]] = None
    explanations: Optional[list[PatchExplanation]] = None
    validation: Optional[ValidationResult] = None


class PlanResponse(BaseModel):
    run_id: str
    plan: MigrationPlan
    critique: Critique
    trace: list[AgentEvent] = []


class PatchExplanation(BaseModel):
    """A grounded, per-file explanation of what a generated patch changed."""
    file_path: str
    line_number: int          # first changed line, for anchoring in the diff viewer
    original: str             # the exact changed lines, before
    patched: str              # the exact changed lines, after
    explanation: str          # why it's safe for AMD/ROCm


class PatchResponse(BaseModel):
    run_id: str
    artifacts: list[Artifact]
    explanations: list[PatchExplanation] = []
    score: ScoreBreakdown


class ValidationResponse(BaseModel):
    run_id: str
    validation: ValidationResult
    score: ScoreBreakdown


class ReportResponse(BaseModel):
    run_id: str
    markdown: str
    score: ScoreBreakdown
    artifacts: list[Artifact]
    model: Optional[str] = None   # which model wrote the report
