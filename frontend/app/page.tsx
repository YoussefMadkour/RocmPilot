"use client";

// 01 · Intake — point the cockpit at a repo and start a run.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type RunStage, type RunSummary } from "@/lib/api";
import { CockpitRail } from "@/components/cockpit-rail";

// Where to drop a returning user back into a run — its current stage.
const STAGE_SEGMENT: Record<RunStage, string> = {
  created: "scan",
  scanned: "scan",
  planned: "plan",
  patched: "patch",
  validated: "validate",
  reported: "report",
};

// Verified CUDA-first showcase repos from PROJECT_TRACKER.md.
const SUGGESTED = [
  "https://github.com/karpathy/nanoGPT",
  "https://github.com/ultralytics/yolov5",
  "https://github.com/xinntao/Real-ESRGAN",
  "https://github.com/openai/whisper",
];

export default function IntakePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [busy, setBusy] = useState<"repo" | "sample" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RunSummary[]>([]);

  useEffect(() => {
    api.listRuns().then((runs) => setRecent(runs.slice(0, 5))).catch(() => {});
  }, []);

  async function start(body: { repo_url?: string; use_sample?: boolean }) {
    setBusy(body.use_sample ? "sample" : "repo");
    setError(null);
    try {
      const run = await api.createRun(body);
      router.push(`/runs/${run.run_id}/scan`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the run");
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8 md:flex-row">
      <CockpitRail />
      <main className="min-w-0 flex-1">
        <p className="font-mono text-[11px] tracking-widest text-ink-dim">
          AMD ROCm · MIGRATION COCKPIT
        </p>
        <h1 className="mt-2 font-display text-4xl font-bold leading-tight">
          CUDA-first in.
          <br />
          <span className="text-accent">AMD-ready</span> out.
        </h1>
        <p className="mt-4 max-w-xl text-ink-dim">
          Scan a PyTorch repo for CUDA and NVIDIA blockers, generate safe
          patches and a ROCm container, validate on AMD, and get a readiness
          score you can act on.
        </p>

        <section className="mt-8 max-w-xl rounded-xl border border-edge bg-panel p-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (repoUrl.trim()) start({ repo_url: repoUrl.trim() });
            }}
          >
            <label
              htmlFor="repo-url"
              className="block text-sm font-medium text-ink"
            >
              GitHub repository URL
            </label>
            <div className="mt-2 flex gap-2">
              <input
                id="repo-url"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/karpathy/nanoGPT"
                className="min-w-0 flex-1 rounded-lg border border-edge bg-bay px-3 py-2 font-mono text-sm placeholder:text-ink-dim/50"
                disabled={busy !== null}
              />
              <button
                type="submit"
                disabled={busy !== null || !repoUrl.trim()}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110 disabled:opacity-40"
              >
                {busy === "repo" ? "Cloning…" : "Start run"}
              </button>
            </div>
          </form>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {SUGGESTED.map((url) => (
              <button
                key={url}
                type="button"
                onClick={() => setRepoUrl(url)}
                disabled={busy !== null}
                className="rounded-full border border-edge px-2.5 py-1 font-mono text-[11px] text-ink-dim hover:border-ink-dim hover:text-ink"
              >
                {url.replace("https://github.com/", "")}
              </button>
            ))}
          </div>

          <div className="my-5 flex items-center gap-3 text-[11px] text-ink-dim">
            <span className="h-px flex-1 bg-edge" aria-hidden />
            or
            <span className="h-px flex-1 bg-edge" aria-hidden />
          </div>

          <button
            type="button"
            onClick={() => start({ use_sample: true })}
            disabled={busy !== null}
            className="w-full rounded-lg border border-edge px-4 py-2 text-sm font-medium text-ink hover:border-ink-dim disabled:opacity-40"
          >
            {busy === "sample"
              ? "Loading sample…"
              : "Scan the bundled CUDA-first sample repo"}
          </button>

          {error && (
            <p role="alert" className="mt-4 text-sm text-ember">
              {error} — check that the backend is running on :8000, then try
              again.
            </p>
          )}
        </section>

        {recent.length > 0 && (
          <section className="mt-8 max-w-xl">
            <p className="font-mono text-[11px] uppercase tracking-widest text-ink-dim">
              Recent runs
            </p>
            <ul className="mt-2 divide-y divide-edge/60 rounded-xl border border-edge bg-panel">
              {recent.map((r) => (
                <li key={r.run_id}>
                  <Link
                    href={`/runs/${r.run_id}/${STAGE_SEGMENT[r.stage]}`}
                    className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-edge/30"
                  >
                    <span className="min-w-0 truncate font-mono text-xs text-ink-dim">
                      {r.source.replace("https://github.com/", "").replace("sample:", "sample · ")}
                    </span>
                    <span className="flex shrink-0 items-center gap-3">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-ink-dim">
                        {r.stage}
                      </span>
                      <span className="font-mono text-xs text-ink">
                        {r.score.final ?? r.score.after_planned ?? r.score.before}/100
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <p className="mt-6 font-mono text-[11px] text-ink-dim">
          Deterministic scanner · Fireworks agents optional · AMD validation
          replay-safe
        </p>
      </main>
    </div>
  );
}
