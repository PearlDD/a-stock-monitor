"""In-memory TTL cache for market data.

Single-worker deployment makes in-memory caching viable.
Provides Redis-like semantics (TTL, counters) without external dependency.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from app.logging import get_logger

log = get_logger("cache")

# Default TTLs (seconds)
QUOTE_TTL = 30
NEWS_TTL = 300  # 5 min
FINANCIALS_TTL = 3600  # 1 hour
CALENDAR_TTL = 86400  # 1 day


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._counters: dict[str, int] = {}
        self._counter_resets: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + ttl,
        )

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    # --- Counter operations (for daily push limits, cooldowns) ---

    async def incr(self, key: str) -> int:
        async with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            return self._counters[key]

    async def get_counter(self, key: str) -> int:
        return self._counters.get(key, 0)

    async def reset_counter(self, key: str) -> None:
        async with self._lock:
            self._counters.pop(key, None)

    async def set_with_daily_reset(self, key: str, value: int) -> None:
        """Set a counter that resets daily (for push quota tracking)."""
        async with self._lock:
            self._counters[key] = value

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = time.monotonic()
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]
        if expired:
            log.debug("cache_cleanup", removed=len(expired))
        return len(expired)

    def clear(self) -> None:
        """Clear all cache entries and counters."""
        self._store.clear()
        self._counters.clear()
        self._counter_resets.clear()


# Module-level singleton for single-worker deployment
_cache: TTLCache | None = None


def get_cache() -> TTLCache:
    """Get or create the cache singleton."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = TTLCache()
    return _cache
