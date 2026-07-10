"""Migration Planner agent (Fireworks-powered, deterministic fallback).

OWNER: Youssef (AI). Turns raw scan findings into a prioritized, explained plan.
"""
from __future__ import annotations

import json
import re

from app.agents import prompts
from app.models import ActionType, Finding, MigrationPlan, PlanAction, Severity
from app.services import fireworks_service

_SEVERITY_ORDER = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}

# Matches a ```json ... ``` or ``` ... ``` fenced block; group 1 is the inner body.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_json(raw: str) -> str:
    """Pull a JSON object out of an LLM reply that may be fenced or prose-wrapped.

    LLMs frequently wrap JSON in ```json fences or add a sentence before/after it;
    a bare json.loads/model_validate on that fails. Recover the object instead of
    silently falling back and throwing away a good plan.
    """
    text = raw.strip()
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    # Trim any leading/trailing prose around the outermost {...}.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


def _parse_plan(raw: str, findings: list[Finding]) -> MigrationPlan | None:
    """Validate an LLM reply into a MigrationPlan, or None if it can't be trusted."""
    try:
        plan_obj = MigrationPlan.model_validate_json(_extract_json(raw))
    except ValueError:
        return None
    # A grounded scan with findings but an empty action list is degenerate — the
    # deterministic fallback is more useful than an empty plan.
    if findings and not plan_obj.actions:
        return None
    return plan_obj


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
    auto = sum(1 for f in findings if f.action_type in (ActionType.auto_patch, ActionType.suggested_patch))
    summary = (
        f"Detected {len(findings)} CUDA/NVIDIA signals across "
        f"{len({f.category for f in findings})} categories: "
        f"{auto} are auto- or suggested-patchable and {len(blockers)} need manual review. "
        "Note: on ROCm the torch.cuda namespace still works — the goal is removing "
        "NVIDIA-only assumptions, not renaming 'cuda'."
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
    # Recover the JSON even if fenced/prose-wrapped; fall back only if it's truly
    # unusable so a flaky model never breaks the demo.
    return _parse_plan(raw, findings) or _fallback(findings)
