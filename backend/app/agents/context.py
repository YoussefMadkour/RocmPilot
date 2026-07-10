"""Shared context/scratchpad passed between agents during an orchestrated run.

OWNER: Youssef (AI). Accumulates the multi-agent activity trace (who did what),
which the Plan screen renders as an agent-activity timeline.
"""
from __future__ import annotations

from app.models import AgentEvent


class AgentContext:
    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id
        self.events: list[AgentEvent] = []

    def log(self, agent: str, message: str, *, ok: bool = True) -> None:
        self.events.append(AgentEvent(agent=agent, message=message, ok=ok))
