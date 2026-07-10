import { StageStub } from "@/components/stage-stub";

export default function ReportPage() {
  return (
    <StageStub
      title="Report"
      phase={4}
      willShow={[
        "Before / after readiness score comparison",
        "Rendered Markdown readiness report",
        "Generated artifact list",
        "Report download",
      ]}
    />
  );
}
