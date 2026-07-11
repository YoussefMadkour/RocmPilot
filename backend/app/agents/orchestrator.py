"""Orchestrator — coordinates the planning agents (code-first, no framework).

OWNER: Youssef (AI). Runs Planner -> Critic; when the LLM is available and the
Critic requests changes, one Planner revision addressing the feedback, then a
re-review. `plan_events` is a generator so the UI can STREAM progress live
(status lines + agent-trace events) instead of staring at a 40s spinner.
`plan_with_review` is the batch wrapper used by the non-streaming endpoint.

Deterministic fallbacks throughout: this never raises and always returns a plan.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.agents import critic, migration_planner
from app.config import settings
from app.models import AgentEvent, Critique, Finding, MigrationPlan


def plan_events(findings: list[Finding], run_id: str | None = None) -> Iterator[tuple]:
    """Yield ('status', msg) liveness lines and ('event', AgentEvent) trace steps as
    the agents work, then a final ('result', (plan, critique, [AgentEvent]))."""
    live = settings.fireworks_enabled
    planner_m = settings.planner_model.split("/")[-1] if live else "deterministic"
    critic_m = settings.critic_model.split("/")[-1] if live else "deterministic"
    events: list[AgentEvent] = []

    def event(agent: str, message: str, ok: bool = True, model: str | None = None) -> tuple:
        e = AgentEvent(agent=agent, message=message, ok=ok, model=model)
        events.append(e)
        return ("event", e)

    yield event("orchestrator", f"Coordinating migration plan for {len(findings)} findings.")

    yield ("status", f"Planner ({planner_m}) is drafting the migration plan…")
    plan = migration_planner.plan(findings)
    yield event("planner", f"Drafted {len(plan.actions)} actions, "
                           f"{len(plan.manual_blockers)} manual blocker(s).", model=planner_m)

    yield ("status", f"Critic ({critic_m}) is reviewing the plan…")
    critique = critic.review(plan, findings)
    if critique.approved:
        yield event("critic", "Reviewed the plan — approved, no issues.", model=critic_m)
        yield ("result", (plan, critique, events))
        return
    yield event("critic", f"Reviewed the plan — requested changes "
                          f"({len(critique.issues)} issue(s)).", ok=False, model=critic_m)

    # Only a live LLM can meaningfully revise; the deterministic planner is fixed.
    if live:
        yield ("status", f"Planner ({planner_m}) is revising to address the Critic…")
        plan = migration_planner.plan(findings, revision_notes=critique.issues)
        yield event("planner", "Revised the plan to address the Critic's feedback.",
                    model=planner_m)
        yield ("status", f"Critic ({critic_m}) is re-reviewing the revision…")
        critique = critic.review(plan, findings)
        yield event("critic",
                    "Re-reviewed the revision — " + ("approved." if critique.approved
                                                          else "issues remain."),
                    ok=critique.approved, model=critic_m)

    yield ("result", (plan, critique, events))


def plan_with_review(
    findings: list[Finding], run_id: str | None = None
) -> tuple[MigrationPlan, Critique, list[AgentEvent]]:
    """Batch version: drain the event stream and return the final result."""
    plan: MigrationPlan | None = None
    critique: Critique | None = None
    trace: list[AgentEvent] = []
    for kind, payload in plan_events(findings, run_id):
        if kind == "result":
            plan, critique, trace = payload
    return plan, critique, trace
