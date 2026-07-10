// Severity + action-type badges, styled per frontend/DESIGN.md.
// Severity hues are status colors, never interactive — brand red stays on actions.

import type { ActionType, Severity } from "@/lib/api";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "border-crit/40 bg-crit/10 text-crit",
  high: "border-ember/40 bg-ember/10 text-ember",
  medium: "border-warn/40 bg-warn/10 text-warn",
  low: "border-edge bg-edge/30 text-ink-dim",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${SEVERITY_STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}

const ACTION_LABELS: Record<ActionType, string> = {
  auto_patch: "auto patch",
  suggested_patch: "suggested patch",
  manual_review: "manual review",
  info: "info",
};

export function ActionTypeTag({ actionType }: { actionType: ActionType }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded border border-edge px-1.5 py-0.5 font-mono text-[10px] ${
        actionType === "manual_review" ? "text-ember" : "text-ink-dim"
      }`}
    >
      {ACTION_LABELS[actionType]}
    </span>
  );
}
