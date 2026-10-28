"""Eval preprocessing. MUST stay numerically identical to ``notebooks/_shared/transforms.py::eval_numpy``.

Contract: RGB uint8 -> resize shorter side to 256 (cv2.INTER_LINEAR) -> center crop 224
-> float32/255 -> ImageNet mean/std -> NCHW float32. Parity is enforced by
``tests/test_preprocessing_parity.py``.
"""
from __future__ import annotations

import cv2
import numpy as np

IMAGENET_MEAN = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
IMAGENET_STD = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)
RESIZE_SHORT = 256
CROP = 224


def crop_geometry(h: int, w: int, resize_short: int = RESIZE_SHORT, crop: int = CROP) -> tuple[int, int, int, int]:
    """Resized size and center-crop offsets: ``(new_h, new_w, top, left)``."""
    scale = resize_short / min(h, w)
    new_w = max(crop, int(round(w * scale)))
    new_h = max(crop, int(round(h * scale)))
    return new_h, new_w, (new_h - crop) // 2, (new_w - crop) // 2


def preprocess_rgb(image_rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 ``HxWx3`` -> float32 ``(1, 3, 224, 224)`` batch."""
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError(f"expected HxWx3 RGB array, got {image_rgb.shape}")
    h, w = image_rgb.shape[:2]
    new_h, new_w, top, left = crop_geometry(h, w)
    resized = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    cropped = resized[top : top + CROP, left : left + CROP]
    x = cropped.astype(np.float32) / 255.0
    x = (x - IMAGENET_MEAN) / IMAGENET_STD
    chw = np.ascontiguousarray(x.transpose(2, 0, 1), dtype=np.float32)
    return chw[None]

