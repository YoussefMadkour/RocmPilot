# AMD / ROCm — where it fits and how to run on it

RocmPilot touches AMD in **three** layers, not one:

1. **The AI runs on AMD.** Every reasoning agent (Planner=DeepSeek-v4-pro,
   Critic=GLM-5.2, Research=Kimi-k2.6) and the RAG embeddings run through the
   **Fireworks AI API, which hosts these models on AMD Instinct GPUs.** So the
   whole agent orchestra is AMD-accelerated inference.
2. **Validation runs on real AMD hardware.** The generated `Dockerfile.rocm`
   (rocm/pytorch base), `smoke_test.py`, and `benchmark.py` build and execute on an
   **a real AMD GPU via AMD Developer Cloud** (Radeon gfx1100 in the hackathon notebook; Instinct MI300X on Instinct hosts). This is the hardware proof.
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
Provision an AMD GPU instance (Radeon or Instinct) with ROCm. Confirm the GPU is visible:
```bash
rocminfo | grep -i "Marketing Name"     # -> your AMD GPU (e.g. Radeon gfx1100 or Instinct MI300X)
python -c "import torch; print(torch.cuda.is_available(), torch.version.hip)"
```

## Testing on AMD — two ways

### A. Capture a run → replay (demo-safe, recommended for the demo)

**On an AMD box with Docker** (repo cloned):
```bash
bash scripts/capture_amd_run.sh
```

**In an AMD AI Notebook / Jupyter Lab (no Docker)** — use the self-contained
single file `scripts/amd_capture.py`. Upload it and run any of:
```bash
python amd_capture.py        # Lab terminal
%run amd_capture.py          # notebook cell
```
It only needs `torch`, runs the same smoke test + benchmark, and writes
`validation_log.txt` + `benchmark.json` in RocmPilot's exact format.

Either way, copy the two files into `backend/app/fixtures/` and commit them; the
Validate screen's `replay` then shows genuine AMD-GPU numbers (always labeled as a
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
