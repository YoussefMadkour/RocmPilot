"""Research agent — the "when it gets stuck" investigator.

OWNER: Youssef (AI). Given a problem (a failed validation log, or a manual
blocker), it GATHERS grounding — the ROCm/HIP knowledge base (RAG) plus an
optional web search — then synthesizes a structured, cited diagnosis:
root cause, recommended fix, confidence, next command, and its sources.

Fallback-safe at every layer: no KB / no web / no Fireworks key each degrade
independently, down to a deterministic ROCm-savvy answer. Never raises.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.agents import json_utils, prompts
from app.config import settings
from app.services import fireworks_service, knowledge_service, web_search


@dataclass
class ResearchResult:
    root_cause: str
    recommended_fix: str
    confidence: str            # "low" | "medium" | "high"
    next_command: str
    sources: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        md = (
            f"**Root cause:** {self.root_cause}\n\n"
            f"**Recommended fix:** {self.recommended_fix}\n\n"
            f"**Confidence:** {self.confidence}\n\n"
            f"**Next command:** `{self.next_command}`"
        )
        if self.sources:
            md += "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in self.sources)
        return md


def _gather(problem: str) -> tuple[str, list[str]]:
    """Collect grounding context + a source list from the KB and (optional) web."""
    blocks: list[str] = []
    sources: list[str] = []

    for c in knowledge_service.retrieve(problem):
        blocks.append(f"[doc] {c.text}")
        sources.append(c.source)

    for r in web_search.search(problem):
        blocks.append(f"[web] {r['title']}: {r['snippet']}")
        sources.append(r["url"])

    # De-dupe sources, keep order.
    seen: set[str] = set()
    unique = [s for s in sources if s and not (s in seen or seen.add(s))]
    return "\n".join(blocks), unique


def _fallback(problem: str, sources: list[str]) -> ResearchResult:
    return ResearchResult(
        root_cause="Likely the AMD/ROCm runtime is not reachable (no HIP device "
                   "visible) or a torch/ROCm version mismatch.",
        recommended_fix="Ensure /dev/kfd and /dev/dri are mounted, the user is in "
                        "the video/render group, a ROCm PyTorch wheel is installed, "
                        "and PYTORCH_ROCM_ARCH matches your GPU (e.g. gfx942).",
        confidence="medium",
        next_command="rocminfo",
        sources=sources,
    )


def investigate(problem: str) -> ResearchResult:
    """Research a problem and return a structured, cited diagnosis."""
    context, sources = _gather(problem)

    raw = fireworks_service.complete(
        system=prompts.RESEARCH_AGENT,
        user=(
            f"Problem:\n{problem}\n\n"
            + (f"Grounding (cite these):\n{context}\n\n" if context else "")
            + 'Return JSON: {"root_cause","recommended_fix","confidence"'
              ' (low|medium|high),"next_command"}.'
        ),
        model=settings.research_model,
        response_format={"type": "json_object"},
        max_tokens=3000,  # Kimi's long reasoning needs headroom before the JSON
    )
    if not raw:
        return _fallback(problem, sources)
    try:
        data = json.loads(json_utils.extract_json(raw))
    except (ValueError, TypeError):
        return _fallback(problem, sources)

    return ResearchResult(
        root_cause=str(data.get("root_cause", "")).strip() or _fallback(problem, sources).root_cause,
        recommended_fix=str(data.get("recommended_fix", "")).strip()
        or _fallback(problem, sources).recommended_fix,
        confidence=str(data.get("confidence", "medium")).strip().lower() or "medium",
        next_command=str(data.get("next_command", "rocminfo")).strip() or "rocminfo",
        sources=sources,
    )
