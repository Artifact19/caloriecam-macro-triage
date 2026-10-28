"""Validate consistency across ``data/``, ``assets/`` and ``models/`` (PROJECT_SPEC.md Section 9).

Usage:
    python scripts/validate_artifacts.py [--warn-only] [--models-dir models]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MODEL_FILES = (
    "class_names.json",
    "mobilenetv3_food25.pt",
    "mobilenetv3_food25_fp32.onnx",
    "mobilenetv3_food25_int8_dynamic.onnx",
    "mobilenetv3_food25_int8_static.onnx",
    "metrics.json",
    "benchmark.json",
)
ONNX_FILES = (
    "mobilenetv3_food25_fp32.onnx",
    "mobilenetv3_food25_int8_dynamic.onnx",
    "mobilenetv3_food25_int8_static.onnx",
)
REQUIRED_METRICS_KEYS = (
    "val_macro_f1",
    "test_top1",
    "test_top3",
    "test_macro_f1",
    "ece",
    "temperature",
    "per_class_f1",
    "training_config",
    "device",
    "date",
)
REQUIRED_BENCHMARK_ENGINES = ("pytorch", "onnx_fp32", "onnx_int8_dynamic", "onnx_int8_static")
REQUIRED_BENCHMARK_FIELDS = ("mean_ms", "p50_ms", "p95_ms", "p99_ms", "size_mb", "top1", "macro_f1")
REQUIRED_ITEM_FIELDS = (
    "display_name",
    "serving_description",
    "serving_grams",
    "calories_kcal",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
    "source",
)


def _check_registry(
    registry_path: Path, schema_path: Path, subset_classes: list[str], errors: list[str], warnings: list[str]
) -> None:
    if not registry_path.is_file():
        errors.append(f"Missing {registry_path}")
        return
    if not schema_path.is_file():
        errors.append(f"Missing {schema_path}")
    data: dict[str, Any] = json.loads(registry_path.read_text(encoding="utf-8"))
    for top_key in ("version", "disclaimer", "items"):
        if top_key not in data:
            errors.append(f"nutrition_registry.json missing top-level key '{top_key}'")
    items: dict[str, Any] = data.get("items", {})
    if list(items.keys()) != subset_classes:
        errors.append(
            "nutrition_registry.json item keys do not match subset_classes.json order/set "
            f"(missing={sorted(set(subset_classes) - set(items))}, extra={sorted(set(items) - set(subset_classes))})"
        )
    for dish, item in items.items():
        for f in REQUIRED_ITEM_FIELDS:
            if f not in item:
                errors.append(f"Registry item '{dish}' missing field '{f}'")
        kcal = float(item.get("calories_kcal", 0))
        p = float(item.get("protein_g", 0))
        c = float(item.get("carbs_g", 0))
        fat = float(item.get("fat_g", 0))
        atwater = 4.0 * p + 4.0 * c + 9.0 * fat
        if kcal > 0:
            rel_diff = abs(atwater - kcal) / kcal
            if rel_diff > 0.12:
                warnings.append(
                    f"Calorie consistency warning for '{dish}': 4P+4C+9F={atwater:.1f} vs {kcal:.1f} kcal "
                    f"(rel diff {rel_diff:.1%} > 12%)"
                )


def _check_models(models_dir: Path, subset_classes: list[str], errors: list[str]) -> None:
    for fname in REQUIRED_MODEL_FILES:
        if not (models_dir / fname).is_file():
            errors.append(f"Missing model artifact: {models_dir / fname}")

    class_names_path = models_dir / "class_names.json"
    if class_names_path.is_file():
        class_names = json.loads(class_names_path.read_text(encoding="utf-8"))
        if class_names != subset_classes:
            errors.append("models/class_names.json does not equal data/subset_classes.json")

    metrics_path = models_dir / "metrics.json"
    if metrics_path.is_file():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        for k in REQUIRED_METRICS_KEYS:
            if k not in metrics:
                errors.append(f"models/metrics.json missing required key '{k}'")

    bench_path = models_dir / "benchmark.json"
    if bench_path.is_file():
        bench = json.loads(bench_path.read_text(encoding="utf-8"))
        if "default_engine" not in bench:
            errors.append("models/benchmark.json missing 'default_engine'")
        for eng in REQUIRED_BENCHMARK_ENGINES:
            if eng not in bench or not isinstance(bench[eng], dict):
                errors.append(f"models/benchmark.json missing engine entry '{eng}'")
            else:
                for f in REQUIRED_BENCHMARK_FIELDS:
                    if f not in bench[eng]:
                        errors.append(f"models/benchmark.json['{eng}'] missing '{f}'")

    try:
        import onnxruntime as ort
    except ImportError:
        errors.append("onnxruntime is not installed")
        return

    dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
    for onnx_name in ONNX_FILES:
        path = models_dir / onnx_name
        if not path.is_file():
            continue
        try:
            sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            inp = sess.get_inputs()[0].name
            out = sess.run(None, {inp: dummy})[0]
            if tuple(out.shape) != (1, len(subset_classes)):
                errors.append(f"{onnx_name} output shape {tuple(out.shape)} != (1, {len(subset_classes)})")
        except Exception as exc:
            errors.append(f"Failed to load/run {onnx_name}: {exc}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-only", action="store_true", help="exit 0 even if artifacts are missing")
    ap.add_argument("--models-dir", default=str(ROOT / "models"))
    ap.add_argument("--assets-dir", default=str(ROOT / "assets"))
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    args = ap.parse_args(argv)

    models_dir = Path(args.models_dir)
    assets_dir = Path(args.assets_dir)
    data_dir = Path(args.data_dir)

    errors: list[str] = []
    warnings: list[str] = []

    subset_path = data_dir / "subset_classes.json"
    if not subset_path.is_file():
        errors.append(f"Missing {subset_path}")
        subset_classes: list[str] = []
    else:
        subset_classes = json.loads(subset_path.read_text(encoding="utf-8"))
        if len(subset_classes) != 25:
            errors.append(f"subset_classes.json has {len(subset_classes)} classes (expected 25)")

    _check_registry(
        assets_dir / "nutrition_registry.json",
        assets_dir / "nutrition_registry.schema.json",
        subset_classes,
        errors,
        warnings,
    )
    _check_models(models_dir, subset_classes, errors)

    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        for e in errors:
            prefix = "[WARN]" if args.warn_only else "[ERROR]"
            print(f"{prefix} {e}", file=sys.stderr if not args.warn_only else sys.stdout)
        if args.warn_only:
            print(f"validate_artifacts: {len(errors)} issue(s) noted (--warn-only; continuing).")
            return 0
        print(f"validate_artifacts FAILED with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("validate_artifacts: ALL CHECKS PASSED (25 classes, registry, checkpoint, 3 ONNX models, metrics, benchmark).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

