"""FastAPI application factory, CORS, request-ID middleware, lifespan warmup and static UI mount."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import health, nutrition, predict
from .config import Settings, get_settings
from .errors import register_error_handlers
from .runtime import build_runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runtime = build_runtime(cfg)
        yield

    app = FastAPI(
        title="Visual Meal Recognition & Macro Triage API",
        description=(
            "Local-first food classification (MobileNetV3-Large, 25 Food-101 dishes), "
            "Grad-CAM explainability, macro estimation and confidence triage. "
            "Estimates are approximate and not medical advice."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = cfg
    # Provide an un-warmed placeholder until the lifespan context runs (e.g. if inspected early).
    app.state.runtime = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _request_id(request: Request, call_next) -> Response:
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = req_id
        # Lazily build runtime if TestClient was used without a context manager.
        if getattr(request.app.state, "runtime", None) is None:
            request.app.state.runtime = build_runtime(cfg)
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
        return response

    register_error_handlers(app)

    # Expose routes both at `/api/*` (used by the Vite frontend) and un-prefixed (for curl).
    for prefix in ("/api", ""):
        app.include_router(health.router, prefix=prefix)
        app.include_router(predict.router, prefix=prefix)
        app.include_router(nutrition.router, prefix=prefix)

    # Optional single-process mode: serve the built frontend if `frontend/dist` exists.
    if cfg.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(cfg.frontend_dist), html=True), name="frontend")

    return app


app = create_app()

