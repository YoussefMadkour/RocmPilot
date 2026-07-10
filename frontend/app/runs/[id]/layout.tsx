import { CockpitRail } from "@/components/cockpit-rail";

export default async function RunLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8 md:flex-row">
      <CockpitRail runId={id} />
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
