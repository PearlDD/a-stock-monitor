"""Tests for market data service (circuit breaker, retry, caching)."""

import time

import pytest

from app.models.market import StockQuote
from app.services.cache import get_cache
from app.services.market_data import (
    CircuitBreaker,
    _filter_quotes,
)


@pytest.fixture(autouse=True)
def fresh_cache():
    """Ensure clean cache for each test."""
    cache = get_cache()
    cache.clear()
    yield cache
    cache.clear()


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(threshold=3, cooldown=10)
        assert cb.is_open is False

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(threshold=3, cooldown=600)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_success_resets_failures(self):
        cb = CircuitBreaker(threshold=3, cooldown=600)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False

    def test_auto_reset_after_cooldown(self):
        cb = CircuitBreaker(threshold=1, cooldown=0.01)
        cb.record_failure()
        assert cb.is_open is True
        # Simulate cooldown expiry
        cb._opened_at = time.monotonic() - 1
        assert cb.is_open is False

    def test_manual_reset(self):
        cb = CircuitBreaker(threshold=1, cooldown=600)
        cb.record_failure()
        assert cb.is_open is True
        cb.reset()
        assert cb.is_open is False


class TestFilterQuotes:
    def test_filter_by_codes(self):
        quotes = [
            StockQuote(
                code="600519",
                name="茅台",
                price=1800,
                change_pct=0,
                volume=0,
                amount=0,
                high=0,
                low=0,
                open=0,
                prev_close=0,
            ),
            StockQuote(
                code="000858",
                name="五粮液",
                price=168,
                change_pct=0,
                volume=0,
                amount=0,
                high=0,
                low=0,
                open=0,
                prev_close=0,
            ),
            StockQuote(
                code="000001",
                name="平安",
                price=50,
                change_pct=0,
                volume=0,
                amount=0,
                high=0,
                low=0,
                open=0,
                prev_close=0,
            ),
        ]
        result = _filter_quotes(quotes, ["600519", "000001"])
        assert len(result) == 2
        assert {q.code for q in result} == {"600519", "000001"}

    def test_filter_empty_quotes(self):
        assert _filter_quotes([], ["600519"]) == []

    def test_filter_none_quotes(self):
        assert _filter_quotes(None, ["600519"]) == []

    def test_filter_no_match(self):
        quotes = [
            StockQuote(
                code="600519",
                name="茅台",
                price=1800,
                change_pct=0,
                volume=0,
                amount=0,
                high=0,
                low=0,
                open=0,
                prev_close=0,
            ),
        ]
        assert _filter_quotes(quotes, ["999999"]) == []
