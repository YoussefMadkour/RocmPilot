"use client";

// 02 · Scan — runs the deterministic scanner and shows the readiness score.
// Phase 1 keeps this minimal (score + category counts) so the vertical slice
// stays alive; the full findings table with severity/category filters is the
// Phase 2 deliverable.

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type ScanResponse } from "@/lib/api";

export default function ScanPage() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true; // avoid double-POST from React strict mode
    api
      .scan(id)
      .then(setScan)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Scan failed"),
      );
  }, [id]);

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
      <section className="rounded-xl border border-edge bg-panel p-6">
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
      </section>

      <section className="rounded-xl border border-edge bg-panel p-6">
        <h2 className="font-display text-sm font-semibold tracking-wide">
          Findings by category
        </h2>
        <ul className="mt-3 space-y-1.5">
          {Object.entries(scan.findings_by_category).map(([cat, count]) => (
            <li key={cat} className="flex justify-between font-mono text-sm">
              <span className="text-ink-dim">{cat.replace(/_/g, " ")}</span>
              <span>{count}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 border-t border-edge pt-3 text-[11px] text-ink-dim">
          Full findings table with severity badges and filters lands in Phase 2.
        </p>
      </section>
    </div>
  );
}
