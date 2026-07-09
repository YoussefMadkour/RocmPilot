"""Minimal model definition for the demo (no external weights needed)."""
import torch
import torch.nn as nn


class TinyNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, 10),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_model() -> nn.Module:
    model = TinyNet()
    model.eval()
    # CUDA-first assumption baked into model loading too.
    return model.cuda()
