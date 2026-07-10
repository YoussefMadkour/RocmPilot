"use client";

// 05 · Validate — the AMD/ROCm validation run. Honesty rule from the API
// contract: a replay run must ALWAYS be labeled "Saved AMD run".

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type ScoreBreakdown, type ValidationResult } from "@/lib/api";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border border-edge bg-bay/60 px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">{label}</p>
      <p className={`mt-1 font-mono text-sm ${tone ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

export default function ValidatePage() {
  const { id } = useParams<{ id: string }>();
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [score, setScore] = useState<ScoreBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true; // avoid double-POST from React strict mode
    api
      .validate(id)
      .then((res) => {
        setValidation(res.validation);
        setScore(res.score);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Validation failed to start"));
  }, [id]);

  if (error)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Validate</h1>
        <p role="alert" className="mt-3 text-sm text-ember">
          {error}
        </p>
      </section>
    );

  if (!validation)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Validate</h1>
        <p className="mt-3 font-mono text-sm text-ink-dim">
          <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
          Running AMD validation…
        </p>
      </section>
    );

  const passed = validation.status === "passed";
  const failed = validation.status === "failed";

  return (
    <div className="space-y-4">
      {/* AMD validation card */}
      <section className="rounded-xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-mono text-[11px] tracking-widest text-ink-dim">
              AMD VALIDATION
            </p>
            <span
              className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider ${
                passed
                  ? "border-ready/40 bg-ready/10 text-ready"
                  : failed
                    ? "border-crit/40 bg-crit/10 text-crit"
                    : "border-edge text-ink-dim"
              }`}
            >
              {validation.status.replace("_", " ")}
            </span>
            {validation.mode === "replay" ? (
              <span className="rounded-full border border-ember/40 bg-ember/10 px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider text-ember">
                Saved AMD run · replay
              </span>
            ) : (
              <span className="rounded-full border border-edge px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider text-ink-dim">
                live run
              </span>
            )}
          </div>
          {score?.final != null && (
            <p className="font-display text-3xl font-bold">
              {score.final}
              <span className="text-base text-ink-dim">/100</span>
            </p>
          )}
        </div>

        {validation.mode === "replay" && (
          <p className="mt-2 text-xs text-ink-dim">
            This result was captured on AMD hardware and replayed for demo
            reliability — it is not executing live right now.
          </p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="GPU" value={validation.gpu_name ?? "—"} />
          <Stat
            label="Inference latency"
            value={
              validation.inference_latency_ms != null
                ? `${validation.inference_latency_ms} ms`
                : "—"
            }
          />
          <Stat label="PyTorch build" value={validation.pytorch_rocm_build ?? "—"} />
          <Stat
            label="ROCm detected"
            value={validation.rocm_detected ? "yes" : "no"}
            tone={validation.rocm_detected ? "text-ready" : "text-crit"}
          />
          <Stat
            label="HIP available"
            value={validation.hip_available ? "yes" : "no"}
            tone={validation.hip_available ? "text-ready" : "text-crit"}
          />
          <Stat
            label="Smoke test"
            value={validation.smoke_test_passed ? "passed" : "failed"}
            tone={validation.smoke_test_passed ? "text-ready" : "text-crit"}
          />
          <Stat
            label="Benchmark"
            value={validation.benchmark_passed ? "passed" : "failed"}
            tone={validation.benchmark_passed ? "text-ready" : "text-crit"}
          />
        </div>

        <div className="mt-5 flex justify-end">
          <Link
            href={`/runs/${id}/report`}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
          >
            View readiness report →
          </Link>
        </div>
      </section>

      {/* Failure diagnosis — only when the run actually failed */}
      {failed && (
        <section className="rounded-xl border border-ember/40 bg-panel p-6">
          <h2 className="font-display text-sm font-semibold tracking-wide text-ember">
            Failure diagnosis
          </h2>
          {validation.diagnosis ? (
            <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-dim">
              {validation.diagnosis}
            </pre>
          ) : (
            <p className="mt-2 text-sm text-ink-dim">
              The validation run failed — check the log below for the first error.
            </p>
          )}
        </section>
      )}

      {/* Terminal-style log panel */}
      <section className="overflow-hidden rounded-xl border border-edge">
        <div className="flex items-center justify-between border-b border-edge bg-panel px-4 py-2">
          <p className="font-mono text-[11px] text-ink-dim">validation_log.txt</p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
            {validation.mode === "replay" ? "saved amd run" : "live output"}
          </p>
        </div>
        <pre className="max-h-96 overflow-y-auto bg-[#0D0A0C] p-4 font-mono text-xs leading-relaxed text-ink-dim">
          {validation.logs || "No log output."}
        </pre>
      </section>
    </div>
  );
}
