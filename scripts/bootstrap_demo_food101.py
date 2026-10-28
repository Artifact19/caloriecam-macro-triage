"""Create a lightweight, torchvision-compatible Food-101 bootstrap dataset under ``data/raw/food-101/``.

Why this exists:
- The full Food-101 archive is ~5 GB. To make the repository immediately runnable offline and allow
  headless execution of notebooks 01 -> 04 (`python scripts/run_notebooks.py --fast`) before downloading
  5 GB, this script generates a compact Food-101 directory (`meta/classes.txt`, `meta/train.json`,
  `meta/test.json`, and `images/<class>/<id>.jpg`) with deterministic, visually separable dish patterns
  for all 25 subset classes.
- A `.bootstrap_marker` file is placed in `data/raw/food-101/` so `python data/download_food101.py`
  knows to replace it when the user opts to download the full 5 GB Food-101 dataset.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SUBSET_PATH = ROOT / "data" / "subset_classes.json"
DEFAULT_RAW = ROOT / "data" / "raw"


def _distinct_palette(idx: int, total: int = 25) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    hue = (idx / total) % 1.0
    r1, g1, b1 = colorsys.hsv_to_rgb(hue, 0.78, 0.92)
    r2, g2, b2 = colorsys.hsv_to_rgb((hue + 0.08) % 1.0, 0.85, 0.65)
    r3, g3, b3 = colorsys.hsv_to_rgb((hue + 0.50) % 1.0, 0.55, 0.95)
    return (
        (int(r1 * 255), int(g1 * 255), int(b1 * 255)),
        (int(r2 * 255), int(g2 * 255), int(b2 * 255)),
        (int(r3 * 255), int(g3 * 255), int(b3 * 255)),
    )


def _render_class_image(cls_idx: int, sample_idx: int, size: tuple[int, int] = (280, 260)) -> Image.Image:
    rng = random.Random(cls_idx * 10_000 + sample_idx)
    bg, fg, accent = _distinct_palette(cls_idx)
    jitter = lambda c: tuple(max(0, min(255, ch + rng.randint(-12, 12))) for ch in c)
    im = Image.new("RGB", size, jitter(bg))
    draw = ImageDraw.Draw(im)
    w, h = size
    cx, cy = w // 2 + rng.randint(-10, 10), h // 2 + rng.randint(-10, 10)

    # Distinct geometric motif per class (stripes + central dish geometry + garnish dots)
    stripe_step = 18 + (cls_idx % 5) * 6
    if cls_idx % 3 == 0:
        for x in range(0, w, stripe_step):
            draw.line([(x, 0), (x, h)], fill=jitter(fg), width=3)
    elif cls_idx % 3 == 1:
        for y in range(0, h, stripe_step):
            draw.line([(0, y), (w, y)], fill=jitter(fg), width=3)
    else:
        for d in range(-h, w, stripe_step):
            draw.line([(d, 0), (d + h, h)], fill=jitter(fg), width=3)

    r_outer = 78 + (cls_idx % 4) * 8
    if cls_idx % 2 == 0:
        draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=jitter(fg), outline=(20, 20, 20), width=4)
    else:
        draw.rectangle((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=jitter(fg), outline=(20, 20, 20), width=4)

    n_toppings = 4 + (cls_idx % 7)
    for k in range(n_toppings):
        tx = cx + rng.randint(-r_outer // 2, r_outer // 2)
        ty = cy + rng.randint(-r_outer // 2, r_outer // 2)
        tr = 10 + (cls_idx % 3) * 5
        if (cls_idx + k) % 2 == 0:
            draw.ellipse((tx - tr, ty - tr, tx + tr, ty + tr), fill=jitter(accent), outline=(20, 20, 20), width=2)
        else:
            draw.polygon([(tx, ty - tr), (tx - tr, ty + tr), (tx + tr, ty + tr)], fill=jitter(accent), outline=(20, 20, 20))
    return im


def build_bootstrap(raw_root: Path, n_train: int = 20, n_test: int = 10) -> None:
    subset: list[str] = json.loads(SUBSET_PATH.read_text(encoding="utf-8"))
    base = raw_root / "food-101"
    meta_dir = base / "meta"
    img_dir = base / "images"
    meta_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    all_classes = sorted(set(subset + [f"extra_food_{i:02d}" for i in range(101 - len(subset))]))
    (meta_dir / "classes.txt").write_text("\n".join(all_classes) + "\n", encoding="utf-8")

    train_meta: dict[str, list[str]] = {c: [] for c in all_classes}
    test_meta: dict[str, list[str]] = {c: [] for c in all_classes}

    for cls_idx, cls_name in enumerate(subset):
        cls_folder = img_dir / cls_name
        cls_folder.mkdir(parents=True, exist_ok=True)
        for i in range(n_train):
            stem = f"{cls_name}/train_{i:04d}"
            out_path = img_dir / f"{stem}.jpg"
            if not out_path.is_file():
                _render_class_image(cls_idx, i).save(out_path, format="JPEG", quality=90)
            train_meta[cls_name].append(stem)
        for i in range(n_test):
            stem = f"{cls_name}/test_{i:04d}"
            out_path = img_dir / f"{stem}.jpg"
            if not out_path.is_file():
                _render_class_image(cls_idx, 1000 + i).save(out_path, format="JPEG", quality=90)
            test_meta[cls_name].append(stem)

    (meta_dir / "train.json").write_text(json.dumps(train_meta, indent=2) + "\n", encoding="utf-8")
    (meta_dir / "test.json").write_text(json.dumps(test_meta, indent=2) + "\n", encoding="utf-8")
    (base / ".bootstrap_marker").write_text(
        "Bootstrap dataset for local smoke/quickstart execution. Run `python data/download_food101.py --yes` for the full 5 GB Food-101 archive.\n",
        encoding="utf-8",
    )
    print(f"Built bootstrap Food-101 dataset at {base} ({len(subset)} classes, {n_train} train / {n_test} test per class).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_RAW))
    ap.add_argument("--train-per-class", type=int, default=20)
    ap.add_argument("--test-per-class", type=int, default=10)
    args = ap.parse_args()
    build_bootstrap(Path(args.root), n_train=args.train_per_class, n_test=args.test_per_class)


if __name__ == "__main__":
    main()

