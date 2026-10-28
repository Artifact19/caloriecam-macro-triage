"""Tests for ``POST /predict``, input validation, Grad-CAM properties and triage boundaries."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

from app.config import REPO_ROOT
from app.schemas import NutritionInfo, Prediction
from app.services.gradcam import GradCAM, disable_inplace
from app.services.nutrition import NutritionService
from app.services.torch_engine import build_model
from app.services.triage import build_triage, triage_level

SAMPLE_EXPECTATIONS = {
    "pizza.jpg": "pizza",
    "salad.jpg": "greek_salad",
    "steak.jpg": "steak",
    "curry.jpg": "chicken_curry",
}


def test_predict_returns_full_schema(synth_client: TestClient, valid_jpeg_bytes: bytes) -> None:
    resp = synth_client.post(
        "/api/predict?top_k=3&gradcam=true&servings=1.5",
        files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["topk"]) == 3
    assert data["top1"] == data["topk"][0]
    assert data["nutrition"]["servings"] == 1.5
    assert data["gradcam"]["target_class"] == data["top1"]["label"]
    assert len(data["gradcam"]["heatmap_png_base64"]) > 100
    assert len(data["gradcam"]["overlay_png_base64"]) > 100
    assert data["latency"]["total_ms"] >= data["latency"]["classification_path_ms"]
    assert data["image"] == {"original_width": 160, "original_height": 120}


def test_predict_gradcam_false_omits_key(synth_client: TestClient, valid_jpeg_bytes: bytes) -> None:
    resp = synth_client.post(
        "/api/predict?gradcam=false",
        files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "gradcam" not in body


def test_predict_engine_override_and_topk_bounds(synth_client: TestClient, valid_jpeg_bytes: bytes) -> None:
    r_pt = synth_client.post(
        "/api/predict?engine=pytorch&top_k=5&gradcam=false",
        files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert r_pt.status_code == 200
    assert r_pt.json()["engine"] == "pytorch"
    assert len(r_pt.json()["topk"]) == 5

    r_bad_k = synth_client.post(
        "/api/predict?top_k=0",
        files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert r_bad_k.status_code == 422

    r_bad_k2 = synth_client.post(
        "/api/predict?top_k=6",
        files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert r_bad_k2.status_code == 422


def test_predict_handles_exif_rotated_image(synth_client: TestClient, exif_rotated_jpeg_bytes: bytes) -> None:
    resp = synth_client.post(
        "/api/predict?gradcam=false",
        files={"file": ("rotated.jpg", exif_rotated_jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    # 200x100 with EXIF orientation 6 (90 deg CW) transposes to 100x200.
    assert resp.json()["image"] == {"original_width": 100, "original_height": 200}


def test_predict_rejects_invalid_inputs(synth_client: TestClient, valid_jpeg_bytes: bytes) -> None:
    # 1. Unsupported content-type (415)
    r_mime = synth_client.post(
        "/api/predict",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert r_mime.status_code == 415

    # 2. Non-image bytes with image/jpeg content-type (422)
    r_garbage = synth_client.post(
        "/api/predict",
        files={"file": ("bad.jpg", b"not-a-jpeg-at-all", "image/jpeg")},
    )
    assert r_garbage.status_code == 422

    # 3. Tiny 10x10 image (422)
    tiny_buf = io.BytesIO()
    Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8)).save(tiny_buf, format="JPEG")
    r_tiny = synth_client.post(
        "/api/predict",
        files={"file": ("tiny.jpg", tiny_buf.getvalue(), "image/jpeg")},
    )
    assert r_tiny.status_code == 422

    # 4. Truncated JPEG (422)
    truncated = valid_jpeg_bytes[: len(valid_jpeg_bytes) // 3]
    r_trunc = synth_client.post(
        "/api/predict",
        files={"file": ("trunc.jpg", truncated, "image/jpeg")},
    )
    assert r_trunc.status_code == 422

    # 5. > 10 MB upload (413)
    big_payload = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 1024)
    r_big = synth_client.post(
        "/api/predict",
        files={"file": ("huge.jpg", big_payload, "image/jpeg")},
    )
    assert r_big.status_code == 413


@pytest.mark.parametrize(
    ("conf", "expected"),
    [
        (0.39999, "uncertain"),
        (0.4, "review"),
        (0.69999, "review"),
        (0.7, "confident"),
    ],
)
def test_triage_boundary_values(conf: float, expected: str) -> None:
    assert triage_level(conf, high=0.70, low=0.40) == expected
    svc = NutritionService(REPO_ROOT / "assets" / "nutrition_registry.json")
    preds = [
        Prediction(label="pizza", display_name="Pizza", confidence=conf),
        Prediction(label="lasagna", display_name="Lasagna", confidence=0.2),
        Prediction(label="steak", display_name="Steak", confidence=0.1),
    ]
    tr = build_triage(conf, preds, lambda d: svc.get_nutrition(d, 1.0), high=0.70, low=0.40)
    assert tr.level == expected
    if expected == "confident":
        assert tr.alternatives_with_nutrition == []
    else:
        assert len(tr.alternatives_with_nutrition) == 3
        assert isinstance(svc.get_nutrition("pizza"), NutritionInfo)


def test_gradcam_shape_range_determinism_and_no_hook_leaks() -> None:
    torch.manual_seed(0)
    model = build_model("mobilenet_v3_large", 25).eval()
    disable_inplace(model)
    layer = model.features[-1]
    x = torch.randn(1, 3, 224, 224)

    first_cam = None
    for _ in range(20):
        with GradCAM(model, layer) as cam_engine:
            cam, idx = cam_engine(x, target_index=3)
            assert idx == 3
            assert cam.shape == (7, 7)
            assert np.isfinite(cam).all()
            assert float(cam.min()) >= 0.0 - 1e-6
            assert float(cam.max()) <= 1.0 + 1e-6
            if first_cam is None:
                first_cam = cam
            else:
                assert np.allclose(cam, first_cam, atol=1e-6)
        assert len(layer._forward_hooks) == 0


@pytest.mark.parametrize(("filename", "expected_label"), list(SAMPLE_EXPECTATIONS.items()))
def test_sample_images_classified_by_shipped_model(
    real_client: TestClient, filename: str, expected_label: str
) -> None:
    sample_path: Path = REPO_ROOT / "assets" / "samples" / filename
    health = real_client.get("/api/health").json()
    if not health["model_loaded"] or not sample_path.is_file():
        pytest.skip("Trained model artifacts or sample images are not present yet.")
    resp = real_client.post(
        "/api/predict",
        files={"file": (filename, sample_path.read_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["top1"]["label"] == expected_label

