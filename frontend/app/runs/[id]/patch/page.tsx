import { StageStub } from "@/components/stage-stub";

export default function PatchPage() {
  return (
    <StageStub
      title="Patch"
      phase={3}
      willShow={[
        "Unified diff viewer for patch.diff",
        "Artifact tabs: Dockerfile.rocm, smoke_test.py, benchmark.py",
        "Download buttons for every artifact",
      ]}
    />
  );
}
