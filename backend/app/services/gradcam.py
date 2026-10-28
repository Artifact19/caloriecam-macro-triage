"""Grad-CAM (canonical implementation; mirrors notebook 03's reference cell).

Math, for target class ``c`` and last-conv activations ``A^k``::

    alpha_k^c = mean_ij d y^c / d A^k_ij        L^c = ReLU(sum_k alpha_k^c A^k)
    L_hat = (L - min L) / (max L - min L + eps)

``y^c`` is the *pre-softmax logit*. Hooks are registered in ``__enter__`` and always removed in
``__exit__`` (no leaks). A forward hook stores the activation and registers a tensor hook to
capture its gradient, which avoids the in-place / ``register_backward_hook`` pitfalls.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import torch
from torch import nn

from .preprocessing import CROP, RESIZE_SHORT, crop_geometry

EPS = 1e-8


def disable_inplace(model: nn.Module) -> None:
    """Set ``inplace=False`` on every activation that supports it."""
    for m in model.modules():
        if isinstance(m, (nn.ReLU, nn.ReLU6, nn.Hardswish, nn.Hardsigmoid, nn.SiLU, nn.Dropout)) and hasattr(m, "inplace"):
            m.inplace = False


class GradCAM:
    """Context manager computing Grad-CAM on ``layer`` of ``model``."""

    def __init__(self, model: nn.Module, layer: nn.Module) -> None:
        self.model = model
        self.layer = layer
        self._handle: Optional[torch.utils.hooks.RemovableHandle] = None
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None

    def __enter__(self) -> "GradCAM":
        def forward_hook(_module: nn.Module, _inp: tuple, output: torch.Tensor) -> None:
            self.activations = output
            if output.requires_grad:
                output.register_hook(self._save_grad)

        self._handle = self.layer.register_forward_hook(forward_hook)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._handle is not None:
            self._handle.remove()
            self._handle = None
        self.activations = None
        self.gradients = None

    def _save_grad(self, grad: torch.Tensor) -> None:
        self.gradients = grad

    def __call__(self, x: torch.Tensor, target_index: Optional[int] = None) -> tuple[np.ndarray, int]:
        """Return ``(cam in [0,1] with shape (u, v), target_index)`` for a ``(1,3,H,W)`` batch."""
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.enable_grad():
                self.model.zero_grad(set_to_none=True)
                logits = self.model(x)
                if target_index is None:
                    target_index = int(logits.argmax(dim=1).item())
                score = logits[0, target_index]
                score.backward()
            if self.activations is None or self.gradients is None:
                raise RuntimeError("Grad-CAM hooks did not capture activations/gradients.")
            acts = self.activations.detach()[0]  # (K, u, v)
            grads = self.gradients.detach()[0]  # (K, u, v)
            weights = grads.mean(dim=(1, 2), keepdim=True)  # alpha_k^c
            cam = torch.relu((weights * acts).sum(dim=0))
            cam = (cam - cam.min()) / (cam.max() - cam.min() + EPS)
            return cam.cpu().numpy().astype(np.float32), int(target_index)
        finally:
            self.model.zero_grad(set_to_none=True)
            self.model.train(was_training)


def render_overlay(
    cam: np.ndarray,
    image_rgb: np.ndarray,
    alpha: float = 0.5,
    blur_ksize: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Turn a model-space CAM into display images aligned with ``image_rgb``.

    The network only sees the centered 224 crop of the 256-resized image, so the CAM is
    placed on that region of the original and left at zero (transparent) elsewhere.

    Returns ``(heatmap_rgba, overlay_rgb)`` as uint8 arrays with ``image_rgb``'s size. The RGBA
    heatmap uses the JET colormap with alpha = normalised intensity.
    """
    h, w = image_rgb.shape[:2]
    new_h, new_w, top, left = crop_geometry(h, w)
    # crop rectangle expressed in original-image pixels
    sy, sx = h / new_h, w / new_w
    y0, y1 = int(round(top * sy)), int(round((top + CROP) * sy))
    x0, x1 = int(round(left * sx)), int(round((left + CROP) * sx))
    y1, x1 = max(y1, y0 + 1), max(x1, x0 + 1)

    region = cv2.resize(cam, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    full = np.zeros((h, w), dtype=np.float32)
    full[y0:y1, x0:x1] = np.clip(region, 0.0, 1.0)
    if blur_ksize and blur_ksize > 1:
        full = cv2.GaussianBlur(full, (blur_ksize, blur_ksize), 0)
    full = np.clip(full, 0.0, 1.0)

    cam_u8 = (full * 255).astype(np.uint8)
    heat_bgr = cv2.applyColorMap(cam_u8, cv2.COLORMAP_JET)
    heat_rgb = cv2.cvtColor(heat_bgr, cv2.COLOR_BGR2RGB)
    heat_rgba = np.dstack([heat_rgb, cam_u8])

    blended = cv2.addWeighted(image_rgb, 1.0 - alpha, heat_rgb, alpha, 0)
    mask = (full > 0)[..., None]
    overlay = np.where(mask, blended, image_rgb).astype(np.uint8)
    return heat_rgba, overlay


__all__ = ["GradCAM", "disable_inplace", "render_overlay", "RESIZE_SHORT"]

