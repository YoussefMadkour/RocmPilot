"use client";

// STARTER vertical slice — proves the frontend talks to the backend end to end.
// Jithandra: this is your seed. Run the frontend-design skill, then split this
// into the six cockpit screens (Intake / Scan / Plan / Patch / Validate / Report)
// described in docs/API_CONTRACT.md and PROJECT_TRACKER.md.

import { useState } from "react";
import { api, type Finding, type ScoreBreakdown } from "@/lib/api";

export default function Home() {
  const [runId, setRunId] = useState<string | null>(null);
  const [score, setScore] = useState<ScoreBreakdown | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runDemo() {
    setBusy(true);
    setError(null);
    try {
      const run = await api.createRun({ use_sample: true });
      setRunId(run.run_id);
      const scan = await api.scan(run.run_id);
      setScore(scan.score);
      setFindings(scan.findings);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold">RocmPilot Studio</h1>
      <p className="mt-2 text-neutral-400">
        AI migration &amp; validation cockpit for AMD GPU readiness.
      </p>

      <button
        onClick={runDemo}
        disabled={busy}
        className="mt-8 rounded-lg bg-accent px-4 py-2 font-medium text-white disabled:opacity-50"
      >
        {busy ? "Scanning…" : "Scan sample CUDA-first repo"}
      </button>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      {score && (
        <div className="mt-8 rounded-xl border border-neutral-800 p-5">
          <p className="text-sm text-neutral-400">Run {runId}</p>
          <p className="mt-1 text-2xl font-semibold">
            ROCm Readiness (before): {score.before}/100
          </p>
          <p className="text-neutral-400">
            Projected after patches: {score.after_planned}/100
          </p>
        </div>
      )}

      {findings.length > 0 && (
        <ul className="mt-6 space-y-2">
          {findings.map((f, i) => (
            <li
              key={i}
              className="rounded-lg border border-neutral-800 px-4 py-3 text-sm"
            >
              <span className="font-mono text-accent">[{f.severity}]</span>{" "}
              <span className="font-mono text-neutral-300">
                {f.file_path}:{f.line_number}
              </span>
              <div className="text-neutral-400">{f.explanation}</div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
