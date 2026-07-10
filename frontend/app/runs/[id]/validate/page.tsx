import { StageStub } from "@/components/stage-stub";

export default function ValidatePage() {
  return (
    <StageStub
      title="Validate"
      phase={3}
      willShow={[
        "AMD validation card: GPU name, ROCm/HIP status, latency",
        "Terminal-style log panel",
        "Replay-mode badge (a saved AMD run is always labeled)",
        "Failure diagnosis panel when a run fails",
      ]}
    />
  );
}
