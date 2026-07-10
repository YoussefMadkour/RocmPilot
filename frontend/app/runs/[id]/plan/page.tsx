"use client";

// 03 · Plan — the Migration Planner agent turns scan findings into a
// prioritized plan. Renders identically with or without a Fireworks key
// (the backend falls back to a deterministic plan).

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type MigrationPlan } from "@/lib/api";
import { ActionTypeTag, SeverityBadge } from "@/components/badges";

export default function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<MigrationPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true; // avoid double-POST from React strict mode
    api
      .plan(id)
      .then((res) => setPlan(res.plan))
      .catch((e) => setError(e instanceof Error ? e.message : "Planning failed"));
  }, [id]);

  if (error)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Plan</h1>
        <p role="alert" className="mt-3 text-sm text-ember">
          {error}
        </p>
        <Link
          href={`/runs/${id}/scan`}
          className="mt-4 inline-block rounded-lg border border-edge px-4 py-2 text-sm hover:border-ink-dim"
        >
          ← Run the scan first
        </Link>
      </section>
    );

  if (!plan)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Plan</h1>
        <p className="mt-3 font-mono text-sm text-ink-dim">
          <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
          Migration Planner is reasoning over the findings…
        </p>
      </section>
    );

  const activity = [
    "Scan findings handed to the Migration Planner",
    `Planner returned ${plan.actions.length} prioritized action${plan.actions.length === 1 ? "" : "s"}`,
    `${plan.manual_blockers.length} finding${plan.manual_blockers.length === 1 ? "" : "s"} flagged for manual review`,
    "Plan validated against the API contract",
  ];

  return (
    <div className="space-y-4">
      {/* Agent summary */}
      <section className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-edge bg-panel p-6">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] tracking-widest text-ink-dim">
            MIGRATION PLANNER · AGENT SUMMARY
          </p>
          <p className="mt-3 text-sm leading-relaxed">{plan.summary}</p>
        </div>
        <Link
          href={`/runs/${id}/patch`}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
        >
          Generate patches →
        </Link>
      </section>

      {/* Prioritized actions — order is the priority, so the numbering is real */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h2 className="font-display text-sm font-semibold tracking-wide">
          Prioritized actions
        </h2>
        <ol className="mt-4 space-y-3">
          {plan.actions.map((a, i) => (
            <li key={i} className="flex gap-3 border-b border-edge/50 pb-3 last:border-b-0 last:pb-0">
              <span className="font-mono text-[11px] text-ink-dim">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{a.title}</span>
                  <SeverityBadge severity={a.severity} />
                  <ActionTypeTag actionType={a.action_type} />
                </div>
                <p className="mt-1 text-sm text-ink-dim">{a.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Manual blockers */}
        <section className="rounded-xl border border-edge bg-panel p-6">
          <h2 className="font-display text-sm font-semibold tracking-wide">
            Manual blockers
          </h2>
          {plan.manual_blockers.length === 0 ? (
            <p className="mt-3 text-sm text-ink-dim">
              None — every finding is auto- or suggested-patchable.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {plan.manual_blockers.map((b, i) => (
                <li key={i} className="flex gap-2 text-xs">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ember" aria-hidden />
                  <span className="font-mono text-ink-dim">{b}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Agent activity */}
        <section className="rounded-xl border border-edge bg-panel p-6">
          <h2 className="font-display text-sm font-semibold tracking-wide">
            Agent activity
          </h2>
          <ol className="mt-4 space-y-0">
            {activity.map((step, i) => (
              <li key={step} className="relative flex gap-3 pb-4 last:pb-0">
                {i < activity.length - 1 && (
                  <span
                    className="absolute left-[3px] top-3 h-full w-px bg-edge"
                    aria-hidden
                  />
                )}
                <span className="relative mt-1.5 h-[7px] w-[7px] shrink-0 rounded-full bg-ready" aria-hidden />
                <span className="text-xs text-ink-dim">{step}</span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
