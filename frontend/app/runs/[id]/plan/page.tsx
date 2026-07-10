import { StageStub } from "@/components/stage-stub";

export default function PlanPage() {
  return (
    <StageStub
      title="Plan"
      phase={2}
      willShow={[
        "Migration summary from the planner agent",
        "Prioritized actions with severity and patch type",
        "Manual blockers that need a human",
        "Agent activity timeline",
      ]}
    />
  );
}
