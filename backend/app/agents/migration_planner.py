"""Migration Planner agent (Fireworks-powered, deterministic fallback).

OWNER: Youssef (AI). Turns raw scan findings into a prioritized, explained plan.
"""
from __future__ import annotations

import json

from app.agents import prompts
from app.models import ActionType, Finding, MigrationPlan, PlanAction, Severity
from app.services import fireworks_service

_SEVERITY_ORDER = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}


def _fallback(findings: list[Finding]) -> MigrationPlan:
    """Deterministic plan so the demo works with no API key."""
    actions: list[PlanAction] = []
    seen: set[tuple[str, str]] = set()
    for f in sorted(findings, key=lambda x: _SEVERITY_ORDER[x.severity]):
        key = (f.category.value, f.recommended_action)
        if key in seen:
            continue
        seen.add(key)
        actions.append(PlanAction(
            title=f"{f.category.value.replace('_', ' ').title()}",
            detail=f.recommended_action,
            severity=f.severity,
            action_type=f.action_type,
        ))
    blockers = [
        f"{f.file_path}:{f.line_number} — {f.explanation}"
        for f in findings if f.action_type == ActionType.manual_review
    ]
    summary = (
        f"Detected {len(findings)} CUDA/NVIDIA signals. "
        f"{len(blockers)} require manual review; the rest are auto- or suggested-patchable."
    )
    return MigrationPlan(summary=summary, actions=actions, manual_blockers=blockers)


def plan(findings: list[Finding]) -> MigrationPlan:
    findings_json = json.dumps([f.model_dump(mode="json") for f in findings], indent=2)
    raw = fireworks_service.complete(
        system=prompts.MIGRATION_PLANNER,
        user=(
            "Scan findings:\n" + findings_json +
            '\n\nReturn JSON: {"summary": str, "actions": '
            '[{"title","detail","severity","action_type"}], "manual_blockers": [str]}.'
        ),
        response_format={"type": "json_object"},
    )
    if not raw:
        return _fallback(findings)
    try:
        return MigrationPlan.model_validate_json(raw)
    except ValueError:
        # Model returned malformed JSON — never break the demo.
        return _fallback(findings)
