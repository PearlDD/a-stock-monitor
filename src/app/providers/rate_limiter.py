"""Async-compatible rate limiter for API calls."""

import asyncio
import time

import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Timestamp-based rate limiter with async support.

    Enforces a minimum interval between requests to the same source.
    Uses asyncio.Lock for concurrency safety.
    """

    def __init__(self, min_interval: float = 3.0) -> None:
        self._min_interval = min_interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the minimum interval has elapsed since the last request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._min_interval:
                wait_time = self._min_interval - elapsed
                await logger.adebug(
                    "rate_limiter.waiting",
                    wait_seconds=round(wait_time, 2),
                )
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()
