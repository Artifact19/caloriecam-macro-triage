"""Food25 PyTorch Dataset + helpers (backed by ``data/download_food101.get_subset_samples``)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import torch
from PIL import Image

from .paths import DATA, MODELS, RAW, ROOT

if str(ROOT / "data") not in sys.path:
    sys.path.insert(0, str(ROOT / "data"))

import download_food101 as _dl  # noqa: E402  (data/download_food101.py)


def class_names() -> list[str]:
    """Ordered class names; single source of truth is ``data/subset_classes.json``."""
    return _dl.load_subset_classes(ROOT / "data" / "subset_classes.json")


def get_subset_samples(split: str) -> list[tuple[str, int]]:
    """``[(path, label)]`` for the 25-class subset in the official Food-101 ``split``."""
    return _dl.get_subset_samples(split, root=RAW, classes_path=ROOT / "data" / "subset_classes.json")


def load_rgb(path: str | Path) -> np.ndarray:
    """Read an image as HxWx3 uint8 RGB."""
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


class Food25(torch.utils.data.Dataset):
    """Minimal map-style dataset over ``(path, label)`` pairs.

    ``transform`` receives an RGB uint8 ndarray. If it is an Albumentations ``Compose`` the
    ``{"image": ...}`` dict protocol is used; otherwise it is called directly.
    """

    def __init__(
        self,
        samples: Sequence[tuple[str, int]],
        transform: Callable | None = None,
        indices: Sequence[int] | None = None,
    ) -> None:
        self.samples = list(samples)
        self.indices = list(indices) if indices is not None else list(range(len(self.samples)))
        self.transform = transform

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, i: int):
        path, label = self.samples[self.indices[i]]
        img = load_rgb(path)
        if self.transform is not None:
            if hasattr(self.transform, "processors"):  # albumentations Compose
                img = self.transform(image=img)["image"]
            else:
                img = self.transform(img)
        return img, label


def load_splits() -> dict:
    """Read ``data/splits.json`` produced by notebook 01."""
    return json.loads((DATA / "splits.json").read_text(encoding="utf-8"))


def write_class_names() -> Path:
    """Write ``models/class_names.json`` (identical, ordered copy of subset_classes.json)."""
    out = MODELS / "class_names.json"
    out.write_text(json.dumps(class_names(), indent=2) + "\n", encoding="utf-8")
    return out
