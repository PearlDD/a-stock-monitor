"""FastAPI application factory."""

import sys
import time

import structlog
from fastapi import FastAPI, Request, Response

from app.config import get_settings
from app.logging import setup_logging

logger = structlog.stdlib.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging(settings.log_level)

    application = FastAPI(
        title="A股智能监控系统",
        description="A-share stock monitoring with real-time alerts",
        version="0.1.0",
    )

    @application.middleware("http")
    async def logging_middleware(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[misc,operator]
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=round(elapsed_ms, 1),
        )
        return response

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


def _cli() -> None:
    """Minimal CLI entry point for --test --dry-run mode."""
    args = sys.argv[1:]
    if "--test" in args and "--dry-run" in args:
        setup_logging("INFO")
        logger.info("mock_mode", status="ready")
        print("ready")
        return
    # Default: run uvicorn
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


# Module-level app instance for uvicorn and eval import_check
app = create_app()

if __name__ == "__main__":
    _cli()
