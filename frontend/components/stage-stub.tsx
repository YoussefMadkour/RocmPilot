// Placeholder panel for screens that land in a later phase. Says exactly what
// will appear here so the empty state gives direction, not mood.
export function StageStub({
  title,
  phase,
  willShow,
}: {
  title: string;
  phase: number;
  willShow: string[];
}) {
  return (
    <section className="rounded-xl border border-edge bg-panel p-6">
      <p className="font-mono text-[11px] tracking-widest text-ink-dim">
        INSTRUMENT OFFLINE · LANDS IN PHASE {phase}
      </p>
      <h1 className="mt-2 font-display text-2xl font-semibold">{title}</h1>
      <p className="mt-3 text-sm text-ink-dim">This screen will show:</p>
      <ul className="mt-2 space-y-1.5 text-sm text-ink-dim">
        {willShow.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="text-edge" aria-hidden>
              —
            </span>
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
