# cuda_first_transformers_demo

A deliberately **CUDA-first** PyTorch inference project used as RocmPilot Studio's
demo input. It is packed with NVIDIA/CUDA assumptions so the scanner has something
real to find:

- `torch.device("cuda")` and `.to("cuda")` with no availability check
- `torch.cuda.get_device_name(0)` at startup
- `FROM nvidia/cuda:...` base image
- `nvidia-smi`, `--gpus all`, `NVIDIA_VISIBLE_DEVICES` in `run.sh`
- CUDA-only wheels (`torch==2.4.0+cu121`, `cupy-cuda12x`)
- No ROCm Dockerfile, no smoke test, no benchmark

Run RocmPilot against this project to see it flagged, patched, and validated.
