"""Plan Critic agent — a second agent that reviews the Migration Planner's output.

OWNER: Youssef (AI). Reviews a plan against the raw findings and returns a
structured Critique. Uses Fireworks when available, but ALWAYS runs deterministic
grounding checks too, so even offline the Critic catches unfaithful plans (invented
blockers, dropped severe findings). Never raises — the demo must not break.
"""
from __future__ import annotations

import json

from app.agents import json_utils, prompts
from app.config import settings
from app.models import ActionType, Critique, Finding, MigrationPlan, Severity
from app.services import fireworks_service

_SEVERITY_ORDER = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}


def _deterministic_issues(plan: MigrationPlan, findings: list[Finding]) -> list[str]:
    """Grounding/coverage checks that need no LLM — the Critic's safety net."""
    issues: list[str] = []
    manual = [f for f in findings if f.action_type == ActionType.manual_review]

    if manual and not plan.manual_blockers:
        issues.append(
            f"{len(manual)} finding(s) need manual review but the plan lists no manual blockers."
        )
    if len(plan.manual_blockers) > len(manual):
        issues.append(
            "Plan lists more manual blockers than the scan found — possible invented items."
        )
    if findings and not plan.actions:
        issues.append("Findings exist but the plan has no actions.")

    if findings and plan.actions:
        top_finding = min(_SEVERITY_ORDER[f.severity] for f in findings)
        top_action = min(_SEVERITY_ORDER[a.severity] for a in plan.actions)
        if top_action > top_finding:
            issues.append(
                "The most severe finding is not reflected at matching severity in the plan."
            )
    return issues


def _llm_issues(plan: MigrationPlan, findings: list[Finding]) -> tuple[list[str], str]:
    """Ask Fireworks to critique the plan. Returns (issues, notes); empty on any failure."""
    raw = fireworks_service.complete(
        system=prompts.CRITIC,
        user=(
            "Findings:\n" + json.dumps([f.model_dump(mode="json") for f in findings], indent=2) +
            "\n\nProposed plan:\n" + plan.model_dump_json(indent=2) +
            '\n\nReturn JSON: {"approved": bool, "issues": [str], "notes": str}.'
        ),
        model=settings.critic_model,
        response_format={"type": "json_object"},
        max_tokens=3000,  # room for reasoning before the JSON verdict (bigger plans)
    )
    if not raw:
        return [], ""
    try:
        data = json.loads(json_utils.extract_json(raw))
    except (ValueError, TypeError):
        return [], ""
    issues = [str(i) for i in data.get("issues", []) if str(i).strip()]
    return issues, str(data.get("notes", ""))


def review(plan: MigrationPlan, findings: list[Finding]) -> Critique:
    """Review a plan; deterministic checks always run, LLM findings merge in when available."""
    issues = _deterministic_issues(plan, findings)
    llm_issues, notes = _llm_issues(plan, findings)
    # Merge, de-duplicating while preserving order.
    for i in llm_issues:
        if i not in issues:
            issues.append(i)
    if not notes:
        notes = "Deterministic review (no LLM)." if not llm_issues else "LLM + deterministic review."
    return Critique(approved=not issues, issues=issues, notes=notes)
