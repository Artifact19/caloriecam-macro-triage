"""Download Food-101 and build the 25-class subset manifest.

Usage:
    python data/download_food101.py [--root data/raw] [--classes data/subset_classes.json] [--yes]

* Idempotent: torchvision verifies the existing archive/extracted folder and skips work.
* Fails loudly if any subset class name is not a Food-101 label.
* Writes ``data/subset_manifest.json`` -> ``{class: {food101_idx, train_count, test_count}}``.
* ``get_subset_samples(split)`` is reused by ``notebooks/_shared/datasets.py``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = DATA_DIR / "raw"
DEFAULT_CLASSES = DATA_DIR / "subset_classes.json"
MANIFEST_PATH = DATA_DIR / "subset_manifest.json"
EXPECTED_DISK_GB = 5.0


def load_subset_classes(path: Path = DEFAULT_CLASSES) -> list[str]:
    """Ordered list of subset class names (defines the model's output index order)."""
    names = json.loads(Path(path).read_text(encoding="utf-8"))
    if len(set(names)) != len(names):
        raise ValueError("subset_classes.json contains duplicates")
    return list(names)


def _food101(root: Path, split: str, download: bool):
    from torchvision.datasets import Food101

    return Food101(root=str(root), split=split, download=download)


def resolve_label_indices(food101_classes: list[str], subset: list[str]) -> dict[str, int]:
    """Map subset class name -> Food-101 label index. Raises if any name is missing."""
    lookup = {c: i for i, c in enumerate(food101_classes)}
    missing = [c for c in subset if c not in lookup]
    if missing:
        raise KeyError(f"Subset classes not found in Food-101: {missing}")
    return {c: lookup[c] for c in subset}


def get_subset_samples(
    split: str,
    root: Path | str = DEFAULT_ROOT,
    classes_path: Path | str = DEFAULT_CLASSES,
) -> list[tuple[str, int]]:
    """Return ``[(image_path, new_label)]`` for the subset in ``split`` ('train' | 'test').

    ``new_label`` is the index into ``subset_classes.json`` (0..24), NOT the Food-101 index.
    The result is ordered deterministically (Food-101 meta order, filtered).
    """
    if split not in ("train", "test"):
        raise ValueError("split must be 'train' or 'test'")
    subset = load_subset_classes(Path(classes_path))
    ds = _food101(Path(root), split, download=False)
    idx_map = resolve_label_indices(list(ds.classes), subset)
    remap = {food_idx: new for new, food_idx in enumerate(idx_map[c] for c in subset)}
    samples: list[tuple[str, int]] = []
    for path, label in zip(ds._image_files, ds._labels):  # noqa: SLF001 (torchvision internals)
        if label in remap:
            samples.append((str(path), remap[label]))
    return samples


def build_manifest(root: Path, classes_path: Path) -> dict:
    subset = load_subset_classes(classes_path)
    train = _food101(root, "train", download=False)
    idx_map = resolve_label_indices(list(train.classes), subset)
    manifest: dict[str, dict[str, int]] = {}
    counts = {}
    for split in ("train", "test"):
        ds = train if split == "train" else _food101(root, "test", download=False)
        c: dict[int, int] = {}
        for label in ds._labels:  # noqa: SLF001
            c[label] = c.get(label, 0) + 1
        counts[split] = c
    for name in subset:
        i = idx_map[name]
        manifest[name] = {
            "food101_idx": i,
            "train_count": counts["train"].get(i, 0),
            "test_count": counts["test"].get(i, 0),
        }
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--classes", default=str(DEFAULT_CLASSES))
    ap.add_argument("--yes", action="store_true", help="skip the disk-usage confirmation prompt")
    args = ap.parse_args(argv)
    root, classes = Path(args.root), Path(args.classes)

    subset = load_subset_classes(classes)
    print(f"Subset: {len(subset)} classes from {classes}")
    bootstrap_marker = root / "food-101" / ".bootstrap_marker"
    if bootstrap_marker.is_file():
        import shutil
        print(f"Removing local bootstrap dataset at {root / 'food-101'} before downloading full Food-101...")
        shutil.rmtree(root / "food-101")
    already = (root / "food-101" / "images").exists()
    if not already:
        print(f"Food-101 will be downloaded to {root} (~{EXPECTED_DISK_GB:.0f} GB on disk).")
        if not args.yes:
            if input("Continue? [y/N] ").strip().lower() not in {"y", "yes"}:
                print("Aborted.")
                return 1
    root.mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        _food101(root, split, download=True)  # verifies / downloads / extracts

    manifest = build_manifest(root, classes)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH}")
    bad = {k: v for k, v in manifest.items() if v["train_count"] != 750 or v["test_count"] != 250}
    for name, m in manifest.items():
        print(f"  {name:<20} idx={m['food101_idx']:>3} train={m['train_count']} test={m['test_count']}")
    if bad:
        print(f"WARNING: unexpected counts for {sorted(bad)}", file=sys.stderr)
        return 2
    print(f"OK: {len(manifest)} classes x 750/250 images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

