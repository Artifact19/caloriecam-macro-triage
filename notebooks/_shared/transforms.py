"""Albumentations pipelines and the numpy eval transform (production contract).

The *eval* transform is the preprocessing contract shared with the backend:

    RGB uint8 HxWx3 -> resize shorter side to 256 (cv2.INTER_LINEAR, no antialias)
    -> center crop 224x224 -> float32 / 255 -> (x - mean) / std -> CHW float32

``eval_numpy`` is the reference implementation. ``backend/app/services/preprocessing.py``
must stay numerically identical (verified by ``test_preprocessing_parity.py``).
"""
from __future__ import annotations

import cv2
import numpy as np

IMAGENET_MEAN: tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: tuple[float, float, float] = (0.229, 0.224, 0.225)
RESIZE_SHORT: int = 256
IMG_SIZE: int = 224


def eval_numpy(
    image_rgb: np.ndarray,
    resize_short: int = RESIZE_SHORT,
    crop: int = IMG_SIZE,
    mean: tuple[float, float, float] = IMAGENET_MEAN,
    std: tuple[float, float, float] = IMAGENET_STD,
) -> np.ndarray:
    """Deterministic eval preprocessing. Returns a ``(3, crop, crop)`` float32 array."""
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError(f"expected HxWx3 RGB array, got shape {image_rgb.shape}")
    h, w = image_rgb.shape[:2]
    scale = resize_short / min(h, w)
    new_w = max(crop, int(round(w * scale)))
    new_h = max(crop, int(round(h * scale)))
    resized = cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    top = (new_h - crop) // 2
    left = (new_w - crop) // 2
    cropped = resized[top : top + crop, left : left + crop]
    x = cropped.astype(np.float32) / 255.0
    x = (x - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)
    return np.ascontiguousarray(x.transpose(2, 0, 1), dtype=np.float32)


class EvalNumpyTransform:
    """Albumentations-free callable wrapper used by the Dataset for val/test."""

    def __call__(self, image: np.ndarray):
        import torch

        return torch.from_numpy(eval_numpy(image))


def build_train_transform(img_size: int = IMG_SIZE):
    """Training augmentation pipeline (Albumentations 1.4.x). Returns a callable on RGB uint8 arrays."""
    import albumentations as A
    from albumentations.pytorch import ToTensorV2

    return A.Compose(
        [
            A.LongestMaxSize(max_size=256),
            A.RandomResizedCrop(size=(img_size, img_size), scale=(0.6, 1.0), ratio=(0.75, 1.33)),
            A.HorizontalFlip(p=0.5),
            A.Affine(scale=(0.9, 1.1), translate_percent=(-0.05, 0.05), rotate=(-15, 15), p=0.7),
            A.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05, p=0.8),
            A.CoarseDropout(
                num_holes_range=(1, 4),
                hole_height_range=(16, 40),
                hole_width_range=(16, 40),
                fill=0,
                p=0.2,
            ),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]
    )


def build_single_aug(name: str, img_size: int = IMG_SIZE):
    """Individual augmentation (for the EDA visual grids): 'colorjitter' | 'affine'."""
    import albumentations as A

    base = [A.LongestMaxSize(max_size=256), A.CenterCrop(img_size, img_size)]
    if name == "colorjitter":
        base.append(A.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05, p=1.0))
    elif name == "affine":
        base.append(A.Affine(scale=(0.9, 1.1), translate_percent=(-0.05, 0.05), rotate=(-15, 15), p=1.0))
    else:
        raise ValueError(name)
    return A.Compose(base)


def build_eval_transform():
    """Eval transform as a callable ``np.ndarray(RGB uint8) -> torch.Tensor`` (see ``eval_numpy``)."""
    return EvalNumpyTransform()


def denormalize(t, mean=IMAGENET_MEAN, std=IMAGENET_STD):
    """Invert normalisation of a CHW tensor/array into an HxWx3 uint8 image (for plots)."""
    arr = t.detach().cpu().numpy() if hasattr(t, "detach") else np.asarray(t)
    arr = arr.transpose(1, 2, 0) * np.asarray(std) + np.asarray(mean)
    return (np.clip(arr, 0, 1) * 255).astype(np.uint8)

