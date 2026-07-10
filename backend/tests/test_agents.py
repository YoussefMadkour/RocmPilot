"""Tests for the multi-agent layer: Critic + Orchestrator.

No network: Fireworks is stubbed. Focus is the Critic's deterministic grounding
checks and the Orchestrator's Planner->Critic->(revise) coordination + trace.
"""
from __future__ import annotations

import pytest

from app.agents import critic, migration_planner, orchestrator
from app.config import settings
from app.models import (
    ActionType, Critique, Finding, FindingCategory, MigrationPlan, PlanAction, Severity,
)
from app.services import scanner_service
from app.config import SAMPLE_PROJECTS_DIR


def _finding(cat, sev, action=ActionType.auto_patch, line=1):
    return Finding(file_path="f.py", line_number=line, severity=sev, category=cat,
                   matched_text="x", explanation="x", recommended_action="x", action_type=action)


def _plan(actions=None, blockers=None, summary="s"):
    return MigrationPlan(summary=summary, actions=actions or [], manual_blockers=blockers or [])


def _no_llm(monkeypatch):
    monkeypatch.setattr(critic.fireworks_service, "complete", lambda **k: None)
    monkeypatch.setattr(migration_planner.fireworks_service, "complete", lambda **k: None)


# --------------------------------------------------------------------------- #
# Critic — deterministic grounding checks
# --------------------------------------------------------------------------- #
def test_critic_flags_missing_manual_blockers(monkeypatch):
    _no_llm(monkeypatch)
    findings = [_finding(FindingCategory.manual_blocker, Severity.critical, ActionType.manual_review)]
    plan = _plan(actions=[PlanAction(title="t", detail="d", severity=Severity.critical,
                                     action_type=ActionType.manual_review)])  # but no manual_blockers
    result = critic.review(plan, findings)
    assert not result.approved
    assert any("manual" in i.lower() for i in result.issues)


def test_critic_flags_invented_blockers(monkeypatch):
    _no_llm(monkeypatch)
    findings = [_finding(FindingCategory.cuda_hardcoding, Severity.medium)]
    plan = _plan(actions=[PlanAction(title="t", detail="d", severity=Severity.medium,
                                     action_type=ActionType.auto_patch)],
                 blockers=["invented.py:1 — made up"])
    result = critic.review(plan, findings)
    assert not result.approved
    assert any("invented" in i.lower() or "more manual blockers" in i.lower() for i in result.issues)


def test_critic_approves_faithful_plan(monkeypatch):
    _no_llm(monkeypatch)
    findings = [_finding(FindingCategory.cuda_hardcoding, Severity.medium)]
    plan = _plan(actions=[PlanAction(title="t", detail="d", severity=Severity.medium,
                                     action_type=ActionType.auto_patch)])
    result = critic.review(plan, findings)
    assert result.approved
    assert result.issues == []


def test_critic_merges_llm_issues(monkeypatch):
    monkeypatch.setattr(critic.fireworks_service, "complete",
                        lambda **k: '{"approved": false, "issues": ["LLM: weak detail"], "notes": "n"}')
    findings = [_finding(FindingCategory.cuda_hardcoding, Severity.medium)]
    plan = _plan(actions=[PlanAction(title="t", detail="d", severity=Severity.medium,
                                     action_type=ActionType.auto_patch)])
    result = critic.review(plan, findings)
    assert not result.approved
    assert "LLM: weak detail" in result.issues


# --------------------------------------------------------------------------- #
# Orchestrator — coordination + trace
# --------------------------------------------------------------------------- #
def test_orchestrator_returns_plan_critique_trace(monkeypatch):
    _no_llm(monkeypatch)
    findings, _ = scanner_service.scan(SAMPLE_PROJECTS_DIR / "cuda_first_transformers_demo")
    plan, critique, trace = orchestrator.plan_with_review(findings, "run1")
    assert isinstance(plan, MigrationPlan) and plan.actions
    assert isinstance(critique, Critique)
    agents_seen = {e.agent for e in trace}
    assert {"orchestrator", "planner", "critic"} <= agents_seen


def test_orchestrator_offline_skips_revision(monkeypatch):
    """Offline, the deterministic planner can't revise — no second planner step."""
    _no_llm(monkeypatch)
    monkeypatch.setattr(settings, "fireworks_api_key", "")  # fireworks_enabled -> False
    # Force the critic to reject so we can confirm no revision is attempted.
    monkeypatch.setattr(critic, "review",
                        lambda p, f: Critique(approved=False, issues=["x"], notes="n"))
    findings = [_finding(FindingCategory.cuda_hardcoding, Severity.medium)]
    _, _, trace = orchestrator.plan_with_review(findings)
    planner_steps = [e for e in trace if e.agent == "planner"]
    assert len(planner_steps) == 1  # drafted only; no "revised" step


def test_orchestrator_revises_when_llm_available(monkeypatch):
    monkeypatch.setattr(settings, "fireworks_api_key", "test-key")  # fireworks_enabled -> True
    calls = {"n": 0}

    def _fake_plan(findings, *, revision_notes=None):
        calls["n"] += 1
        return _plan(actions=[PlanAction(title="t", detail="d", severity=Severity.medium,
                                         action_type=ActionType.auto_patch)])

    # First review rejects, second (post-revision) approves.
    reviews = iter([Critique(approved=False, issues=["fix me"], notes="n"),
                    Critique(approved=True, issues=[], notes="ok")])
    monkeypatch.setattr(orchestrator.migration_planner, "plan", _fake_plan)
    monkeypatch.setattr(orchestrator.critic, "review", lambda p, f: next(reviews))

    findings = [_finding(FindingCategory.cuda_hardcoding, Severity.medium)]
    _, critique, trace = orchestrator.plan_with_review(findings)
    assert calls["n"] == 2  # drafted + revised
    assert critique.approved
    assert any("Revised" in e.message for e in trace)
