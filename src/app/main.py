"""FastAPI application factory."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("app")

    application = FastAPI(
        title="A股智能监控系统",
        description="A-share stock monitoring with real-time alerts",
        version="0.1.0",
    )

    # CORS for local dev
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structlog request logging middleware
    @application.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        log.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=elapsed_ms,
        )
        return response

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


# Module-level app instance for uvicorn and eval import_check
app = create_app()
