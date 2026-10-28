"""Execute notebooks 01 -> 04 headlessly via nbconvert (PROJECT_SPEC.md Section 12.3).

Usage:
    python scripts/run_notebooks.py [--fast] [--out-dir notebooks]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = ROOT / "notebooks"
NOTEBOOK_NAMES = (
    "01_dataset_eda_and_preprocessing.ipynb",
    "02_mobilenetv3_finetuning.ipynb",
    "03_gradcam_explainability.ipynb",
    "04_onnx_export_and_quantization.ipynb",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true", help="set FAST_DEV=1 for a quick smoke training run")
    ap.add_argument("--kernel", default="python3", help="Jupyter kernel name (default: python3)")
    ap.add_argument(
        "--out-dir",
        default=str(NOTEBOOKS_DIR),
        help="Directory where executed notebooks are written (default: in-place in notebooks/)",
    )
    args = ap.parse_args(argv)

    if args.fast:
        os.environ["FAST_DEV"] = "1"

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    total_t0 = time.perf_counter()
    for name in NOTEBOOK_NAMES:
        src = NOTEBOOKS_DIR / name
        dst = out_dir / name
        if not src.is_file():
            print(f"[ERROR] Missing notebook: {src}", file=sys.stderr)
            return 1
        print(f"==> Executing {name} (FAST_DEV={os.environ.get('FAST_DEV', '0')}) ...")
        t0 = time.perf_counter()
        nb = nbformat.read(str(src), as_version=4)
        ep = ExecutePreprocessor(timeout=-1, kernel_name=args.kernel)
        try:
            ep.preprocess(nb, {"metadata": {"path": str(NOTEBOOKS_DIR)}})
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"[FAILED] {name} after {elapsed:.1f}s: {exc}", file=sys.stderr)
            return 1
        nbformat.write(nb, str(dst))
        elapsed = time.perf_counter() - t0
        print(f"    Finished {name} in {elapsed:.1f}s -> {dst}")

    print(f"All 4 notebooks completed in {time.perf_counter() - total_t0:.1f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
