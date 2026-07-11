# AMD / ROCm — where it fits and how to run on it

RocmPilot touches AMD in **three** layers, not one:

1. **The AI runs on AMD.** Every reasoning agent (Planner=DeepSeek-v4-pro,
   Critic=GLM-5.2, Research=Kimi-k2.6) and the RAG embeddings run through the
   **Fireworks AI API, which hosts these models on AMD Instinct GPUs.** So the
   whole agent orchestra is AMD-accelerated inference.
2. **Validation runs on real AMD hardware.** The generated `Dockerfile.rocm`
   (rocm/pytorch base), `smoke_test.py`, and `benchmark.py` build and execute on an
   **AMD MI300X via AMD Developer Cloud**. This is the hardware proof.
3. **The output targets ROCm.** Patches, the ROCm container, and the kernel-risk
   classifier (wavefront64, HIPIFY, rocWMMA, hipBLAS/MIOpen/rocFFT/RCCL) all speak
   AMD/ROCm.

Everything except layer 2 runs anywhere (CPU/laptop). Layer 2 needs an AMD GPU.

---

## Setup

### 1. Fireworks (the AMD-hosted AI) — required for live agents/RAG
```bash
# in backend/.env
FIREWORKS_API_KEY=fw_...
QDRANT_URL=https://<cluster>.cloud.qdrant.io      # for RAG (optional)
QDRANT_API_KEY=...
cd backend && python -m app.knowledge.ingest       # build the ROCm knowledge base once
```
Without a key the pipeline still runs (deterministic fallbacks) — you just don't
get the live LLM reasoning.

### 2. AMD Developer Cloud (the real GPU) — for validation
Provision an MI300X instance with ROCm + Docker. Confirm the GPU is visible:
```bash
rocminfo | grep -i "Marketing Name"     # -> AMD Instinct MI300X
python -c "import torch; print(torch.cuda.is_available(), torch.version.hip)"
```

## Testing on AMD — two ways

### A. Capture a run → replay (demo-safe, recommended for the demo)
On the AMD box, from the repo root:
```bash
bash scripts/capture_amd_run.sh
```
It runs the smoke test + benchmark in a `rocm/pytorch` container (with
`--device=/dev/kfd --device=/dev/dri --group-add video`) and writes
`backend/app/fixtures/validation_log.txt` + `benchmark.json`. Commit those; the
Validate screen's `replay` now shows genuine MI300X numbers (always labeled as a
saved run — we never fake it).

### B. Live mode (end-to-end on the AMD host)
Run the backend **on the AMD box** and set:
```bash
VALIDATION_MODE=live
```
Now `POST /api/runs/{id}/validate` will `docker build` the generated
`Dockerfile.rocm` and run the smoke test + benchmark on the GPU, parsing real
stdout into the result. If Docker/GPU aren't reachable it falls back to the saved
run with a clear note — so a demo never dead-ends.

## Quick verification
```bash
# on the AMD box
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  --security-opt seccomp=unconfined rocm/pytorch:latest \
  python -c "import torch; assert torch.cuda.is_available(); print('HIP', torch.version.hip, torch.cuda.get_device_name(0))"
```
