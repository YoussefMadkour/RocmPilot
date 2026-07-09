#!/usr/bin/env bash
set -euo pipefail

# NVIDIA-specific runtime invocation.
nvidia-smi
docker run --gpus all -e NVIDIA_VISIBLE_DEVICES=all cuda-first-demo
