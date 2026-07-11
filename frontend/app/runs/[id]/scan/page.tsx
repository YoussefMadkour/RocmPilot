"use client";

// 02 · Scan — deterministic CUDA/NVIDIA blocker scan.
// Score card + findings-by-category summary + full findings table with
// severity and category filtering (Phase 2 acceptance).

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type ScanResponse, type Severity } from "@/lib/api";
import { ActionTypeTag, SeverityBadge } from "@/components/badges";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-2.5 py-1 font-mono text-[11px] transition-colors ${
        active
          ? "border-ink-dim bg-edge/60 text-ink"
          : "border-edge text-ink-dim hover:border-ink-dim hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

export default function ScanPage() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState<Severity | "all">("all");
  const [catFilter, setCatFilter] = useState<string>("all");
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true; // avoid double-POST from React strict mode
    api
      .scan(id)
      .then(setScan)
      .catch((e) => setError(e instanceof Error ? e.message : "Scan failed"));
  }, [id]);

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    scan?.findings.forEach((f) => (counts[f.severity] += 1));
    return counts;
  }, [scan]);

  const filtered = useMemo(
    () =>
      (scan?.findings ?? []).filter(
        (f) =>
          (sevFilter === "all" || f.severity === sevFilter) &&
          (catFilter === "all" || f.category === catFilter),
      ),
    [scan, sevFilter, catFilter],
  );

  if (error)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Scan</h1>
        <p role="alert" className="mt-3 text-sm text-ember">
          {error}
        </p>
      </section>
    );

  if (!scan)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Scan</h1>
        <p className="mt-3 font-mono text-sm text-ink-dim">
          <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
          Scanning source for CUDA / NVIDIA blockers…
        </p>
      </section>
    );

  return (
    <div className="space-y-4">
      {/* Score card */}
      <section className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-edge bg-panel p-6">
        <div>
          <p className="font-mono text-[11px] tracking-widest text-ink-dim">
            ROCM READINESS
          </p>
          <div className="mt-2 flex items-baseline gap-6">
            <p className="font-display text-5xl font-bold">
              {scan.score.before}
              <span className="text-lg text-ink-dim">/100</span>
            </p>
            {scan.score.after_planned != null && (
              <p className="text-sm text-ink-dim">
                projected after patches:{" "}
                <span className="font-mono text-ready">
                  {scan.score.after_planned}/100
                </span>
              </p>
            )}
          </div>
          <p className="mt-3 font-mono text-[11px] text-ink-dim">
            {scan.findings.length} findings across {scan.files_scanned} files
          </p>
        </div>
        <Link
          href={`/runs/${id}/plan`}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
        >
          Generate migration plan →
        </Link>
      </section>

      {/* Findings table with filters */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-display text-sm font-semibold tracking-wide">
            Findings
          </h2>
          <p className="font-mono text-[11px] text-ink-dim">
            showing {filtered.length} of {scan.findings.length}
          </p>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="mr-1 font-mono text-[10px] uppercase tracking-widest text-ink-dim">
            severity
          </span>
          <FilterChip active={sevFilter === "all"} onClick={() => setSevFilter("all")}>
            all
          </FilterChip>
          {SEVERITIES.map((s) => (
            <FilterChip
              key={s}
              active={sevFilter === s}
              onClick={() => setSevFilter(sevFilter === s ? "all" : s)}
            >
              {s} · {severityCounts[s]}
            </FilterChip>
          ))}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="mr-1 font-mono text-[10px] uppercase tracking-widest text-ink-dim">
            category
          </span>
          <FilterChip active={catFilter === "all"} onClick={() => setCatFilter("all")}>
            all
          </FilterChip>
          {Object.entries(scan.findings_by_category).map(([cat, count]) => (
            <FilterChip
              key={cat}
              active={catFilter === cat}
              onClick={() => setCatFilter(catFilter === cat ? "all" : cat)}
            >
              {cat.replace(/_/g, " ")} · {count}
            </FilterChip>
          ))}
        </div>

        {filtered.length === 0 ? (
          <p className="mt-6 text-sm text-ink-dim">
            No findings match these filters. Clear a filter to see the rest.
          </p>
        ) : (
          <div className="mt-4 max-h-[34rem] overflow-auto">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead className="sticky top-0 z-10 bg-panel">
                <tr className="border-b border-edge font-mono text-[10px] uppercase tracking-widest text-ink-dim">
                  <th className="py-2 pr-4 font-normal">Severity</th>
                  <th className="py-2 pr-4 font-normal">Location</th>
                  <th className="py-2 pr-4 font-normal">Category</th>
                  <th className="py-2 font-normal">Finding</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((f, i) => (
                  <tr key={i} className="border-b border-edge/50 align-top">
                    <td className="py-3 pr-4">
                      <SeverityBadge severity={f.severity} />
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-ink-dim">
                      {f.line_number > 0 ? (
                        <>
                          {f.file_path}
                          <span className="text-ink">:{f.line_number}</span>
                        </>
                      ) : (
                        "repo level"
                      )}
                    </td>
                    <td className="py-3 pr-4">
                      <div className="text-xs text-ink-dim">
                        {f.category.replace(/_/g, " ")}
                      </div>
                      <div className="mt-1">
                        <ActionTypeTag actionType={f.action_type} />
                      </div>
                    </td>
                    <td className="py-3">
                      <p>{f.explanation}</p>
                      {f.line_number > 0 && (
                        <p className="mt-1 truncate font-mono text-xs text-ink-dim/70 max-w-md">
                          {f.matched_text}
                        </p>
                      )}
                      <p className="mt-1 text-xs text-ink-dim">
                        → {f.recommended_action}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
