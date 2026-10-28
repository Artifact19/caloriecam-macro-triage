"""Shared pytest fixtures for backend unit and integration tests."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

for p in (str(BACKEND_DIR), str(REPO_ROOT / "notebooks")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.torch_engine import build_model  # noqa: E402


def _make_jpeg_bytes(w: int = 160, h: int = 120, seed: int = 0, exif_orientation: int | None = None) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    im = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    if exif_orientation is not None:
        exif = im.getexif()
        exif[0x0112] = exif_orientation  # Orientation tag
        im.save(buf, format="JPEG", quality=92, exif=exif.tobytes())
    else:
        im.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture(scope="session")
def fixture_images() -> list[Path]:
    """Ensure 5 deterministic fixture JPEGs exist in ``backend/tests/fixtures/``."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    sizes = [(160, 120), (240, 240), (300, 180), (180, 300), (320, 200)]
    paths: list[Path] = []
    for idx, (w, h) in enumerate(sizes):
        p = FIXTURES_DIR / f"sample_{idx}.jpg"
        if not p.is_file():
            p.write_bytes(_make_jpeg_bytes(w, h, seed=100 + idx))
        paths.append(p)
    return paths


@pytest.fixture(scope="session")
def valid_jpeg_bytes() -> bytes:
    return _make_jpeg_bytes(160, 120, seed=7)


@pytest.fixture(scope="session")
def exif_rotated_jpeg_bytes() -> bytes:
    return _make_jpeg_bytes(200, 100, seed=11, exif_orientation=6)  # 90 deg CW -> 100x200


@pytest.fixture(scope="session")
def synth_models_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a self-contained models directory with a real 25-class MobileNetV3-Large checkpoint + FP32 ONNX."""
    models_dir = tmp_path_factory.mktemp("models")
    classes = json.loads((REPO_ROOT / "data" / "subset_classes.json").read_text(encoding="utf-8"))
    (models_dir / "class_names.json").write_text(json.dumps(classes, indent=2), encoding="utf-8")

    torch.manual_seed(42)
    model = build_model("mobilenet_v3_large", len(classes)).eval()
    ckpt = {
        "state_dict": model.state_dict(),
        "class_names": classes,
        "arch": "mobilenet_v3_large",
        "img_size": 224,
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
        "val_macro_f1": 0.85,
        "epoch": 1,
        "temperature": 1.0,
    }
    torch.save(ckpt, models_dir / "mobilenetv3_food25.pt")

    dummy = torch.zeros(1, 3, 224, 224, dtype=torch.float32)
    onnx_fp32 = models_dir / "mobilenetv3_food25_fp32.onnx"
    torch.onnx.export(
        model,
        dummy,
        str(onnx_fp32),
        input_names=["input"],
        output_names=["logits"],
        opset_version=17,
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
    )
    (models_dir / "metrics.json").write_text(
        json.dumps({"val_macro_f1": 0.85, "temperature": 1.0}, indent=2),
        encoding="utf-8",
    )
    (models_dir / "benchmark.json").write_text(
        json.dumps({"default_engine": "onnx_fp32"}, indent=2),
        encoding="utf-8",
    )
    return models_dir


@pytest.fixture(scope="session")
def synth_client(synth_models_dir: Path) -> TestClient:
    """TestClient backed by synthetic model artifacts and the real nutrition registry."""
    cfg = Settings(
        models_dir=synth_models_dir,
        assets_dir=REPO_ROOT / "assets",
        default_engine="onnx_fp32",
        usda_api_key=None,
    )
    app = create_app(cfg)
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def real_client() -> TestClient:
    """TestClient backed by the repository's ``models/`` and ``assets/`` directories."""
    cfg = Settings(
        models_dir=REPO_ROOT / "models",
        assets_dir=REPO_ROOT / "assets",
        usda_api_key=None,
    )
    app = create_app(cfg)
    with TestClient(app) as client:
        yield client
