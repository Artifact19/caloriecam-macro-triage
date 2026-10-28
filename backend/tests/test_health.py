"""Tests for ``GET /health`` and graceful startup when model artifacts are absent."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import REPO_ROOT, Settings
from app.main import create_app


def test_health_ok_with_loaded_model(synth_client: TestClient) -> None:
    resp = synth_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["num_classes"] == 25
    assert len(body["classes"]) == 25
    assert "onnx_fp32" in body["engines"]
    assert "pytorch" in body["engines"]
    assert body["default_engine"] == "onnx_fp32"
    assert isinstance(body["uptime_s"], (int, float))


def test_unprefixed_health_matches_api_health(synth_client: TestClient) -> None:
    r1 = synth_client.get("/health")
    r2 = synth_client.get("/api/health")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["classes"] == r2.json()["classes"]


def test_missing_artifacts_starts_cleanly_and_predict_returns_503(
    tmp_path: Path, valid_jpeg_bytes: bytes
) -> None:
    empty_models = tmp_path / "empty_models"
    empty_models.mkdir()
    cfg = Settings(
        models_dir=empty_models,
        assets_dir=REPO_ROOT / "assets",
        usda_api_key=None,
    )
    app = create_app(cfg)
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200
        hdata = h.json()
        assert hdata["status"] == "ok"
        assert hdata["model_loaded"] is False
        assert "class_names.json" in hdata["missing_artifacts"]
        assert "mobilenetv3_food25.pt" in hdata["missing_artifacts"]

        pred = client.post(
            "/api/predict",
            files={"file": ("meal.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
        assert pred.status_code == 503
        err = pred.json()
        assert "Model artifacts not found" in err["detail"]
        assert err["code"] == "model_not_loaded"

