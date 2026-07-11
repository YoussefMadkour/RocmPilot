"use client";

// 06 · Report — the flight debrief: score journey, the judge-ready Markdown
// report from the Report Writer agent, and every artifact in one place.

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Markdown from "react-markdown";
import { api, type Artifact, type ScoreBreakdown } from "@/lib/api";

function ScoreStep({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | null | undefined;
  tone: string;
}) {
  return (
    <div className="flex-1 rounded-lg border border-edge bg-bay/60 px-4 py-3 text-center">
      <p className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
        {label}
      </p>
      <p className={`mt-1 font-display text-4xl font-bold ${tone}`}>
        {value ?? "—"}
        <span className="text-sm text-ink-dim">/100</span>
      </p>
    </div>
  );
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [score, setScore] = useState<ScoreBreakdown | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true;
    api
      .report(id)
      .then((res) => {
        setMarkdown(res.markdown);
        setScore(res.score);
        setArtifacts(res.artifacts);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Report generation failed"),
      );
  }, [id]);

  function downloadReport() {
    const blob = new Blob([markdown ?? ""], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "readiness_report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Report</h1>
        <p role="alert" className="mt-3 text-sm text-ember">
          {error}
        </p>
        <Link
          href={`/runs/${id}/validate`}
          className="mt-4 inline-block rounded-lg border border-edge px-4 py-2 text-sm hover:border-ink-dim"
        >
          ← Complete the earlier stages first
        </Link>
      </section>
    );

  if (markdown == null)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Report</h1>
        <p className="mt-3 font-mono text-sm text-ink-dim">
          <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
          Report Writer is assembling the debrief…
        </p>
      </section>
    );

  return (
    <div className="space-y-4">
      {/* Score journey */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-mono text-[11px] tracking-widest text-ink-dim">
            ROCM READINESS · BEFORE → AFTER
          </p>
          <div className="flex gap-2">
            <a
              href={api.artifactsZipUrl(id)}
              className="rounded-lg border border-edge px-4 py-2 text-sm font-medium hover:border-ink-dim"
            >
              Download all artifacts (.zip)
            </a>
            <button
              onClick={downloadReport}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
            >
              Download report
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
          <ScoreStep label="Before" value={score?.before} tone="text-crit" />
          <span className="hidden text-center font-mono text-ink-dim sm:block" aria-hidden>
            →
          </span>
          <ScoreStep label="After patches" value={score?.after_planned} tone="text-warn" />
          <span className="hidden text-center font-mono text-ink-dim sm:block" aria-hidden>
            →
          </span>
          <ScoreStep label="Validated final" value={score?.final} tone="text-ready" />
        </div>
      </section>

      {/* The judge-ready report */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <p className="font-mono text-[11px] tracking-widest text-ink-dim">
          REPORT WRITER · READINESS_REPORT.MD
        </p>
        <div className="report-md mt-4">
          <Markdown>{markdown}</Markdown>
        </div>
      </section>

      {/* Artifact list */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h2 className="font-display text-sm font-semibold tracking-wide">
          Generated artifacts
        </h2>
        <ul className="mt-3 space-y-1.5">
          {artifacts.map((a) => (
            <li key={a.name} className="flex items-baseline justify-between gap-2 font-mono text-sm">
              <span>{a.name}</span>
              <span className="text-[11px] text-ink-dim">{a.language}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 border-t border-edge pt-3 text-xs text-ink-dim">
          Everything above is in the zip. Apply <span className="font-mono">patch.diff</span>,
          build with <span className="font-mono">Dockerfile.rocm</span>, and run{" "}
          <span className="font-mono">smoke_test.py</span> on AMD hardware to reproduce
          the validated score.
        </p>
      </section>
    </div>
  );
}
