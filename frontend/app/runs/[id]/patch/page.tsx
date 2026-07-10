"use client";

// 04 · Patch — generated diff + ROCm artifacts, each viewable and downloadable.
// Diff additions/removals use status colors (ready/crit), never the brand red.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type Artifact } from "@/lib/api";

function DiffView({ text }: { text: string }) {
  return (
    <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed">
      {text.split("\n").map((line, i) => {
        let cls = "text-ink-dim";
        if (line.startsWith("+++") || line.startsWith("---")) cls = "text-ink";
        else if (line.startsWith("@@")) cls = "text-warn";
        else if (line.startsWith("+")) cls = "text-ready";
        else if (line.startsWith("-")) cls = "text-crit";
        return (
          <div key={i} className={cls}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export default function PatchPage() {
  const { id } = useParams<{ id: string }>();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [contents, setContents] = useState<Record<string, string>>({});
  const [active, setActive] = useState<string>("patch.diff");
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!id || started.current) return;
    started.current = true; // avoid double-POST from React strict mode
    api
      .patch(id)
      .then(async (res) => {
        setArtifacts(res.artifacts);
        const loaded = await Promise.all(
          res.artifacts.map((a) =>
            api.artifact(id, a.name).then((r) => [a.name, r.content] as const),
          ),
        );
        setContents(Object.fromEntries(loaded));
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Patch generation failed"),
      );
  }, [id]);

  function download(name: string) {
    const blob = new Blob([contents[name] ?? ""], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Patch</h1>
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

  if (artifacts.length === 0)
    return (
      <section className="rounded-xl border border-edge bg-panel p-6">
        <h1 className="font-display text-2xl font-semibold">Patch</h1>
        <p className="mt-3 font-mono text-sm text-ink-dim">
          <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
          Generating patch.diff and ROCm artifacts…
        </p>
      </section>
    );

  const activeContent = contents[active];

  return (
    <div className="space-y-4">
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-edge bg-panel p-6">
        <div>
          <p className="font-mono text-[11px] tracking-widest text-ink-dim">
            GENERATED ARTIFACTS
          </p>
          <p className="mt-2 text-sm text-ink-dim">
            A conservative device-handling patch plus the three ROCm files the
            repo was missing. Review, download, apply.
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={api.artifactsZipUrl(id)}
            className="rounded-lg border border-edge px-4 py-2 text-sm font-medium hover:border-ink-dim"
          >
            Download all (.zip)
          </a>
          <Link
            href={`/runs/${id}/validate`}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
          >
            Run AMD validation →
          </Link>
        </div>
      </section>

      <section className="rounded-xl border border-edge bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-edge px-4 pt-3">
          <div role="tablist" aria-label="Artifacts" className="flex flex-wrap gap-1">
            {artifacts.map((a) => (
              <button
                key={a.name}
                role="tab"
                aria-selected={active === a.name}
                onClick={() => setActive(a.name)}
                className={`rounded-t-lg border-b-2 px-3 py-2 font-mono text-xs ${
                  active === a.name
                    ? "border-accent text-ink"
                    : "border-transparent text-ink-dim hover:text-ink"
                }`}
              >
                {a.name}
              </button>
            ))}
          </div>
          <button
            onClick={() => download(active)}
            disabled={activeContent == null}
            className="mb-2 rounded-lg border border-edge px-3 py-1.5 text-xs hover:border-ink-dim disabled:opacity-40"
          >
            Download {active}
          </button>
        </div>

        <div className="max-h-[32rem] overflow-y-auto bg-bay">
          {activeContent == null ? (
            <p className="p-4 font-mono text-xs text-ink-dim">
              <span className="led-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ember" />
              Loading {active}…
            </p>
          ) : active === "patch.diff" ? (
            <DiffView text={activeContent} />
          ) : (
            <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed text-ink-dim">
              {activeContent}
            </pre>
          )}
        </div>
      </section>
    </div>
  );
}
