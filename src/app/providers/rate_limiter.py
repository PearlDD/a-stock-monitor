"""Async rate limiter with configurable min interval and exponential backoff.

Prevents AKShare ban from rapid requests. Uses asyncio.Lock for safety.
"""

from __future__ import annotations

import asyncio
import time

from app.logging import get_logger

log = get_logger("rate_limiter")

# HTTP status codes that trigger backoff
_BACKOFF_STATUS_CODES = {401, 403, 429, 500, 502, 503, 504}


class RateLimiter:
    """Async rate limiter with per-source minimum interval and backoff."""

    def __init__(self, min_interval: float = 3.0, max_backoff: float = 60.0) -> None:
        self.min_interval = min_interval
        self.max_backoff = max_backoff
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0
        self._consecutive_errors: int = 0

    @property
    def current_delay(self) -> float:
        """Calculate current delay including backoff."""
        if self._consecutive_errors == 0:
            return self.min_interval
        backoff = self.min_interval * (2 ** self._consecutive_errors)
        return float(min(backoff, self.max_backoff))

    async def acquire(self) -> None:
        """Wait until it's safe to make a request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            delay = self.current_delay
            if elapsed < delay:
                wait_time = delay - elapsed
                log.debug("rate_limit_wait", wait_s=round(wait_time, 2))
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()

    def record_success(self) -> None:
        """Reset backoff on successful request."""
        self._consecutive_errors = 0

    def record_error(self, status_code: int | None = None) -> None:
        """Increase backoff on error. Only backs off for retryable errors."""
        if status_code is not None and status_code not in _BACKOFF_STATUS_CODES:
            return
        self._consecutive_errors += 1
        log.warning(
            "rate_limiter_backoff",
            consecutive_errors=self._consecutive_errors,
            next_delay_s=round(self.current_delay, 1),
        )

    def reset(self) -> None:
        """Reset all state."""
        self._consecutive_errors = 0
        self._last_request = 0.0


# Module-level singleton
_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = RateLimiter(min_interval=3.0)
    return _limiter
