"""Orchestrator — coordinates the planning agents (code-first, no framework).

OWNER: Youssef (AI). Runs Planner -> Critic, and when the LLM is available and the
Critic requests changes, asks the Planner for ONE revision addressing the feedback,
then re-reviews. Offline the Planner is deterministic, so a revise pass would just
repeat itself — we skip it but still surface the Critic's honest findings.

Every step is recorded in an AgentContext trace so the UI can show what each agent
did. Deterministic fallbacks throughout: this never raises and always returns a plan.
"""
from __future__ import annotations

from app.agents import critic, migration_planner
from app.agents.context import AgentContext
from app.config import settings
from app.models import AgentEvent, Critique, Finding, MigrationPlan


def plan_with_review(
    findings: list[Finding], run_id: str | None = None
) -> tuple[MigrationPlan, Critique, list[AgentEvent]]:
    # Short model names for the trace (e.g. "deepseek-v4-pro"); None when offline.
    live = settings.fireworks_enabled
    planner_m = settings.planner_model.split("/")[-1] if live else "deterministic"
    critic_m = settings.critic_model.split("/")[-1] if live else "deterministic"

    ctx = AgentContext(run_id)
    ctx.log("orchestrator", f"Coordinating migration plan for {len(findings)} findings.")

    plan = migration_planner.plan(findings)
    ctx.log("planner", f"Drafted {len(plan.actions)} actions, "
                       f"{len(plan.manual_blockers)} manual blocker(s).", model=planner_m)

    critique = critic.review(plan, findings)
    if critique.approved:
        ctx.log("critic", "Reviewed the plan — approved, no issues.", model=critic_m)
        return plan, critique, ctx.events

    ctx.log("critic", f"Reviewed the plan — requested changes ({len(critique.issues)} issue(s)).",
            ok=False, model=critic_m)

    # Only a live LLM can meaningfully revise; the deterministic planner is fixed.
    if live:
        plan = migration_planner.plan(findings, revision_notes=critique.issues)
        ctx.log("planner", "Revised the plan to address the Critic's feedback.", model=planner_m)
        critique = critic.review(plan, findings)
        ctx.log("critic",
                "Re-reviewed the revision — " + ("approved." if critique.approved
                                                 else "issues remain."),
                ok=critique.approved, model=critic_m)

    return plan, critique, ctx.events
