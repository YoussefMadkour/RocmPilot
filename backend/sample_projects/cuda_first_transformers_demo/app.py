"""Tiny CUDA-first inference server. Deliberately NVIDIA-locked for the demo."""
import torch

from model import load_model


def main() -> None:
    # CUDA-first: hardcoded device, no availability check.
    device = torch.device("cuda")
    print("Using device:", torch.cuda.get_device_name(0))

    model = load_model()
    model.to("cuda")

    dummy = torch.randn(1, 128).to("cuda")
    with torch.no_grad():
        out = model(dummy)
    print("Inference output shape:", tuple(out.shape))


if __name__ == "__main__":
    main()
