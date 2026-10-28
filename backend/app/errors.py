"""Application errors and the consistent ``{"detail": str, "code": str}`` JSON shape."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("meal_triage.errors")


class AppError(Exception):
    """Domain error carrying an HTTP status, a human message and a machine code."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


class PayloadTooLarge(AppError):
    def __init__(self, max_mb: float) -> None:
        super().__init__(413, f"Upload exceeds the {max_mb:g} MB limit.", "payload_too_large")


def _json(status: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})


_STATUS_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    503: "service_unavailable",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _json(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _json(exc.status_code, detail, _STATUS_CODES.get(exc.status_code, "http_error"))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        return _json(422, "; ".join(parts) or "Invalid request.", "validation_error")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the traceback server-side only; the client never sees stack traces.
        log.exception("unhandled error path=%s", request.url.path, exc_info=exc)
        return _json(500, "Internal server error.", "internal_error")

