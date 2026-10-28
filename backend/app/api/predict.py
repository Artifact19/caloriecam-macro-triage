"""``POST /predict`` (and ``/api/predict``): classify a meal photo, triage, lookup macros, Grad-CAM."""
from __future__ import annotations

import logging
from typing import Optional

import anyio
import numpy as np
from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from ..errors import AppError, PayloadTooLarge
from ..runtime import Runtime
from ..schemas import GradcamResult, ImageInfo, Latency, Prediction, PredictResponse
from ..services.gradcam import render_overlay
from ..services.nutrition import MAX_SERVINGS, MIN_SERVINGS, normalize_dish_name
from ..services.preprocessing import preprocess_rgb
from ..services.triage import build_triage
from ..utils.images import check_content_type, decode_image, downscale_max_side, encode_png_base64
from ..utils.timing import Timer

log = logging.getLogger("meal_triage.predict")
router = APIRouter(tags=["predict"])

STREAM_CHUNK = 64 * 1024
MISSING_MSG = "Model artifacts not found. Run notebooks 01 to 04 (python scripts/run_notebooks.py)."


async def _read_bounded(upload: UploadFile, max_bytes: int, max_mb: float) -> bytes:
    """Read an upload in chunks, aborting with 413 as soon as ``max_bytes`` is exceeded."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(STREAM_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLarge(max_mb)
        chunks.append(chunk)
    if total == 0:
        raise AppError(422, "Uploaded file is empty.", "empty_upload")
    return b"".join(chunks)


def _softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    t = max(float(temperature), 1e-3)
    z = logits / t
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return (e / e.sum(axis=-1, keepdims=True)).astype(np.float32)


def _run_gradcam(rt: Runtime, batch: np.ndarray, image_rgb: np.ndarray, target_idx: int, target_label: str) -> GradcamResult:
    if rt.torch_engine is None:
        raise RuntimeError("PyTorch checkpoint not loaded")
    cam, _ = rt.torch_engine.gradcam(batch, target_idx)
    display_rgb = downscale_max_side(image_rgb)
    heat_rgba, overlay_rgb = render_overlay(cam, display_rgb, alpha=0.5, blur_ksize=5)
    h, w = display_rgb.shape[:2]
    return GradcamResult(
        target_class=target_label,
        heatmap_png_base64=encode_png_base64(heat_rgba),
        overlay_png_base64=encode_png_base64(overlay_rgb),
        width=w,
        height=h,
    )


@router.post(
    "/predict",
    response_model=PredictResponse,
    response_model_exclude_none=True,
    summary="Classify a meal photo and return macros, triage and Grad-CAM",
)
async def predict(
    request: Request,
    file: UploadFile = File(..., description="Meal photo (JPEG, PNG or WebP)"),
    top_k: int = Query(3, ge=1, le=5, description="Number of top predictions to return (1-5)"),
    gradcam: bool = Query(True, description="Include Grad-CAM attention overlay"),
    engine: Optional[str] = Query(None, description="Override engine: onnx_int8_static | onnx_int8_dynamic | onnx_fp32 | pytorch"),
    servings: float = Query(1.0, ge=MIN_SERVINGS, le=MAX_SERVINGS, description="Portion multiplier (0.25-10)"),
    gradcam_class: Optional[str] = Query(None, description="Explain this class instead of top-1"),
    tta: bool = Query(False, description="Optional test-time augmentation (horizontal flip average)"),
) -> JSONResponse:
    rt: Runtime = request.app.state.runtime
    settings = rt.settings

    check_content_type(file.content_type)
    raw_bytes = await _read_bounded(file, settings.max_upload_bytes, settings.max_upload_mb)

    # Server-side wall-clock starts once the request body has been received (spec 6.3).
    with Timer() as total_timer:
        with Timer() as t_pre:
            image_rgb = await anyio.to_thread.run_sync(decode_image, raw_bytes)
            orig_h, orig_w = image_rgb.shape[:2]
            batch = await anyio.to_thread.run_sync(preprocess_rgb, image_rgb)
            if tta:
                flipped = np.ascontiguousarray(image_rgb[:, ::-1, :])
                batch_flip = await anyio.to_thread.run_sync(preprocess_rgb, flipped)

        if not rt.ready or rt.nutrition is None or rt.default_engine is None:
            raise AppError(503, MISSING_MSG, "model_not_loaded")

        chosen_name = engine or rt.default_engine
        if chosen_name not in rt.available_engines():
            raise AppError(
                422,
                f"Unavailable engine '{chosen_name}'. Available: {rt.available_engines()}",
                "invalid_engine",
            )
        eng = rt.get_engine(chosen_name)

        target_idx: Optional[int] = None
        if gradcam_class is not None:
            norm_cls = normalize_dish_name(gradcam_class)
            if norm_cls not in rt.class_names:
                raise AppError(
                    422,
                    f"Unknown gradcam_class '{gradcam_class}'. Known: {rt.class_names}",
                    "invalid_gradcam_class",
                )
            target_idx = rt.class_names.index(norm_cls)

        with Timer() as t_inf:
            logits = await anyio.to_thread.run_sync(eng.predict_logits, batch)
            if tta:
                logits_flip = await anyio.to_thread.run_sync(eng.predict_logits, batch_flip)
                logits = 0.5 * (logits + logits_flip)

        with Timer() as t_post:
            probs = _softmax(logits, rt.temperature)[0]
            k = min(int(top_k), len(rt.class_names))
            order = np.argsort(-probs)[: max(k, 3)]
            all_preds = [
                Prediction(
                    label=rt.class_names[int(i)],
                    display_name=rt.nutrition.display_name(rt.class_names[int(i)]),
                    confidence=round(float(probs[int(i)]), 4),
                )
                for i in order
            ]
            top1 = all_preds[0]
            topk = all_preds[:k]
            nutrition = rt.nutrition.get_nutrition(top1.label, servings=servings)
            triage = build_triage(
                top1.confidence,
                all_preds,
                lambda d: rt.nutrition.get_nutrition(d, servings=servings),  # type: ignore[union-attr]
                high=settings.conf_threshold_high,
                low=settings.conf_threshold_low,
            )

        gradcam_result: Optional[GradcamResult] = None
        gradcam_ms = 0.0
        if gradcam and rt.torch_engine is not None:
            explain_idx = target_idx if target_idx is not None else int(order[0])
            explain_label = rt.class_names[explain_idx]
            with Timer() as t_cam:
                gradcam_result = await anyio.to_thread.run_sync(
                    _run_gradcam, rt, batch, image_rgb, explain_idx, explain_label
                )
            gradcam_ms = t_cam.ms

        total_ms = total_timer.elapsed_ms()
        class_ms = t_pre.ms + t_inf.ms + t_post.ms
        resp = PredictResponse(
            top1=top1,
            topk=topk,
            triage=triage,
            nutrition=nutrition,
            gradcam=gradcam_result,
            latency=Latency(
                preprocess_ms=round(t_pre.ms, 2),
                inference_ms=round(t_inf.ms, 2),
                gradcam_ms=round(gradcam_ms, 2),
                postprocess_ms=round(t_post.ms, 2),
                total_ms=round(max(total_ms, class_ms + gradcam_ms), 2),
                classification_path_ms=round(class_ms, 2),
            ),
            engine=chosen_name,
            model_version=rt.model_version or "mobilenetv3_large-food25",
            image=ImageInfo(original_width=orig_w, original_height=orig_h),
        )

    log.info(
        "predict req=%s engine=%s label=%s conf=%.3f triage=%s total_ms=%.1f class_ms=%.1f cam_ms=%.1f",
        getattr(request.state, "request_id", "-"),
        chosen_name,
        top1.label,
        top1.confidence,
        triage.level,
        resp.latency.total_ms,
        resp.latency.classification_path_ms,
        resp.latency.gradcam_ms,
    )
    return JSONResponse(content=resp.model_dump(exclude_none=True))

