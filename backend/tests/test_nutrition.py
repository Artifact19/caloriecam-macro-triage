"""Tests for the nutrition registry service, scaling math, name normalisation and mocked USDA fallback."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_ROOT, Settings
from app.main import create_app


def test_all_25_classes_present_and_consistent(synth_client: TestClient) -> None:
    classes = json.loads((REPO_ROOT / "data" / "subset_classes.json").read_text(encoding="utf-8"))
    resp = synth_client.get("/api/nutrition")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["items"]) == 25
    returned = [item["dish"] for item in payload["items"]]
    assert returned == classes


@pytest.mark.parametrize("variant", ["Chicken Curry", "chicken-curry", "chicken_curry", "  CHICKEN_CURRY  "])
def test_dish_name_normalization_variants(synth_client: TestClient, variant: str) -> None:
    resp = synth_client.get(f"/api/nutrition/{variant}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dish"] == "chicken_curry"
    assert body["display_name"] == "Chicken Curry"
    assert body["calories_kcal"] == 330


def test_servings_scaling_doubles_macros_and_preserves_energy_split(synth_client: TestClient) -> None:
    r1 = synth_client.get("/api/nutrition/pizza?servings=1").json()
    r2 = synth_client.get("/api/nutrition/pizza?servings=2").json()
    assert r2["servings"] == 2.0
    assert r2["calories_kcal"] == pytest.approx(r1["calories_kcal"] * 2)
    assert r2["protein_g"] == pytest.approx(r1["protein_g"] * 2)
    assert r2["carbs_g"] == pytest.approx(r1["carbs_g"] * 2)
    assert r2["fat_g"] == pytest.approx(r1["fat_g"] * 2)
    assert r2["fiber_g"] == pytest.approx(r1["fiber_g"] * 2)
    assert r2["macro_energy_split"] == r1["macro_energy_split"]
    split_sum = sum(r1["macro_energy_split"].values())
    assert split_sum == pytest.approx(100.0, abs=0.2)


def test_unknown_dish_returns_404_when_fallback_disabled(synth_client: TestClient) -> None:
    resp = synth_client.get("/api/nutrition/beef_wellington")
    assert resp.status_code == 404
    body = resp.json()
    assert "Unknown dish" in body["detail"]
    assert body["code"] == "unknown_dish"


def test_usda_fallback_with_mocked_http(monkeypatch: pytest.MonkeyPatch, synth_models_dir: Path) -> None:
    fake_fdc_payload = {
        "foods": [
            {
                "description": "Beef Wellington, cooked",
                "dataType": "Foundation",
                "foodNutrients": [
                    {"nutrientNumber": "208", "value": 320.0},
                    {"nutrientNumber": "203", "value": 18.0},
                    {"nutrientNumber": "205", "value": 22.0},
                    {"nutrientNumber": "204", "value": 18.0},
                    {"nutrientNumber": "291", "value": 1.5},
                ],
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = fake_fdc_payload

    import httpx

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)

    cfg = Settings(
        models_dir=synth_models_dir,
        assets_dir=REPO_ROOT / "assets",
        usda_api_key="test-fake-key",
    )
    app = create_app(cfg)
    with TestClient(app) as client:
        resp = client.get("/api/nutrition/beef_wellington?servings=1.5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "usda_fdc_live"
        assert data["calories_kcal"] == pytest.approx(320.0 * 1.5)
        assert data["protein_g"] == pytest.approx(18.0 * 1.5)

