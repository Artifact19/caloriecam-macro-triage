"""Copy 4 sample images from the Food-101 test split into ``assets/samples/`` and ``frontend/public/samples/``.

Mapping (PROJECT_SPEC.md Section 3):
    pizza -> pizza.jpg
    greek_salad -> salad.jpg
    steak -> steak.jpg
    chicken_curry -> curry.jpg

Usage:
    python scripts/make_samples.py [--require-correct] [--max-tries 50]
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "notebooks"), str(ROOT / "data")):
    if p not in sys.path:
        sys.path.insert(0, p)

from _shared.transforms import eval_numpy  # noqa: E402
import download_food101 as dl  # noqa: E402

SAMPLE_MAP: dict[str, str] = {
    "pizza.jpg": "pizza",
    "salad.jpg": "greek_salad",
    "steak.jpg": "steak",
    "curry.jpg": "chicken_curry",
}
MAX_SIDE = 1024
JPEG_QUALITY = 90


def _resize_max_side(im: Image.Image, max_side: int = MAX_SIDE) -> Image.Image:
    w, h = im.size
    longest = max(w, h)
    if longest <= max_side:
        return im
    scale = max_side / longest
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)


def _load_onnx_predictor(models_dir: Path):
    import onnxruntime as ort

    bench_path = models_dir / "benchmark.json"
    engine = "onnx_fp32"
    if bench_path.is_file():
        engine = json.loads(bench_path.read_text(encoding="utf-8")).get("default_engine", "onnx_fp32")
    file_map = {
        "onnx_fp32": "mobilenetv3_food25_fp32.onnx",
        "onnx_int8_dynamic": "mobilenetv3_food25_int8_dynamic.onnx",
        "onnx_int8_static": "mobilenetv3_food25_int8_static.onnx",
    }
    onnx_path = models_dir / file_map.get(engine, "mobilenetv3_food25_fp32.onnx")
    if not onnx_path.is_file():
        onnx_path = models_dir / "mobilenetv3_food25_fp32.onnx"
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp_name = sess.get_inputs()[0].name

    def predict_index(im: Image.Image) -> int:
        rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
        batch = eval_numpy(rgb)[None]
        logits = sess.run(None, {inp_name: batch})[0]
        return int(np.argmax(logits, axis=1)[0])

    return predict_index


def _render_placeholder_dish(dish: str, size: tuple[int, int] = (640, 480)) -> Image.Image:
    """Create a clean, deterministic illustrative dish card when Food-101 raw images are not present yet."""
    palettes = {
        "pizza": ((242, 95, 92), (255, 224, 102), (180, 50, 45)),
        "greek_salad": ((60, 203, 185), (120, 200, 90), (245, 240, 230)),
        "steak": ((140, 75, 55), (244, 162, 97), (90, 45, 32)),
        "chicken_curry": ((244, 162, 97), (255, 205, 86), (195, 95, 40)),
    }
    bg, ring, center = palettes.get(dish, ((200, 180, 160), (240, 220, 200), (120, 100, 80)))
    im = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(im)
    w, h = size
    cx, cy = w // 2, h // 2
    draw.ellipse((cx - 190, cy - 190, cx + 190, cy + 190), fill=(252, 239, 230), outline=(20, 20, 20), width=6)
    draw.ellipse((cx - 145, cy - 145, cx + 145, cy + 145), fill=ring, outline=(20, 20, 20), width=5)
    rng = random.Random(dish)
    for _ in range(18):
        rx = cx + rng.randint(-105, 105)
        ry = cy + rng.randint(-105, 105)
        r = rng.randint(14, 28)
        draw.ellipse((rx - r, ry - r, rx + r, ry + r), fill=center, outline=(20, 20, 20), width=2)
    return im


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--models-dir", default=str(ROOT / "models"))
    ap.add_argument("--require-correct", action="store_true", help="re-sample until ONNX model predicts the target class")
    ap.add_argument("--max-tries", type=int, default=50)
    ap.add_argument(
        "--placeholder-if-missing",
        action="store_true",
        help="generate clean placeholder JPEGs if Food-101 has not been downloaded yet",
    )
    args = ap.parse_args(argv)

    raw_root = Path(args.root)
    models_dir = Path(args.models_dir)
    assets_samples = ROOT / "assets" / "samples"
    public_samples = ROOT / "frontend" / "public" / "samples"
    assets_samples.mkdir(parents=True, exist_ok=True)
    public_samples.mkdir(parents=True, exist_ok=True)

    classes = dl.load_subset_classes()
    has_food101 = (raw_root / "food-101" / "images").is_dir()

    if not has_food101:
        if not args.placeholder_if_missing:
            print(f"[ERROR] Food-101 not found at {raw_root}. Run python data/download_food101.py first.", file=sys.stderr)
            return 1
        for out_name, dish in SAMPLE_MAP.items():
            im = _render_placeholder_dish(dish)
            dst = assets_samples / out_name
            im.save(dst, format="JPEG", quality=JPEG_QUALITY)
            shutil.copy2(dst, public_samples / out_name)
            print(f"Wrote placeholder sample {dst} -> {public_samples / out_name}")
        return 0

    test_samples = dl.get_subset_samples("test", root=raw_root)
    by_label: dict[int, list[str]] = {}
    for path, label in test_samples:
        by_label.setdefault(label, []).append(path)

    predictor = _load_onnx_predictor(models_dir) if args.require_correct else None
    rng = random.Random(42)

    for out_name, dish in SAMPLE_MAP.items():
        target_idx = classes.index(dish)
        candidates = list(by_label.get(target_idx, []))
        if not candidates:
            print(f"[ERROR] No test images found for '{dish}'", file=sys.stderr)
            return 1
        rng.shuffle(candidates)

        chosen_im: Image.Image | None = None
        chosen_path: str | None = None
        tries = min(len(candidates), max(1, args.max_tries))
        for path in candidates[:tries]:
            with Image.open(path) as im:
                resized = _resize_max_side(im.convert("RGB"), MAX_SIDE)
            if predictor is None or predictor(resized) == target_idx:
                chosen_im = resized
                chosen_path = path
                break

        if chosen_im is None:
            print(
                f"[ERROR] Could not find a correctly classified sample for '{dish}' in {tries} tries.",
                file=sys.stderr,
            )
            return 2

        dst = assets_samples / out_name
        chosen_im.save(dst, format="JPEG", quality=JPEG_QUALITY)
        shutil.copy2(dst, public_samples / out_name)
        print(f"Saved {out_name} ({dish}) from {chosen_path} -> {dst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

