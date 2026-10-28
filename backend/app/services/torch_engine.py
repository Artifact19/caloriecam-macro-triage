"""PyTorch model wrapper: plain classification and Grad-CAM (always fp32 on CPU)."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from torch import nn
from torchvision import models

from .gradcam import GradCAM, disable_inplace


def build_model(arch: str, num_classes: int) -> nn.Module:
    """Rebuild the fine-tuned architecture (no pretrained download)."""
    if arch == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights=None)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
    elif arch == "efficientnet_b0":
        m = models.efficientnet_b0(weights=None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"Unsupported arch '{arch}'")
    return m


def load_checkpoint(path: Path) -> dict[str, Any]:
    """Load the notebook checkpoint dict (state_dict + metadata)."""
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except Exception:  # metadata containing non-tensor objects (e.g. numpy scalars)
        return torch.load(path, map_location="cpu", weights_only=False)


class TorchEngine:
    """Holds the eval-mode model. Grad-CAM is serialised with a lock (hooks are per-model state)."""

    def __init__(self, checkpoint_path: Path, class_names: Optional[list[str]] = None) -> None:
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        ckpt = load_checkpoint(Path(checkpoint_path))
        self.metadata = {k: v for k, v in ckpt.items() if k != "state_dict"}
        names = class_names or list(ckpt.get("class_names", []))
        if not names:
            raise ValueError("Checkpoint has no class_names and none were supplied.")
        self.arch: str = ckpt.get("arch", "mobilenet_v3_large")
        self.model = build_model(self.arch, len(names))
        self.model.load_state_dict(ckpt["state_dict"])
        disable_inplace(self.model)
        self.model.eval()
        self.target_layer: nn.Module = self.model.features[-1]
        self._lock = threading.Lock()

    @property
    def temperature(self) -> Optional[float]:
        t = self.metadata.get("temperature")
        return float(t) if t is not None else None

    @torch.inference_mode()
    def predict_logits(self, batch: np.ndarray) -> np.ndarray:
        x = torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32))
        return self.model(x).cpu().numpy().astype(np.float32)

    def gradcam(self, batch: np.ndarray, target_index: Optional[int] = None) -> tuple[np.ndarray, int]:
        """Grad-CAM for a ``(1,3,H,W)`` batch. Returns ``(cam in [0,1], target_index)``."""
        x = torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32))
        with self._lock:
            with GradCAM(self.model, self.target_layer) as cam:
                return cam(x, target_index)

    def warmup(self) -> None:
        dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
        self.predict_logits(dummy)
        self.gradcam(dummy, 0)

