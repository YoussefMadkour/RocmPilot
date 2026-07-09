"""Assemble and persist the final readiness report.

OWNER: Youssef (backend). Thin orchestration over the report_writer agent.
"""
from __future__ import annotations

from app.agents import report_writer
from app.models import Artifact, MigrationPlan, ScoreBreakdown, ValidationResult
from app.services import run_store


def build(
    run_id: str,
    source: str,
    plan: MigrationPlan,
    artifacts: list[Artifact],
    validation: ValidationResult,
    score: ScoreBreakdown,
) -> str:
    markdown = report_writer.write(source, plan, artifacts, validation, score)
    run_store.write_artifact(run_id, "readiness_report.md", markdown)
    return markdown
