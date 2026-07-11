#!/usr/bin/env bash
# Capture a REAL AMD (MI300X) validation run into the repo's fixtures, so `replay`
# mode reflects genuine hardware and `live` mode has a format to parse.
#
# Run this ON an AMD Developer Cloud box (ROCm + Docker installed), from the repo
# root. It runs the generated smoke test + benchmark inside a rocm/pytorch
# container using the same device flags RocmPilot's Dockerfile documents.
#
#   bash scripts/capture_amd_run.sh
#
# Then commit backend/app/fixtures/validation_log.txt + benchmark.json.
set -euo pipefail

WORK="$(mktemp -d)"
cp backend/app/templates/smoke_test.py.template "$WORK/smoke_test.py"
cp backend/app/templates/benchmark.py.template  "$WORK/benchmark.py"

IMAGE="${ROCM_IMAGE:-rocm/pytorch:latest}"
echo ">> Using image: $IMAGE"

docker run --rm \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --security-opt seccomp=unconfined \
  -v "$WORK:/work" -w /work \
  "$IMAGE" bash -lc '
    { echo "=== RocmPilot AMD Validation (LIVE — AMD Developer Cloud) ===";
      echo "Runtime    : $(cat /opt/rocm/.info/version 2>/dev/null || echo ROCm)";
      echo;
      echo "$ rocminfo | grep -i \"Marketing Name\"";
      rocminfo | grep -i "Marketing Name" | head -1;
      echo;
      echo "$ python smoke_test.py --require-gpu";
      python smoke_test.py --require-gpu;
      echo;
      echo "$ python benchmark.py";
      python benchmark.py;
    } | tee /work/validation_log.txt
  '

cp "$WORK/validation_log.txt" backend/app/fixtures/validation_log.txt
[ -f "$WORK/benchmark.json" ] && cp "$WORK/benchmark.json" backend/app/fixtures/benchmark.json

echo
echo ">> Captured to backend/app/fixtures/. Commit them; replay now shows a real MI300X run."
