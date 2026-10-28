"""Parity tests: backend preprocessing vs notebook ``eval_numpy``, and ONNX FP32 vs PyTorch logits."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from _shared.transforms import eval_numpy
from app.services.onnx_engine import OnnxEngine
from app.services.preprocessing import preprocess_rgb
from app.services.torch_engine import TorchEngine


def test_preprocessing_parity_with_notebook_eval_numpy(fixture_images: list[Path]) -> None:
    assert len(fixture_images) == 5
    for img_path in fixture_images:
        with Image.open(img_path) as im:
            rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
        nb_chw = eval_numpy(rgb)
        be_batch = preprocess_rgb(rgb)
        assert be_batch.shape == (1, 3, 224, 224)
        assert nb_chw.shape == (3, 224, 224)
        assert np.allclose(be_batch[0], nb_chw, atol=1e-5)


def test_onnx_fp32_logits_match_pytorch_logits(
    synth_models_dir: Path, fixture_images: list[Path]
) -> None:
    pt_engine = TorchEngine(synth_models_dir / "mobilenetv3_food25.pt")
    ort_engine = OnnxEngine(synth_models_dir / "mobilenetv3_food25_fp32.onnx")

    for img_path in fixture_images:
        with Image.open(img_path) as im:
            rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
        batch = preprocess_rgb(rgb)
        pt_logits = pt_engine.predict_logits(batch)
        ort_logits = ort_engine.predict_logits(batch)
        assert pt_logits.shape == (1, 25)
        assert ort_logits.shape == (1, 25)
        assert np.allclose(pt_logits, ort_logits, atol=1e-3)

