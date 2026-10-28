"""``GET /health`` (and ``/api/health``)."""
from __future__ import annotations

import time

import onnxruntime as ort
import torch
from fastapi import APIRouter, Request

from ..runtime import Runtime
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness and artifact readiness")
def get_health(request: Request) -> HealthResponse:
    rt: Runtime = request.app.state.runtime
    return HealthResponse(
        status="ok",
        model_loaded=rt.ready,
        engines=rt.available_engines(),
        default_engine=rt.default_engine,
        num_classes=len(rt.class_names),
        classes=rt.class_names,
        model_version=rt.model_version,
        onnxruntime_version=ort.__version__,
        torch_version=torch.__version__,
        uptime_s=round(max(0.0, time.time() - rt.started_at), 2),
        missing_artifacts=rt.missing,
    )

