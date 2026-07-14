"""Structured logging configuration using structlog.

JSON output for production. Request tracing via request_id middleware.
"""

from __future__ import annotations

import logging
import sys
import uuid

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output for production."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return uuid.uuid4().hex[:12]


def bind_request_id(request_id: str) -> None:
    """Bind request_id to structlog context for the current async task."""
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_context() -> None:
    """Clear structlog context vars after request completes."""
    structlog.contextvars.unbind_contextvars("request_id")
