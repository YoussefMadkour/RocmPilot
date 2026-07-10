"""Tests for the Migration Planner agent.

No network: the Fireworks call is stubbed. Focus is JSON-validity robustness
(recover fenced/prose-wrapped replies, reject bad ones) and the grounded,
always-valid deterministic fallback.
"""
from __future__ import annotations

import pytest

from app.agents import migration_planner
from app.models import ActionType, MigrationPlan, Severity
from app.services import scanner_service
from app.config import SAMPLE_PROJECTS_DIR

VALID_JSON = (
    '{"summary": "Mostly ready.", "actions": ['
    '{"title": "Resolve device dynamically", "detail": "Use torch.cuda.is_available().",'
    ' "severity": "medium", "action_type": "auto_patch"}], "manual_blockers": []}'
)


def _sample_findings():
    findings, _ = scanner_service.scan(SAMPLE_PROJECTS_DIR / "cuda_first_transformers_demo")
    return findings


# --------------------------------------------------------------------------- #
# _extract_json — recover JSON from messy LLM replies
# --------------------------------------------------------------------------- #
def test_extract_plain_json():
    assert migration_planner._extract_json(VALID_JSON) == VALID_JSON


def test_extract_from_json_fence():
    fenced = f"```json\n{VALID_JSON}\n```"
    assert migration_planner._extract_json(fenced) == VALID_JSON


def test_extract_from_bare_fence():
    fenced = f"```\n{VALID_JSON}\n```"
    assert migration_planner._extract_json(fenced) == VALID_JSON


def test_extract_strips_surrounding_prose():
    wrapped = f"Here is your plan:\n{VALID_JSON}\nHope that helps!"
    assert migration_planner._extract_json(wrapped) == VALID_JSON


# --------------------------------------------------------------------------- #
# _parse_plan — validate into a MigrationPlan or reject
# --------------------------------------------------------------------------- #
def test_parse_valid():
    plan = migration_planner._parse_plan(VALID_JSON, _sample_findings())
    assert isinstance(plan, MigrationPlan)
    assert plan.actions[0].action_type == ActionType.auto_patch


def test_parse_fenced_valid():
    plan = migration_planner._parse_plan(f"```json\n{VALID_JSON}\n```", _sample_findings())
    assert isinstance(plan, MigrationPlan)


def test_parse_rejects_bad_enum():
    bad = VALID_JSON.replace('"action_type": "auto_patch"', '"action_type": "patch_it"')
    assert migration_planner._parse_plan(bad, _sample_findings()) is None


def test_parse_rejects_garbage():
    assert migration_planner._parse_plan("not json at all", _sample_findings()) is None


def test_parse_rejects_empty_actions_when_findings_exist():
    empty = '{"summary": "x", "actions": [], "manual_blockers": []}'
    assert migration_planner._parse_plan(empty, _sample_findings()) is None
    # ...but an empty plan is fine when there were no findings.
    assert migration_planner._parse_plan(empty, []) is not None


# --------------------------------------------------------------------------- #
# plan() — orchestration with the Fireworks call stubbed
# --------------------------------------------------------------------------- #
def test_plan_uses_llm_when_valid(monkeypatch):
    monkeypatch.setattr(migration_planner.fireworks_service, "complete",
                        lambda **k: f"```json\n{VALID_JSON}\n```")
    plan = migration_planner.plan(_sample_findings())
    assert plan.summary == "Mostly ready."  # came from the (fenced) LLM reply


def test_plan_falls_back_when_no_key(monkeypatch):
    monkeypatch.setattr(migration_planner.fireworks_service, "complete", lambda **k: None)
    plan = migration_planner.plan(_sample_findings())
    assert isinstance(plan, MigrationPlan)
    assert plan.actions  # deterministic fallback still produced a plan


def test_plan_falls_back_on_garbage(monkeypatch):
    monkeypatch.setattr(migration_planner.fireworks_service, "complete",
                        lambda **k: "the model rambled and forgot the json")
    plan = migration_planner.plan(_sample_findings())
    assert plan.actions  # fell back rather than raising/returning empty


# --------------------------------------------------------------------------- #
# Fallback quality — grounded and always valid
# --------------------------------------------------------------------------- #
def test_fallback_is_grounded_and_valid():
    findings = _sample_findings()
    plan = migration_planner._fallback(findings)
    # Every action carries valid enums (this is what keeps the response schema-valid).
    for a in plan.actions:
        assert isinstance(a.severity, Severity)
        assert isinstance(a.action_type, ActionType)
    # Manual blockers correspond exactly to manual_review findings.
    n_manual = sum(1 for f in findings if f.action_type == ActionType.manual_review)
    assert len(plan.manual_blockers) == n_manual


def test_fallback_dedupes_actions():
    """Many findings that share a fix collapse to fewer actions than findings."""
    findings = _sample_findings()
    plan = migration_planner._fallback(findings)
    assert len(plan.actions) < len(findings)


def test_fallback_orders_by_severity():
    plan = migration_planner._fallback(_sample_findings())
    order = [migration_planner._SEVERITY_ORDER[a.severity] for a in plan.actions]
    assert order == sorted(order)
