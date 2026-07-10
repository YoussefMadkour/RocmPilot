# Benchmark repos

Real repos we calibrate the scanner + readiness score against. The clones live in
`benchmark_repos/` at the repo root — **gitignored** (large 3rd-party sources, no
need to vendor them). Re-hydrate them anytime with the script at the bottom.

Scores below are the **honest "before"** scores from the current scoring model
(see `backend/app/services/scoring_service.py`), captured 2026-07-10.

## Two tiers

RocmPilot's honest scoring naturally splits repos into two buckets:

### Tier 1 — application repos (ROCm-transparent) — WORK ON THESE FIRST
High-level PyTorch apps. ROCm maps `'cuda'`/`.cuda()` transparently, so they're
mostly ready — RocmPilot's job is containerize → validate → optimize (the
"one-stop shop" path). These are the demo/dev targets.

| Repo | before | What it is |
|------|-------:|------------|
| [nanoGPT](https://github.com/karpathy/nanoGPT) | ~67 | Minimal GPT training/finetuning. **Primary demo repo.** |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | ~65 | Image/video super-resolution (very visual). |
| [YOLOv5](https://github.com/ultralytics/yolov5) | ~55 | Real-time object detection; ships an NVIDIA Dockerfile. |

### Tier 2 — kernel/infra libraries (custom CUDA) — DEFERRED
Ship hand-written CUDA kernels that must be HIPified/ported by hand. Flagged as
`manual_blocker` in v1, not auto-solved. **Kept offline for later** — we tackle
these only once the Tier 1 pipeline produces good end-to-end results.

| Repo | before | What it is |
|------|-------:|------------|
| [detectron2](https://github.com/facebookresearch/detectron2) | ~12 | Detection/segmentation platform; custom C++/CUDA ops. |
| [mmcv](https://github.com/open-mmlab/mmcv) | ~16 | OpenMMLab foundation lib; many custom CUDA ops. |
| [flash-attention](https://github.com/Dao-AILab/flash-attention) | ~17 | Memory-efficient attention; ~entirely custom CUDA kernels. |
| [apex](https://github.com/NVIDIA/apex) | ~25 | NVIDIA mixed-precision/distributed training; custom kernels. |

## Plan
1. Get the full flow (scan → plan → patch → validate → report) polished on **Tier 1**.
2. Only then take on **Tier 2** — custom-kernel porting is the hard, high-risk work.

## Re-hydrate the clones
```bash
mkdir -p benchmark_repos && cd benchmark_repos
for r in karpathy/nanoGPT ultralytics/yolov5 xinntao/Real-ESRGAN \
         facebookresearch/detectron2 open-mmlab/mmcv \
         Dao-AILab/flash-attention NVIDIA/apex; do
  git clone --depth 1 --single-branch "https://github.com/$r"
done
```
