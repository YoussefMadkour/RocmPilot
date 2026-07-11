"use client";

// The signature element of the UI (see frontend/DESIGN.md): a numbered
// flight-check rail. The numbers are honest — the backend enforces this stage
// order with 409s — and the LEDs reflect the run's real persisted stage.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type RunStage, type ScoreBreakdown } from "@/lib/api";

const STAGES = [
  { num: "01", label: "Intake", segment: "" },
  { num: "02", label: "Scan", segment: "scan" },
  { num: "03", label: "Plan", segment: "plan" },
  { num: "04", label: "Patch", segment: "patch" },
  { num: "05", label: "Validate", segment: "validate" },
  { num: "06", label: "Report", segment: "report" },
] as const;

// How many stages a run at each backend stage has completed (intake = 1).
const STAGE_RANK: Record<RunStage, number> = {
  created: 1,
  scanned: 2,
  planned: 3,
  patched: 4,
  validated: 5,
  reported: 6,
};

function Led({ state }: { state: "done" | "active" | "pending" }) {
  if (state === "done")
    return <span className="h-2 w-2 rounded-full bg-ready" aria-hidden />;
  if (state === "active")
    return <span className="led-pulse h-2 w-2 rounded-full bg-ember" aria-hidden />;
  return <span className="h-2 w-2 rounded-full border border-edge" aria-hidden />;
}

export function CockpitRail({ runId }: { runId?: string }) {
  const pathname = usePathname();
  const [stage, setStage] = useState<RunStage | null>(null);
  const [score, setScore] = useState<ScoreBreakdown | null>(null);

  useEffect(() => {
    if (!runId) return;
    api
      .getRun(runId)
      .then((run) => {
        setStage(run.stage);
        setScore(run.score);
      })
      .catch(() => {
        /* rail degrades to route-only highlighting if the API is down */
      });
  }, [runId, pathname]);

  const completed = stage ? STAGE_RANK[stage] : runId ? 1 : 0;
  const activeSegment = runId ? pathname.split("/").pop() ?? "" : "";

  return (
    <nav
      aria-label="Run stages"
      className="shrink-0 rounded-xl border border-edge bg-panel p-3 md:w-52 md:p-4"
    >
      <ol className="flex gap-1 overflow-x-auto md:flex-col md:gap-0.5">
        {STAGES.map((s, i) => {
          const isIntake = s.segment === "";
          const href = isIntake ? "/" : runId ? `/runs/${runId}/${s.segment}` : null;
          const isActive = runId
            ? !isIntake && s.segment === activeSegment
            : isIntake;
          const led: "done" | "active" | "pending" = isActive
            ? "active"
            : i < completed
              ? "done"
              : "pending";

          const inner = (
            <span className="flex items-center gap-2.5 whitespace-nowrap px-2.5 py-2">
              <Led state={led} />
              <span className="font-mono text-[11px] text-ink-dim">{s.num}</span>
              <span
                className={`font-display text-sm tracking-wide ${
                  isActive ? "text-ink" : led === "done" ? "text-ink-dim" : "text-ink-dim/60"
                }`}
              >
                {s.label}
              </span>
            </span>
          );

          return (
            <li key={s.num}>
              {href ? (
                <Link
                  href={href}
                  aria-current={isActive ? "step" : undefined}
                  className={`block rounded-lg hover:bg-edge/40 ${isActive ? "bg-edge/60" : ""}`}
                >
                  {inner}
                </Link>
              ) : (
                <span className="block cursor-not-allowed opacity-50" title="Start a run first">
                  {inner}
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {runId && (
        <div className="mt-3 hidden border-t border-edge pt-3 md:block">
          <p className="font-mono text-[11px] text-ink-dim">RUN {runId}</p>
          {score && (
            <p className="mt-1 font-mono text-[11px] text-ink-dim">
              READINESS{" "}
              <span className="text-ink">
                {score.final ?? score.after_planned ?? score.before}
              </span>
              /100
            </p>
          )}
        </div>
      )}
    </nav>
  );
}
