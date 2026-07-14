"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="A股智能监控系统",
        description="A-share stock monitoring with real-time alerts",
        version="0.1.0",
    )

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


# Module-level app instance for uvicorn and eval import_check
app = create_app()
