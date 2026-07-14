"""Tests for async rate limiter."""

import time

import pytest

from app.providers.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_first_acquire_no_delay(self):
        limiter = RateLimiter(min_interval=1.0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # first call should be instant

    @pytest.mark.asyncio
    async def test_second_acquire_delayed(self):
        limiter = RateLimiter(min_interval=0.1)
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08  # should wait ~0.1s

    @pytest.mark.asyncio
    async def test_no_delay_after_interval(self):
        limiter = RateLimiter(min_interval=0.05)
        await limiter.acquire()
        import asyncio

        await asyncio.sleep(0.1)  # longer than min_interval
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # should not wait

    def test_current_delay_no_errors(self):
        limiter = RateLimiter(min_interval=3.0)
        assert limiter.current_delay == 3.0

    def test_current_delay_with_errors(self):
        limiter = RateLimiter(min_interval=3.0, max_backoff=60.0)
        limiter.record_error()
        assert limiter.current_delay == 6.0  # 3 * 2^1
        limiter.record_error()
        assert limiter.current_delay == 12.0  # 3 * 2^2
        limiter.record_error()
        assert limiter.current_delay == 24.0  # 3 * 2^3

    def test_backoff_capped_at_max(self):
        limiter = RateLimiter(min_interval=3.0, max_backoff=10.0)
        for _ in range(10):
            limiter.record_error()
        assert limiter.current_delay == 10.0

    def test_success_resets_backoff(self):
        limiter = RateLimiter(min_interval=3.0)
        limiter.record_error()
        limiter.record_error()
        assert limiter.current_delay > 3.0
        limiter.record_success()
        assert limiter.current_delay == 3.0

    def test_reset(self):
        limiter = RateLimiter(min_interval=3.0)
        limiter.record_error()
        limiter._last_request = time.monotonic()
        limiter.reset()
        assert limiter.current_delay == 3.0
        assert limiter._last_request == 0.0

    def test_non_retryable_status_ignored(self):
        limiter = RateLimiter(min_interval=3.0)
        limiter.record_error(status_code=404)  # not in backoff set
        assert limiter.current_delay == 3.0  # no backoff

    def test_retryable_statuses_trigger_backoff(self):
        for code in [401, 403, 429, 500, 502, 503, 504]:
            limiter = RateLimiter(min_interval=1.0)
            limiter.record_error(status_code=code)
            assert limiter.current_delay > 1.0, f"status {code} should trigger backoff"
