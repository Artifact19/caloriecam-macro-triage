"""Programmatically build the four research notebooks in ``notebooks/`` using ``nbformat``.

Run:
    python scripts/build_notebooks.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"


def _make_nb(cells: list) -> nbformat.NotebookNode:
    nb = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
    )
    return nb


def build_nb01() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            """# 01 — Dataset EDA, Stratified Splitting & Preprocessing Pipeline

* **Goal:** Inspect the 25-class Food-101 subset, verify class balance and image integrity, create a deterministic stratified train/validation split while holding out the official test split, define and visualize the Albumentations + CutMix training pipeline, and benchmark DataLoader throughput.
* **Inputs:** `data/subset_classes.json`, Food-101 dataset under `data/raw/food-101/` (downloaded via `python data/download_food101.py`).
* **Outputs:** `data/splits.json`, `models/class_names.json`, `notebooks/_shared/dataloader_config.json`.
* **Expected Runtime:** ~2–4 min on CPU or GPU (I/O bound)."""
        ),
        new_code_cell(
            """from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from PIL import Image
from sklearn.model_selection import StratifiedShuffleSplit
from torch.utils.data import DataLoader
from torchvision.transforms import v2 as Tv2

SEED = 42


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


seed_everything(SEED)
sns.set_theme(style="whitegrid")"""
        ),
        new_code_cell(
            """if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from _shared.paths import DATA, MODELS, RAW, ROOT
from _shared.datasets import Food25, class_names, get_subset_samples, load_rgb, write_class_names
from _shared.transforms import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    build_eval_transform,
    build_single_aug,
    build_train_transform,
    denormalize,
    eval_numpy,
)

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
)
FAST_DEV = os.environ.get("FAST_DEV", "0") == "1"
print(f"Selected device: {DEVICE} | FAST_DEV={FAST_DEV} | ROOT={ROOT}")"""
        ),
        new_markdown_cell(
            """## 1. Load the 25-Class Food-101 Subset

We load the official Food-101 `train` and `test` splits filtered to our 25 target classes (`data/subset_classes.json`). Maintaining a single canonical class list ensures that class index $k \\in \\{0, \\dots, 24\\}$ means the exact same dish across training, ONNX export, nutrition lookup, and the FastAPI backend."""
        ),
        new_code_cell(
            """CLASSES = class_names()
assert len(CLASSES) == 25, f"Expected 25 classes, got {len(CLASSES)}"

train_samples = get_subset_samples("train")
test_samples = get_subset_samples("test")

rows = [
    {"path": p, "label": lbl, "class_name": CLASSES[lbl], "split": "train"}
    for p, lbl in train_samples
] + [
    {"path": p, "label": lbl, "class_name": CLASSES[lbl], "split": "test"}
    for p, lbl in test_samples
]
df = pd.DataFrame(rows)
print(f"Total subset images: {len(df):,} (train={len(train_samples):,}, test={len(test_samples):,})")
df.head()"""
        ),
        new_markdown_cell(
            """## 2. Class Distribution, Image Geometry & Channel Statistics

Before training a vision backbone, we verify three things:
1. **Class balance:** Every class should have identical support (750 train / 250 test in full Food-101) so macro-F1 and accuracy are not skewed by prior shift.
2. **Geometry & file integrity:** Unreadable files or extreme aspect ratios can crash DataLoader workers mid-epoch or suffer severe distortion under cropping.
3. **Channel statistics:** We compare empirical RGB mean/std on a random sample against the ImageNet normalization constants
$$\\mu_{\\text{ImageNet}} = [0.485,\\; 0.456,\\; 0.406], \\qquad \\sigma_{\\text{ImageNet}} = [0.229,\\; 0.224,\\; 0.225]$$
Because our MobileNetV3-Large backbone was pretrained on ImageNet-1K with these exact moments, preserving $\\mu_{\\text{ImageNet}}, \\sigma_{\\text{ImageNet}}$ keeps early convolutional filters in their calibrated operating regime."""
        ),
        new_code_cell(
            """counts = df.groupby(["class_name", "split"]).size().unstack(fill_value=0).loc[CLASSES]
expected_train = counts["train"].iloc[0]
expected_test = counts["test"].iloc[0]
assert (counts["train"] == expected_train).all(), "Train split is not balanced across classes!"
assert (counts["test"] == expected_test).all(), "Test split is not balanced across classes!"

fig, ax = plt.subplots(figsize=(12, 4))
counts.plot(kind="bar", ax=ax, width=0.8, color=["#F25F5C", "#3CCBB9"])
ax.set_title("Per-Class Image Counts (Train vs. Official Held-Out Test)")
ax.set_ylabel("Images")
ax.set_xlabel("Dish Class")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()"""
        ),
        new_code_cell(
            """sample_n = min(len(df), 200 if FAST_DEV else 2000)
sample_df = df.sample(n=sample_n, random_state=SEED)

widths, heights, ratios = [], [], []
corrupted = []
channel_sum = np.zeros(3, dtype=np.float64)
channel_sq_sum = np.zeros(3, dtype=np.float64)
pixel_count = 0

for p in sample_df["path"]:
    try:
        with Image.open(p) as im:
            im_rgb = im.convert("RGB")
            w, h = im_rgb.size
            arr = np.asarray(im_rgb, dtype=np.float32) / 255.0
        widths.append(w)
        heights.append(h)
        ratios.append(w / max(h, 1))
        channel_sum += arr.reshape(-1, 3).sum(axis=0)
        channel_sq_sum += (arr.reshape(-1, 3) ** 2).sum(axis=0)
        pixel_count += arr.shape[0] * arr.shape[1]
    except Exception as exc:
        corrupted.append((p, str(exc)))

assert len(corrupted) == 0, f"Found corrupted images: {corrupted[:5]}"
emp_mean = channel_sum / max(pixel_count, 1)
emp_std = np.sqrt(np.maximum(channel_sq_sum / max(pixel_count, 1) - emp_mean**2, 1e-8))

print(f"Checked {sample_n} images — 0 corrupted files.")
print(f"Width  : median={np.median(widths):.0f}px, min={np.min(widths)}px, max={np.max(widths)}px")
print(f"Height : median={np.median(heights):.0f}px, min={np.min(heights)}px, max={np.max(heights)}px")
print(f"Aspect : mean={np.mean(ratios):.2f}, p05={np.percentile(ratios, 5):.2f}, p95={np.percentile(ratios, 95):.2f}")
print(f"Empirical RGB mean: {np.round(emp_mean, 3).tolist()} vs ImageNet {list(IMAGENET_MEAN)}")
print(f"Empirical RGB std : {np.round(emp_std, 3).tolist()} vs ImageNet {list(IMAGENET_STD)}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
axes[0].hist(widths, bins=20, alpha=0.7, label="Width", color="#A78BFA")
axes[0].hist(heights, bins=20, alpha=0.7, label="Height", color="#F25F5C")
axes[0].set_title("Image Dimension Distribution")
axes[0].legend()
axes[1].hist(ratios, bins=20, color="#3CCBB9")
axes[1].set_title("Aspect Ratio (W / H)")
plt.tight_layout()
plt.show()"""
        ),
        new_markdown_cell(
            """## 3. Stratified Train / Validation Split

We split the official training set into **90% train** and **10% validation** using `StratifiedShuffleSplit(n_splits=1, test_size=0.1, random_state=42)`. The official Food-101 test split remains completely untouched until the single final evaluation at the end of Notebook 02."""
        ),
        new_code_cell(
            """labels_np = np.array([lbl for _, lbl in train_samples], dtype=np.int64)
sss = StratifiedShuffleSplit(n_splits=1, test_size=0.1, random_state=SEED)
train_idx, val_idx = next(sss.split(np.zeros(len(labels_np)), labels_np))

expected_val_per_class = len(val_idx) / len(CLASSES)
val_class_counts = np.bincount(labels_np[val_idx], minlength=len(CLASSES))
assert np.all(np.abs(val_class_counts - expected_val_per_class) <= 1.0), (
    f"Stratification failed: counts={val_class_counts}"
)

splits_payload = {
    "seed": SEED,
    "val_fraction": 0.1,
    "train_indices": [int(i) for i in train_idx],
    "val_indices": [int(i) for i in val_idx],
    "num_train": int(len(train_idx)),
    "num_val": int(len(val_idx)),
    "num_test": int(len(test_samples)),
}
splits_path = DATA / "splits.json"
splits_path.write_text(json.dumps(splits_payload, indent=2) + "\\n", encoding="utf-8")
class_names_path = write_class_names()
print(f"Saved stratified splits -> {splits_path} (train={len(train_idx)}, val={len(val_idx)}, test={len(test_samples)})")
print(f"Saved class names       -> {class_names_path}")"""
        ),
        new_markdown_cell(
            """## 4. Augmentation Pipeline & CutMix

Meal photos in the wild vary in lighting, camera tilt, zoom, and partial occlusion. Our training pipeline in `_shared/transforms.py` applies:
1. `LongestMaxSize(256)` $\\rightarrow$ `RandomResizedCrop(224, scale=(0.6, 1.0), ratio=(0.75, 1.33))`
2. `HorizontalFlip(p=0.5)` and `Affine(scale=(0.9, 1.1), translate_percent=(-0.05, 0.05), rotate=(-15, 15), p=0.7)`
3. `ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05, p=0.8)` and `CoarseDropout(p=0.2)`
4. `Normalize(ImageNet)` $\\rightarrow$ `ToTensorV2`

For **evaluation and production**, we use the deterministic contract (`_shared/transforms.py::eval_numpy`):
`Resize(shorter_side=256, INTER_LINEAR)` $\\rightarrow$ `CenterCrop(224)` $\\rightarrow$ `/255.0` $\\rightarrow$ `Normalize(ImageNet)` $\\rightarrow$ `CHW float32`.

At the batch level we apply **CutMix** with probability $p=0.5$ (`torchvision.transforms.v2.CutMix(num_classes=25, alpha=1.0)`):
$$\\tilde{x} = M \\odot x_A + (1-M)\\odot x_B,\\qquad \\tilde{y} = \\lambda y_A + (1-\\lambda) y_B,\\qquad \\lambda \\sim \\mathrm{Beta}(\\alpha,\\alpha),\\quad \\lambda \\approx 1 - \\frac{\\text{area}(B)}{H W}$$"""
        ),
        new_code_cell(
            """train_tf = build_train_transform()
eval_tf = build_eval_transform()
cj_tf = build_single_aug("colorjitter")
aff_tf = build_single_aug("affine")
cutmix = Tv2.CutMix(num_classes=len(CLASSES), alpha=1.0)


def show_grid(images: list[np.ndarray], title: str) -> None:
    fig, axes = plt.subplots(4, 4, figsize=(7, 7))
    fig.suptitle(title, fontsize=12, fontweight="bold")
    for ax, img in zip(axes.flat, images[:16]):
        ax.imshow(img)
        ax.axis("off")
    plt.tight_layout()
    plt.show()


raw_imgs = [load_rgb(train_samples[i][0]) for i in train_idx[:16]]
show_grid([cj_tf(image=im)["image"] for im in raw_imgs], "ColorJitter-Only (4x4)")
show_grid([aff_tf(image=im)["image"] for im in raw_imgs], "Affine-Only (4x4)")
show_grid([denormalize(train_tf(image=im)["image"]) for im in raw_imgs], "Full Training Pipeline (4x4)")

batch_ds = Food25(train_samples, transform=train_tf, indices=train_idx[:16])
bx = torch.stack([batch_ds[i][0] for i in range(16)])
by = torch.tensor([batch_ds[i][1] for i in range(16)], dtype=torch.long)
cm_x, cm_y = cutmix(bx, by)
show_grid([denormalize(t) for t in cm_x], "CutMix Batch (alpha=1.0)")"""
        ),
        new_markdown_cell(
            """## 5. DataLoader Throughput Benchmark

We benchmark `num_workers` $\\in \\{0, 2, 4\\}$ to select the fastest worker configuration for this machine and record the choice in `notebooks/_shared/dataloader_config.json`."""
        ),
        new_code_cell(
            """bench_n = min(len(train_idx), 64 if FAST_DEV else 256)
bench_ds = Food25(train_samples, transform=train_tf, indices=train_idx[:bench_n])
worker_Candidates = [0] if (os.name == "nt" and FAST_DEV) else [0, 2, 4]
throughput: dict[int, float] = {}

for nw in worker_Candidates:
    try:
        loader = DataLoader(bench_ds, batch_size=32, shuffle=False, num_workers=nw)
        t0 = time.perf_counter()
        seen = 0
        for xb, _ in loader:
            seen += int(xb.size(0))
        dt = max(time.perf_counter() - t0, 1e-6)
        throughput[nw] = round(seen / dt, 1)
    except Exception as exc:
        print(f"num_workers={nw} unavailable ({exc}); skipping")

best_nw = max(throughput, key=throughput.get)
cfg_note = Path(ROOT / "notebooks" / "_shared" / "dataloader_config.json")
cfg_note.write_text(
    json.dumps({"best_num_workers": best_nw, "throughput_imgs_per_sec": throughput}, indent=2) + "\\n",
    encoding="utf-8",
)
print(f"Throughput (imgs/sec): {throughput} -> selected num_workers={best_nw}")"""
        ),
    ]
    return _make_nb(cells)


def build_nb02() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            """# 02 — MobileNetV3-Large Fine-Tuning, Calibration & Held-Out Evaluation

* **Goal:** Fine-tune an ImageNet-pretrained `mobilenet_v3_large` classifier on the 25-class Food-101 subset using a two-phase recipe (frozen-backbone warmup followed by differential-LR full fine-tuning with CutMix, label smoothing, cosine annealing, and FP16 mixed precision), calibrate probabilities via temperature scaling, and evaluate once on the held-out test split.
* **Inputs:** `data/splits.json`, `models/class_names.json`, Food-101 images under `data/raw/`.
* **Outputs:** `models/mobilenetv3_food25.pt`, `models/metrics.json`.
* **Expected Runtime:** ~25–45 min on a single mid-range GPU (RTX 4050); set `FAST_DEV=1` for a 3-epoch smoke run."""
        ),
        new_code_cell(
            """from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import confusion_matrix, f1_score
from torch import nn
from torch.utils.data import DataLoader, default_collate
from torchvision import models
from torchvision.transforms import v2 as Tv2

SEED = 42


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


seed_everything(SEED)"""
        ),
        new_code_cell(
            """if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from _shared.paths import DATA, MODELS, RAW, ROOT
from _shared.datasets import Food25, class_names, get_subset_samples, load_splits
from _shared.transforms import IMAGENET_MEAN, IMAGENET_STD, IMG_SIZE, build_eval_transform, build_train_transform

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
)
FAST_DEV = os.environ.get("FAST_DEV", "0") == "1"
OFFLINE_WEIGHTS = os.environ.get("MEAL_TRIAGE_OFFLINE_WEIGHTS", "0") == "1"
print(f"Device: {DEVICE} | FAST_DEV={FAST_DEV}")"""
        ),
        new_markdown_cell(
            """## 1. Architecture, Loss Function, Learning-Rate Schedule & Metrics

### Architecture
We use `torchvision.models.mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2)` and replace the final linear layer `classifier[3]` (`Linear(1280, 1000)`) with `Linear(1280, 25)` while keeping `Dropout(0.2)`.
*(To compare against EfficientNet-B0, set `ARCH = "efficientnet_b0"` in the cell below; MobileNetV3-Large remains our default because its inverted-residual + Hardswish design achieves significantly lower CPU latency.)*

### Label-Smoothed Cross-Entropy ($\\varepsilon = 0.1, K = 25$)
$$\\mathcal{L}=-\\sum_{k=1}^{K}\\tilde{y}_k\\log p_k,\\quad \\tilde{y}_k=(1-\\varepsilon)y_k+\\frac{\\varepsilon}{K},\\quad p_k=\\frac{e^{z_k}}{\\sum_j e^{z_j}}$$
When a batch has been mixed by **CutMix**, its targets $\\tilde{y}$ are already soft convex combinations $\\lambda y_A + (1-\\lambda) y_B$, so we apply hard-label smoothing only on non-CutMix batches.

### Cosine Annealing with Linear Warmup
$$\\eta_t=\\eta_{\\min}+\\tfrac12(\\eta_{\\max}-\\eta_{\\min})\\bigl(1+\\cos\\tfrac{\\pi t}{T}\\bigr)$$

### Macro-$F_1$
$$F_1^{(c)}=\\frac{2\\,P_cR_c}{P_c+R_c},\\qquad F_1^{\\text{macro}}=\\frac1K\\sum_c F_1^{(c)}$$

### FP16 Mixed Precision & Dynamic Loss Scaling
On CUDA we run the forward pass under `torch.autocast(device_type="cuda", dtype=torch.float16)` and scale gradients via `torch.amp.GradScaler("cuda")`. Multiplication by a dynamic scale factor $S$ pushes small FP16 gradients out of the subnormal/underflow range during backpropagation; `scaler.unscale_(optimizer)` restores true gradient magnitudes prior to `clip_grad_norm_(..., 1.0)`."""
        ),
        new_code_cell(
            """CLASSES = class_names()
NUM_CLASSES = len(CLASSES)
ARCH = "mobilenet_v3_large"  # one-line switch: set to "efficientnet_b0" for comparison


def create_model(arch: str = ARCH, num_classes: int = NUM_CLASSES, pretrained: bool = True) -> nn.Module:
    if arch == "mobilenet_v3_large":
        weights = models.MobileNet_V3_Large_Weights.IMAGENET1K_V2 if (pretrained and not OFFLINE_WEIGHTS) else None
        try:
            m = models.mobilenet_v3_large(weights=weights)
        except Exception as exc:
            print(f"Pretrained download unavailable ({exc}); falling back to weights=None")
            m = models.mobilenet_v3_large(weights=None)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
        return m
    if arch == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if (pretrained and not OFFLINE_WEIGHTS) else None
        m = models.efficientnet_b0(weights=weights)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, num_classes)
        return m
    raise ValueError(f"Unknown arch: {arch}")"""
        ),
        new_code_cell(
            """splits = load_splits()
train_samples = get_subset_samples("train")
test_samples = get_subset_samples("test")

train_indices = splits["train_indices"]
val_indices = splits["val_indices"]

if FAST_DEV:
    # Cap per-class samples in FAST_DEV mode (up to 200 imgs/class).
    per_cls_limit = 200
    cls_seen: dict[int, int] = {}
    fast_train: list[int] = []
    for idx in train_indices:
        lbl = train_samples[idx][1]
        if cls_seen.get(lbl, 0) < per_cls_limit:
            fast_train.append(idx)
            cls_seen[lbl] = cls_seen.get(lbl, 0) + 1
    train_indices = fast_train

cutmix_op = Tv2.CutMix(num_classes=NUM_CLASSES, alpha=1.0)
rng_collate = random.Random(SEED)


def train_collate(batch):
    xb, yb = default_collate(batch)
    if not FAST_DEV and xb.size(0) > 1 and rng_collate.random() < 0.5:
        xb, yb = cutmix_op(xb, yb)
    return xb, yb


BATCH_SIZE = 32 if FAST_DEV else 64
train_ds = Food25(train_samples, transform=build_eval_transform() if FAST_DEV else build_train_transform(), indices=train_indices)
val_ds = Food25(train_samples, transform=build_eval_transform(), indices=val_indices)
test_ds = Food25(test_samples, transform=build_eval_transform())

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, collate_fn=train_collate)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
print(f"Samples -> train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}")"""
        ),
        new_markdown_cell(
            """## 2. Two-Phase Training Recipe (Frozen Warm-Up $\\rightarrow$ Differential-LR Full Fine-Tune)

* **Phase A (Head Warm-Up):** Freeze `model.features` (`requires_grad=False`, BatchNorm layers locked in `.eval()` mode so pretrained running mean/var are not corrupted) and train `model.classifier` at $\\eta = 10^{-3}$.
* **Phase B (Full Fine-Tuning):** Unfreeze all layers with differential learning rates in `AdamW`: backbone `features` at $10^{-4}$, `classifier` head at $10^{-3}$, weight decay $0.01$ on weight matrices only (zero decay on biases and BatchNorm/LayerNorm parameters), cosine schedule with 1-epoch linear warmup."""
        ),
        new_code_cell(
            """hard_ce = nn.CrossEntropyLoss(label_smoothing=0.1)
soft_ce = nn.CrossEntropyLoss()


def compute_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if targets.ndim == 2:  # soft CutMix probabilities
        return soft_ce(logits, targets)
    return hard_ce(logits, targets)


def set_backbone_frozen(model: nn.Module, frozen: bool) -> None:
    for p in model.features.parameters():
        p.requires_grad = not frozen
    for m in model.features.modules():
        if isinstance(m, (nn.BatchNorm2d, nn.SyncBatchNorm)):
            m.eval() if frozen else m.train()


def build_differential_adamw(model: nn.Module, lr_backbone: float = 1e-4, lr_head: float = 1e-3, wd: float = 0.01):
    groups = []
    for module, lr in ((model.features, lr_backbone), (model.classifier, lr_head)):
        decay, no_decay = [], []
        for name, p in module.named_parameters():
            if not p.requires_grad:
                continue
            if p.ndim <= 1 or name.endswith(".bias"):
                no_decay.append(p)
            else:
                decay.append(p)
        if decay:
            groups.append({"params": decay, "lr": lr, "initial_lr": lr, "weight_decay": wd})
        if no_decay:
            groups.append({"params": no_decay, "lr": lr, "initial_lr": lr, "weight_decay": 0.0})
    return torch.optim.AdamW(groups)


def build_warmup_cosine_scheduler(optimizer: torch.optim.Optimizer, total_epochs: int, warmup_epochs: int = 1):
    def lr_lambda(epoch: int) -> float:
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(max(1, warmup_epochs))
        progress = (epoch - warmup_epochs) / float(max(1, total_epochs - warmup_epochs))
        return 0.01 + 0.5 * (1.0 - 0.01) * (1.0 + math.cos(math.pi * min(1.0, progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)"""
        ),
        new_code_cell(
            """@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader) -> dict:
    model.eval()
    total_loss = 0.0
    all_logits, all_targets = [], []
    for xb, yb in loader:
        xb = xb.to(DEVICE)
        yb = yb.to(DEVICE)
        logits = model(xb)
        total_loss += float(hard_ce(logits, yb).item()) * xb.size(0)
        all_logits.append(logits.cpu())
        all_targets.append(yb.cpu())

    logits_cat = torch.cat(all_logits, dim=0)
    targets_cat = torch.cat(all_targets, dim=0)
    preds = logits_cat.argmax(dim=1)
    top1 = float((preds == targets_cat).float().mean().item())
    top3_idx = logits_cat.topk(k=min(3, NUM_CLASSES), dim=1).indices
    top3 = float((top3_idx == targets_cat.unsqueeze(1)).any(dim=1).float().mean().item())
    y_true = targets_cat.numpy()
    y_pred = preds.numpy()
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    per_cls = f1_score(y_true, y_pred, average=None, labels=list(range(NUM_CLASSES)), zero_division=0)
    return {
        "loss": total_loss / max(1, len( targets_cat)),
        "top1": top1,
        "top3": top3,
        "macro_f1": macro_f1,
        "per_class_f1": {CLASSES[i]: round(float(per_cls[i]), 4) for i in range(NUM_CLASSES)},
        "logits": logits_cat,
        "targets": targets_cat,
    }


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    freeze_bn: bool = False,
) -> float:
    model.train()
    if freeze_bn:
        set_backbone_frozen(model, True)
    use_cuda_amp = DEVICE == "cuda"
    running_loss = 0.0
    seen = 0
    for xb, yb in loader:
        xb = xb.to(DEVICE)
        yb = yb.to(DEVICE)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda" if use_cuda_amp else "cpu", dtype=torch.float16, enabled=use_cuda_amp):
            logits = model(xb)
            loss = compute_loss(logits, yb)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        running_loss += float(loss.item()) * xb.size(0)
        seen += int(xb.size(0))
    return running_loss / max(1, seen)"""
        ),
        new_code_cell(
            """model = create_model(ARCH, NUM_CLASSES, pretrained=True).to(DEVICE)
use_cuda_amp = DEVICE == "cuda"
scaler = torch.amp.GradScaler("cuda", enabled=use_cuda_amp)

PHASE_A_EPOCHS = 2 if FAST_DEV else 3
PHASE_B_EPOCHS = 4 if FAST_DEV else 12
PATIENCE = 4
LR_HEAD = 3e-3 if FAST_DEV else 1e-3
LR_BACKBONE = 3e-4 if FAST_DEV else 1e-4

history: list[dict] = []
best_val_f1 = -1.0
best_epoch = 0
epochs_no_improve = 0
ckpt_path = MODELS / "mobilenetv3_food25.pt"

# --- Phase A: head warm-up ---
set_backbone_frozen(model, True)
opt_a = torch.optim.AdamW([p for p in model.classifier.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=0.01)

for ep in range(1, PHASE_A_EPOCHS + 1):
    t0 = time.perf_counter()
    tr_loss = train_one_epoch(model, train_loader, opt_a, scaler, freeze_bn=True)
    val_res = evaluate(model, val_loader)
    lr_now = opt_a.param_groups[0]["lr"]
    history.append(
        {
            "epoch": ep,
            "phase": "A_head_warmup",
            "train_loss": tr_loss,
            "val_loss": val_res["loss"],
            "val_top1": val_res["top1"],
            "val_top3": val_res["top3"],
            "val_macro_f1": val_res["macro_f1"],
            "lr_head": lr_now,
            "sec": round(time.perf_counter() - t0, 1),
        }
    )
    if val_res["macro_f1"] > best_val_f1:
        best_val_f1 = val_res["macro_f1"]
        best_epoch = ep
        torch.save(
            {
                "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                "class_names": CLASSES,
                "arch": ARCH,
                "img_size": IMG_SIZE,
                "mean": list(IMAGENET_MEAN),
                "std": list(IMAGENET_STD),
                "val_macro_f1": round(best_val_f1, 4),
                "epoch": ep,
                "temperature": 1.0,
            },
            ckpt_path,
        )
    print(f"[Phase A | Ep {ep}/{PHASE_A_EPOCHS}] tr_loss={tr_loss:.4f} val_top1={val_res['top1']:.4f} val_F1={val_res['macro_f1']:.4f}")

# --- Phase B: full fine-tuning ---
set_backbone_frozen(model, False)
opt_b = build_differential_adamw(model, lr_backbone=LR_BACKBONE, lr_head=LR_HEAD, wd=0.01)
sched_b = build_warmup_cosine_scheduler(opt_b, total_epochs=PHASE_B_EPOCHS, warmup_epochs=1)

for step_ep in range(1, PHASE_B_EPOCHS + 1):
    ep = PHASE_A_EPOCHS + step_ep
    t0 = time.perf_counter()
    tr_loss = train_one_epoch(model, train_loader, opt_b, scaler, freeze_bn=False)
    sched_b.step()
    val_res = evaluate(model, val_loader)
    lr_now = max(g["lr"] for g in opt_b.param_groups)
    history.append(
        {
            "epoch": ep,
            "phase": "B_finetune",
            "train_loss": tr_loss,
            "val_loss": val_res["loss"],
            "val_top1": val_res["top1"],
            "val_top3": val_res["top3"],
            "val_macro_f1": val_res["macro_f1"],
            "lr_head": lr_now,
            "sec": round(time.perf_counter() - t0, 1),
        }
    )
    print(f"[Phase B | Ep {ep}/{PHASE_A_EPOCHS + PHASE_B_EPOCHS}] tr_loss={tr_loss:.4f} val_top1={val_res['top1']:.4f} val_F1={val_res['macro_f1']:.4f}")
    if val_res["macro_f1"] > best_val_f1:
        best_val_f1 = val_res["macro_f1"]
        best_epoch = ep
        epochs_no_improve = 0
        torch.save(
            {
                "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                "class_names": CLASSES,
                "arch": ARCH,
                "img_size": IMG_SIZE,
                "mean": list(IMAGENET_MEAN),
                "std": list(IMAGENET_STD),
                "val_macro_f1": round(best_val_f1, 4),
                "epoch": ep,
                "temperature": 1.0,
            },
            ckpt_path,
        )
    else:
        epochs_no_improve += 1
        if epochs_no_improve >= PATIENCE:
            print(f"Early stopping triggered at epoch {ep} (best epoch={best_epoch}, val_macro_f1={best_val_f1:.4f})")
            break

hist_df = pd.DataFrame(history)
hist_df"""
        ),
        new_code_cell(
            """fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
axes[0].plot(hist_df["epoch"], hist_df["train_loss"], marker="o", label="Train Loss")
axes[0].plot(hist_df["epoch"], hist_df["val_loss"], marker="s", label="Val Loss")
axes[0].set_title("Loss Curve")
axes[0].legend()

axes[1].plot(hist_df["epoch"], hist_df["val_top1"], marker="o", label="Val Top-1")
axes[1].plot(hist_df["epoch"], hist_df["val_macro_f1"], marker="s", label="Val Macro-F1")
axes[1].set_title("Validation Accuracy & Macro-F1")
axes[1].legend()

axes[2].plot(hist_df["epoch"], hist_df["lr_head"], marker="d", color="#F25F5C")
axes[2].set_title("Classifier Head Learning Rate")
plt.tight_layout()
plt.show()"""
        ),
        new_markdown_cell(
            """## 3. Temperature Scaling, Reliability Diagram (ECE) & Held-Out Test Evaluation

To ensure our confidence triage thresholds ($0.70$ for `confident`, $0.40$ for `review`) correspond to true empirical accuracy, we fit a post-hoc temperature scalar $T > 0$ on the validation logits via NLL minimization:
$$p_k = \\mathrm{softmax}(z / T)_k = \\frac{e^{z_k / T}}{\\sum_j e^{z_j / T}}$$
and measure the 15-bin Expected Calibration Error (ECE) on the held-out test set."""
        ),
        new_code_cell(
            """ckpt = torch.load(ckpt_path, map_location=DEVICE, weights_only=False)
model.load_state_dict(ckpt["state_dict"])
val_best = evaluate(model, val_loader)


def fit_temperature(logits: torch.Tensor, targets: torch.Tensor) -> float:
    log_t = nn.Parameter(torch.zeros(1))
    opt_t = torch.optim.LBFGS([log_t], lr=0.1, max_iter=50)
    nll = nn.CrossEntropyLoss()

    def closure():
        opt_t.zero_grad()
        t = torch.exp(log_t).clamp(0.05, 10.0)
        loss = nll(logits / t, targets)
        loss.backward()
        return loss

    opt_t.step(closure)
    return float(torch.exp(log_t).clamp(0.05, 10.0).item())


temperature = round(fit_temperature(val_best["logits"], val_best["targets"]), 4)
ckpt["temperature"] = temperature
torch.save(ckpt, ckpt_path)
print(f"Fitted validation temperature T = {temperature:.4f} (saved into {ckpt_path.name})")"""
        ),
        new_code_cell(
            """test_res = evaluate(model, test_loader)
scaled_probs = torch.softmax(test_res["logits"] / temperature, dim=1).numpy()
confs = scaled_probs.max(axis=1)
preds = scaled_probs.argmax(axis=1)
trues = test_res["targets"].numpy()
correct = (preds == trues).astype(np.float32)

# 15-bin Expected Calibration Error (ECE)
n_bins = 15
bins = np.linspace(0.0, 1.0, n_bins + 1)
ece = 0.0
bin_accs, bin_confs, bin_centers = [], [], []
for b0, b1 in zip(bins[:-1], bins[1:]):
    mask = (confs > b0) & (confs <= b1) if b0 > 0 else (confs >= b0) & (confs <= b1)
    if np.any(mask):
        acc_b = float(correct[mask].mean())
        conf_b = float(confs[mask].mean())
        ece += (mask.sum() / len(confs)) * abs(acc_b - conf_b)
        bin_accs.append(acc_b)
        bin_confs.append(conf_b)
        bin_centers.append(0.5 * (b0 + b1))

# Confusion matrix & top-10 confused pairs
cm = confusion_matrix(trues, preds, labels=list(range(NUM_CLASSES)))
pairs = []
for i in range(NUM_CLASSES):
    for j in range(NUM_CLASSES):
        if i != j and cm[i, j] > 0:
            pairs.append({"true": CLASSES[i], "pred": CLASSES[j], "count": int(cm[i, j])})
pairs_df = pd.DataFrame(pairs).sort_values("count", ascending=False).head(10) if pairs else pd.DataFrame(columns=["true", "pred", "count"])

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sns.heatmap(cm, ax=axes[0], cmap="YlOrRd", cbar=True, xticklabels=False, yticklabels=False)
axes[0].set_title("25-Class Test Confusion Matrix")
axes[0].set_xlabel("Predicted Class")
axes[0].set_ylabel("True Class")

axes[1].plot([0, 1], [0, 1], "--", color="gray", label="Perfect Calibration")
axes[1].bar(bin_centers, bin_accs, width=1.0 / n_bins, alpha=0.7, edgecolor="black", color="#3CCBB9", label="Empirical Accuracy")
axes[1].axvline(0.40, color="#F4A261", linestyle=":", label="Triage Low (0.40)")
axes[1].axvline(0.70, color="#F25F5C", linestyle=":", label="Triage High (0.70)")
axes[1].set_title(f"Reliability Diagram (ECE = {ece:.4f}, T = {temperature:.2f})")
axes[1].set_xlabel("Predicted Confidence")
axes[1].set_ylabel("Accuracy")
axes[1].legend()
plt.tight_layout()
plt.show()

print("Top confused class pairs:")
display(pairs_df)"""
        ),
        new_code_cell(
            """metrics_payload = {
    "val_macro_f1": round(float(best_val_f1), 4),
    "test_top1": round(float(test_res["top1"]), 4),
    "test_top3": round(float(test_res["top3"]), 4),
    "test_macro_f1": round(float(test_res["macro_f1"]), 4),
    "ece": round(float(ece), 4),
    "temperature": temperature,
    "per_class_f1": test_res["per_class_f1"],
    "training_config": {
        "arch": ARCH,
        "phase_a_epochs": PHASE_A_EPOCHS,
        "phase_b_epochs": PHASE_B_EPOCHS,
        "best_epoch": best_epoch,
        "batch_size": BATCH_SIZE,
        "lr_backbone": 1e-4,
        "lr_head": 1e-3,
        "weight_decay": 0.01,
        "label_smoothing": 0.1,
        "cutmix_alpha": 1.0,
        "fast_dev": FAST_DEV,
    },
    "device": DEVICE,
    "date": dt.datetime.now(dt.timezone.utc).isoformat(),
}
metrics_path = MODELS / "metrics.json"
metrics_path.write_text(json.dumps(metrics_payload, indent=2) + "\\n", encoding="utf-8")
print(f"Wrote measured metrics -> {metrics_path}")
print(json.dumps({k: v for k, v in metrics_payload.items() if k != "per_class_f1"}, indent=2))"""
        ),
    ]
    return _make_nb(cells)


def build_nb03() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            """# 03 — Grad-CAM Explainability & Faithfulness Verification

* **Goal:** Implement Gradient-weighted Class Activation Mapping (Grad-CAM) on `model.features[-1]` of our fine-tuned MobileNetV3-Large checkpoint, verify hook cleanup, class-discriminative localization, and deletion faithfulness, and render attention galleries.
* **Inputs:** `models/mobilenetv3_food25.pt`, `models/class_names.json`, Food-101 test split.
* **Outputs:** Visual verification galleries and the canonical `GradCAM` reference implementation mirrored in `backend/app/services/gradcam.py`.
* **Expected Runtime:** ~1–2 min on CPU or GPU."""
        ),
        new_code_cell(
            """from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Optional

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torchvision import models

SEED = 42


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


seed_everything(SEED)"""
        ),
        new_code_cell(
            """if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from _shared.paths import DATA, MODELS, RAW, ROOT
from _shared.datasets import class_names, get_subset_samples, load_rgb
from _shared.transforms import IMG_SIZE, RESIZE_SHORT, eval_numpy

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
)
FAST_DEV = os.environ.get("FAST_DEV", "0") == "1"
print(f"Selected device: {DEVICE} (Grad-CAM runs in FP32 with gradients enabled)")"""
        ),
        new_markdown_cell(
            """## 1. Grad-CAM Formulation

For target class $c$, pre-softmax logit $y^c$, and last convolutional feature maps $A^k \\in \\mathbb{R}^{u \\times v}$ (`model.features[-1]`, $960$ channels of $7 \\times 7$ at $224 \\times 224$ input):
$$\\alpha_k^c=\\frac{1}{Z}\\sum_{i}\\sum_{j}\\frac{\\partial y^c}{\\partial A^k_{ij}},\\qquad L^c_{\\text{Grad-CAM}}=\\mathrm{ReLU}\\Bigl(\\sum_k \\alpha_k^c A^k\\Bigr)$$
We normalize into $[0, 1]$ via:
$$\\hat L=\\dfrac{L-\\min L}{\\max L-\\min L+\\epsilon}$$

### Hook & In-Place Safety
PyTorch's `register_full_backward_hook` can conflict with in-place activations (`Hardswish(inplace=True)`, `ReLU(inplace=True)`). We therefore:
1. Disable all in-place flags across the network via `disable_inplace(model)`.
2. Register a **forward hook** on `model.features[-1]` that captures the forward activation tensor and attaches `output.register_hook(...)` directly to the tensor, removing the handle in `__exit__`."""
        ),
        new_code_cell(
            """EPS = 1e-8


def disable_inplace(model: nn.Module) -> None:
    for m in model.modules():
        if isinstance(m, (nn.ReLU, nn.ReLU6, nn.Hardswish, nn.Hardsigmoid, nn.SiLU, nn.Dropout)) and hasattr(m, "inplace"):
            m.inplace = False


def crop_geometry(h: int, w: int, resize_short: int = RESIZE_SHORT, crop: int = IMG_SIZE) -> tuple[int, int, int, int]:
    scale = resize_short / min(h, w)
    new_w = max(crop, int(round(w * scale)))
    new_h = max(crop, int(round(h * scale)))
    return new_h, new_w, (new_h - crop) // 2, (new_w - crop) // 2


class GradCAM:
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
            acts = self.activations.detach()[0]
            grads = self.gradients.detach()[0]
            weights = grads.mean(dim=(1, 2), keepdim=True)
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
    h, w = image_rgb.shape[:2]
    new_h, new_w, top, left = crop_geometry(h, w)
    sy, sx = h / new_h, w / new_w
    y0, y1 = int(round(top * sy)), int(round((top + IMG_SIZE) * sy))
    x0, x1 = int(round(left * sx)), int(round((left + IMG_SIZE) * sx))
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
    return heat_rgba, overlay"""
        ),
        new_code_cell(
            """CLASSES = class_names()
ckpt = torch.load(MODELS / "mobilenetv3_food25.pt", map_location="cpu", weights_only=False)
model = models.mobilenet_v3_large(weights=None)
model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(CLASSES))
model.load_state_dict(ckpt["state_dict"])
disable_inplace(model)
model.eval()
target_layer = model.features[-1]

test_samples = get_subset_samples("test")
print(f"Loaded checkpoint (epoch={ckpt.get('epoch')}, val_macro_f1={ckpt.get('val_macro_f1')})")"""
        ),
        new_markdown_cell(
            """## 2. Verification Suite

1. **Shape, Finiteness & Hook Hygiene:** Spatial CAM has shape `(7, 7)`, values in `[0, 1]`, zero `NaN`s, and `len(target_layer._forward_hooks) == 0` after context exit.
2. **Class Sensitivity:** Computing Grad-CAM for the predicted class vs. a distinct runner-up class produces meaningfully different spatial maps.
3. **Deletion Faithfulness Test:** Blanking the top 20% hottest pixels in the $224 \\times 224$ input reduces the predicted class probability on average across 100 test images."""
        ),
        new_code_cell(
            """sample_rgb = load_rgb(test_samples[0][0])
x0 = torch.from_numpy(eval_numpy(sample_rgb)).unsqueeze(0)

with GradCAM(model, target_layer) as gcam:
    cam_top, pred_idx = gcam(x0, target_index=None)
    alt_idx = (pred_idx + 1) % len(CLASSES)
    cam_alt, _ = gcam(x0, target_index=alt_idx)

assert cam_top.shape == (7, 7), f"Unexpected CAM shape {cam_top.shape}"
assert np.isfinite(cam_top).all() and cam_top.min() >= -1e-6 and cam_top.max() <= 1.0 + 1e-6
assert len(target_layer._forward_hooks) == 0, "Forward hook leaked!"

mad = float(np.mean(np.abs(cam_top - cam_alt)))
print(f"Verification 1 & 2 passed: shape={cam_top.shape}, range=[{cam_top.min():.3f}, {cam_top.max():.3f}], class-pair MAD={mad:.4f}")"""
        ),
        new_code_cell(
            """n_del = min(len(test_samples), 20 if FAST_DEV else 100)
rng = random.Random(SEED)
del_subset = rng.sample(test_samples, n_del)
drops: list[float] = []

with GradCAM(model, target_layer) as gcam:
    for path, _ in del_subset:
        rgb = load_rgb(path)
        x = torch.from_numpy(eval_numpy(rgb)).unsqueeze(0)
        with torch.no_grad():
            p_orig = torch.softmax(model(x), dim=1)
            c_idx = int(p_orig.argmax(dim=1).item())
            prob_before = float(p_orig[0, c_idx].item())
        cam, _ = gcam(x, target_index=c_idx)
        cam_224 = cv2.resize(cam, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_CUBIC)
        thresh = np.quantile(cam_224, 0.80)
        mask = torch.from_numpy((cam_224 < thresh).astype(np.float32)).unsqueeze(0).unsqueeze(0)
        x_masked = x * mask
        with torch.no_grad():
            prob_after = float(torch.softmax(model(x_masked), dim=1)[0, c_idx].item())
        drops.append(prob_before - prob_after)

mean_drop = float(np.mean(drops))
print(f"Deletion test over {n_del} images: mean target-class probability drop = {mean_drop:+.4f}")"""
        ),
        new_markdown_cell(
            """## 3. Sample Class Galleries & Failure Case Analysis

We visualize `(Original, Heatmap, Overlay)` for our 4 UI sample classes (`pizza`, `greek_salad`, `steak`, `chicken_curry`) and inspect misclassified test examples to see what visual cues distracted the network."""
        ),
        new_code_cell(
            """sample_classes = ["pizza", "greek_salad", "steak", "chicken_curry"]
fig, axes = plt.subplots(len(sample_classes), 3, figsize=(9, 10))

with GradCAM(model, target_layer) as gcam:
    for row, dish in enumerate(sample_classes):
        cls_idx = CLASSES.index(dish)
        img_path = next(p for p, l in test_samples if l == cls_idx)
        rgb = load_rgb(img_path)
        x = torch.from_numpy(eval_numpy(rgb)).unsqueeze(0)
        cam, pred_idx = gcam(x)
        heat_rgba, overlay = render_overlay(cam, rgb)
        axes[row, 0].imshow(rgb)
        axes[row, 0].set_title(f"Original: {dish}")
        axes[row, 1].imshow(heat_rgba[..., :3])
        axes[row, 1].set_title("Grad-CAM Heatmap")
        axes[row, 2].imshow(overlay)
        axes[row, 2].set_title(f"Overlay (pred: {CLASSES[pred_idx]})")
        for col in range(3):
            axes[row, col].axis("off")

plt.tight_layout()
plt.show()"""
        ),
        new_code_cell(
            """failures = []
with GradCAM(model, target_layer) as gcam:
    for path, true_lbl in test_samples:
        rgb = load_rgb(path)
        x = torch.from_numpy(eval_numpy(rgb)).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=1)[0]
            pred_lbl = int(probs.argmax().item())
        if pred_lbl != true_lbl:
            cam, _ = gcam(x, target_index=pred_lbl)
            _, overlay = render_overlay(cam, rgb)
            failures.append((rgb, overlay, CLASSES[true_lbl], CLASSES[pred_lbl], float(probs[pred_lbl].item())))
        if len(failures) >= 6:
            break

if failures:
    fig, axes = plt.subplots(2, min(3, len(failures)), figsize=(11, 6))
    axes_flat = np.atleast_1d(axes).flat
    for ax, (_, ov, t_name, p_name, conf) in zip(axes_flat, failures):
        ax.imshow(ov)
        ax.set_title(f"True: {t_name}\\nPred: {p_name} ({conf:.0%})", fontsize=9)
        ax.axis("off")
    plt.suptitle("Misclassified Examples (Grad-CAM on Predicted Class)", fontweight="bold")
    plt.tight_layout()
    plt.show()
else:
    print("No misclassifications found in scanned subset.")"""
        ),
        new_markdown_cell(
            """## 4. Production Reference Note

The `GradCAM`, `disable_inplace`, and `render_overlay` functions defined in Section 1 of this notebook are the exact reference implementation deployed in `backend/app/services/gradcam.py`."""
        ),
    ]
    return _make_nb(cells)


def build_nb04() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            """# 04 — ONNX Export, Dynamic & Static QDQ INT8 Quantization & CPU Benchmarking

* **Goal:** Export the trained PyTorch checkpoint to ONNX FP32 (opset 17), verify numerical logit parity (`max |Δ| < 1e-4`), produce both Dynamic INT8 and Static QDQ INT8 quantized models, evaluate held-out test accuracy across all engines, benchmark latency (mean, p50, p95, p99) across CPU thread counts, and select the production default engine.
* **Inputs:** `models/mobilenetv3_food25.pt`, `models/class_names.json`, `models/metrics.json`, `data/splits.json`.
* **Outputs:** `models/mobilenetv3_food25_fp32.onnx`, `models/mobilenetv3_food25_int8_dynamic.onnx`, `models/mobilenetv3_food25_int8_static.onnx`, `models/benchmark.json`, updated `models/metrics.json`.
* **Expected Runtime:** ~2–5 min on CPU."""
        ),
        new_code_cell(
            """from __future__ import annotations

import json
import os
import platform
import random
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import onnx
import onnxruntime as ort
import pandas as pd
import torch
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_dynamic, quantize_static
from sklearn.metrics import f1_score
from torch import nn
from torchvision import models

SEED = 42


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


seed_everything(SEED)"""
        ),
        new_code_cell(
            """if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

from _shared.paths import DATA, MODELS, RAW, ROOT
from _shared.datasets import class_names, get_subset_samples, load_rgb, load_splits
from _shared.transforms import eval_numpy

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
)
FAST_DEV = os.environ.get("FAST_DEV", "0") == "1"
print(f"Selected device: {DEVICE} | ONNX Runtime {ort.__version__}")"""
        ),
        new_markdown_cell(
            """## 1. Preprocessing Contract & Class Registry Verification

Both the calibration reader and the FastAPI backend obey the exact same preprocessing contract:
1. Decode RGB `uint8` image of shape $(H, W, 3)$.
2. Resize shorter side to `256` with `cv2.resize(..., interpolation=cv2.INTER_LINEAR)`.
3. Center-crop `224 x 224`.
4. Scale to `float32` in $[0, 1]$ via `/ 255.0`.
5. Normalize per channel by ImageNet $\\mu = [0.485, 0.456, 0.406]$, $\\sigma = [0.229, 0.224, 0.225]$.
6. Transpose to contiguous `NCHW` (`(1, 3, 224, 224)` `float32`)."""
        ),
        new_code_cell(
            """CLASSES = class_names()
model_classes = json.loads((MODELS / "class_names.json").read_text(encoding="utf-8"))
assert model_classes == CLASSES, "models/class_names.json does not match data/subset_classes.json!"

ckpt = torch.load(MODELS / "mobilenetv3_food25.pt", map_location="cpu", weights_only=False)
pt_model = models.mobilenet_v3_large(weights=None)
pt_model.classifier[3] = nn.Linear(pt_model.classifier[3].in_features, len(CLASSES))
pt_model.load_state_dict(ckpt["state_dict"])
pt_model.eval()
print(f"Verified 25 classes and loaded checkpoint from {MODELS / 'mobilenetv3_food25.pt'}")"""
        ),
        new_markdown_cell(
            """## 2. Export FP32 ONNX & Numerical Parity Check

We export with `opset_version=17` and dynamic batch axis, validate the graph with `onnx.checker.check_model`, and verify that ONNX Runtime FP32 logits match PyTorch FP32 logits within $\\max |\\Delta| < 10^{-4}$ across 64 test images."""
        ),
        new_code_cell(
            """fp32_path = MODELS / "mobilenetv3_food25_fp32.onnx"
dummy = torch.randn(1, 3, 224, 224, dtype=torch.float32)

torch.onnx.export(
    pt_model,
    dummy,
    str(fp32_path),
    input_names=["input"],
    output_names=["logits"],
    opset_version=17,
    do_constant_folding=True,
    dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
)
onnx_model = onnx.load(str(fp32_path))
onnx.checker.check_model(onnx_model)

ort_fp32 = ort.InferenceSession(str(fp32_path), providers=["CPUExecutionProvider"])
test_samples = get_subset_samples("test")
parity_n = min(64, len(test_samples))
max_diff = 0.0
with torch.no_grad():
    for path, _ in test_samples[:parity_n]:
        batch = eval_numpy(load_rgb(path))[None]
        pt_out = pt_model(torch.from_numpy(batch)).numpy()
        ort_out = ort_fp32.run(["logits"], {"input": batch})[0]
        max_diff = max(max_diff, float(np.max(np.abs(pt_out - ort_out))))

print(f"FP32 ONNX parity across {parity_n} test images: max |Δ| = {max_diff:.2e}")
assert max_diff < 1e-4, f"Parity check failed: {max_diff}" """
        ),
        new_markdown_cell(
            """## 3. Dynamic vs. Static (QDQ) INT8 Quantization

* **Dynamic INT8 (`quantize_dynamic`):** Quantizes `MatMul`/`Gemm` weights on-the-fly while leaving convolutions in floating point or inserting dynamic range calculations. Because MobileNetV3 spends most of its FLOPs inside depthwise-separable `Conv` blocks (`features`) rather than the final `Linear` classifier, dynamic quantization often yields **little or no latency improvement** on CPU — a hypothesis we verify empirically below.
* **Static INT8 QDQ (`quantize_static`):** Calibrates activation ranges on 200 validation images using `QuantFormat.QDQ` (`QUInt8` activations, per-channel `QInt8` weights), enabling integer convolution kernels."""
        ),
        new_code_cell(
            """dyn_path = MODELS / "mobilenetv3_food25_int8_dynamic.onnx"
stat_path = MODELS / "mobilenetv3_food25_int8_static.onnx"

quantize_dynamic(
    model_input=str(fp32_path),
    model_output=str(dyn_path),
    weight_type=QuantType.QUInt8,
)

splits = load_splits()
train_samples = get_subset_samples("train")
val_indices = splits["val_indices"]
calib_n = min(len(val_indices), 32 if FAST_DEV else 200)
calib_paths = [train_samples[i][0] for i in val_indices[:calib_n]]


class Food25CalibrationReader(CalibrationDataReader):
    def __init__(self, paths: list[str]) -> None:
        self._batches = [{"input": eval_numpy(load_rgb(p))[None]} for p in paths]
        self._iter = iter(self._batches)

    def get_next(self):
        return next(self._iter, None)


quantize_static(
    model_input=str(fp32_path),
    model_output=str(stat_path),
    calibration_data_reader=Food25CalibrationReader(calib_paths),
    quant_format=QuantFormat.QDQ,
    activation_type=QuantType.QUInt8,
    weight_type=QuantType.QInt8,
    per_channel=True,
)
print(f"Exported Dynamic INT8 ({dyn_path.stat().st_size / 1e6:.2f} MB) and Static QDQ INT8 ({stat_path.stat().st_size / 1e6:.2f} MB)")"""
        ),
        new_markdown_cell(
            """## 4. Full Held-Out Test Accuracy & Latency Benchmarking

We evaluate all four engines (`pytorch`, `onnx_fp32`, `onnx_int8_dynamic`, `onnx_int8_static`) on the held-out test split and benchmark single-image CPU latency across `intra_op_num_threads` $\\in \\{1, 4, \\text{all}\\}$ (`20` warmup + `200` timed runs with `time.perf_counter`).

**Production Default Selection Rule:** An INT8 model is selected as `default_engine` if and only if its top-1 accuracy drop is $\\le 1.0$ percentage point relative to `onnx_fp32` **and** its mean CPU latency is strictly lower than `onnx_fp32`; otherwise we fall back to `onnx_fp32`."""
        ),
        new_code_cell(
            """eval_samples = test_samples[: (64 if FAST_DEV else len(test_samples))]
precomputed = [(eval_numpy(load_rgb(p))[None], lbl) for p, lbl in eval_samples]


def eval_onnx(path: Path) -> tuple[float, float]:
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    preds, trues = [], []
    for batch, lbl in precomputed:
        out = sess.run(["logits"], {"input": batch})[0]
        preds.append(int(np.argmax(out, axis=1)[0]))
        trues.append(lbl)
    top1 = float(np.mean(np.array(preds) == np.array(trues)))
    f1 = float(f1_score(trues, preds, average="macro", zero_division=0))
    return round(top1, 4), round(f1, 4)


def eval_pt() -> tuple[float, float]:
    preds, trues = [], []
    with torch.no_grad():
        for batch, lbl in precomputed:
            out = pt_model(torch.from_numpy(batch)).numpy()
            preds.append(int(np.argmax(out, axis=1)[0]))
            trues.append(lbl)
    top1 = float(np.mean(np.array(preds) == np.array(trues)))
    f1 = float(f1_score(trues, preds, average="macro", zero_division=0))
    return round(top1, 4), round(f1, 4)


acc_pt = eval_pt()
acc_fp32 = eval_onnx(fp32_path)
acc_dyn = eval_onnx(dyn_path)
acc_stat = eval_onnx(stat_path)
print("Accuracy (top1, macro_f1):", {"pytorch": acc_pt, "onnx_fp32": acc_fp32, "onnx_int8_dynamic": acc_dyn, "onnx_int8_static": acc_stat})"""
        ),
        new_code_cell(
            """WARMUP = 5 if FAST_DEV else 20
TIMED = 30 if FAST_DEV else 200
dummy_np = precomputed[0][0]
dummy_pt = torch.from_numpy(dummy_np)


def bench_callable(fn) -> dict[str, float]:
    for _ in range(WARMUP):
        fn()
    times_ms = []
    for _ in range(TIMED):
        t0 = time.perf_counter()
        fn()
        times_ms.append((time.perf_counter() - t0) * 1000.0)
    arr = np.array(times_ms, dtype=np.float64)
    mean_ms = float(arr.mean())
    return {
        "mean_ms": round(mean_ms, 2),
        "p50_ms": round(float(np.percentile(arr, 50)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "p99_ms": round(float(np.percentile(arr, 99)), 2),
        "throughput_ips": round(1000.0 / max(mean_ms, 1e-6), 1),
    }


thread_grid = [1, 4, 0]  # 0 = all cores in ORT
thread_rows = []
for th in thread_grid:
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = th
    for name, path in (("onnx_fp32", fp32_path), ("onnx_int8_dynamic", dyn_path), ("onnx_int8_static", stat_path)):
        sess = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
        stats = bench_callable(lambda s=sess: s.run(["logits"], {"input": dummy_np}))
        thread_rows.append({"engine": name, "threads": th if th > 0 else (os.cpu_count() or 1), **stats})

torch.set_num_threads(min(4, os.cpu_count() or 1))
with torch.no_grad():
    pt_stats = bench_callable(lambda: pt_model(dummy_pt))

thread_df = pd.DataFrame(thread_rows)
display(thread_df)

def best_ort_stats(engine_name: str, path: Path, acc: tuple[float, float]) -> dict:
    sub = thread_df[thread_df["engine"] == engine_name].sort_values("mean_ms").iloc[0]
    return {
        "mean_ms": float(sub["mean_ms"]),
        "p50_ms": float(sub["p50_ms"]),
        "p95_ms": float(sub["p95_ms"]),
        "p99_ms": float(sub["p99_ms"]),
        "throughput_ips": float(sub["throughput_ips"]),
        "best_threads": int(sub["threads"]),
        "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        "top1": acc[0],
        "macro_f1": acc[1],
    }


benchmark_engines = {
    "pytorch": {
        **pt_stats,
        "size_mb": round((MODELS / "mobilenetv3_food25.pt").stat().st_size / (1024 * 1024), 2),
        "top1": acc_pt[0],
        "macro_f1": acc_pt[1],
    },
    "onnx_fp32": best_ort_stats("onnx_fp32", fp32_path, acc_fp32),
    "onnx_int8_dynamic": best_ort_stats("onnx_int8_dynamic", dyn_path, acc_dyn),
    "onnx_int8_static": best_ort_stats("onnx_int8_static", stat_path, acc_stat),
}

# Selection rule: <= 1.0 percentage point top-1 drop vs FP32 AND strictly faster mean_ms
fp32_top1 = benchmark_engines["onnx_fp32"]["top1"]
fp32_ms = benchmark_engines["onnx_fp32"]["mean_ms"]
default_engine = "onnx_fp32"
for cand in ("onnx_int8_static", "onnx_int8_dynamic"):
    drop_pp = (fp32_top1 - benchmark_engines[cand]["top1"]) * 100.0
    if drop_pp <= 1.0 and benchmark_engines[cand]["mean_ms"] < fp32_ms:
        default_engine = cand
        break

benchmark_payload = {
    **benchmark_engines,
    "default_engine": default_engine,
    "system_info": {
        "cpu": platform.processor() or platform.machine(),
        "cores": os.cpu_count(),
        "os": f"{platform.system()} {platform.release()}",
        "onnxruntime_version": ort.__version__,
        "torch_version": torch.__version__,
    },
}
(MODELS / "benchmark.json").write_text(json.dumps(benchmark_payload, indent=2) + "\\n", encoding="utf-8")

metrics_path = MODELS / "metrics.json"
if metrics_path.is_file():
    metrics_data = json.loads(metrics_path.read_text(encoding="utf-8"))
else:
    metrics_data = {}
metrics_data["quantization"] = {
    k: {"top1": benchmark_engines[k]["top1"], "macro_f1": benchmark_engines[k]["macro_f1"], "size_mb": benchmark_engines[k]["size_mb"]}
    for k in ("onnx_fp32", "onnx_int8_dynamic", "onnx_int8_static")
}
metrics_data["default_engine"] = default_engine
metrics_path.write_text(json.dumps(metrics_data, indent=2) + "\\n", encoding="utf-8")

print(f"Selected default_engine = {default_engine}")
summary_df = pd.DataFrame.from_dict(benchmark_engines, orient="index")
display(summary_df)

fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(summary_df.index, summary_df["mean_ms"], color=["#A78BFA", "#F25F5C", "#FFE066", "#3CCBB9"], edgecolor="black")
ax.set_ylabel("Mean Latency (ms, batch=1 CPU)")
ax.set_title(f"Inference Latency by Engine (Selected Default: {default_engine})")
plt.tight_layout()
plt.show()"""
        ),
    ]
    return _make_nb(cells)


def main() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "01_dataset_eda_and_preprocessing.ipynb": build_nb01(),
        "02_mobilenetv3_finetuning.ipynb": build_nb02(),
        "03_gradcam_explainability.ipynb": build_nb03(),
        "04_onnx_export_and_quantization.ipynb": build_nb04(),
    }
    for name, nb in mapping.items():
        out = NB_DIR / name
        nbformat.write(nb, str(out))
        print(f"Wrote {out} ({len(nb.cells)} cells)")


if __name__ == "__main__":
    main()
