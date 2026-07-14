"""Tests for AI stock screening service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.screener import (
    PREDEFINED_FILTERS,
    SCREEN_RATE_LIMIT,
    _apply_filters,
    _check_rate_limit,
    screen_stocks,
)


@pytest.fixture(autouse=True)
def clear_cache():
    from app.services.cache import get_cache
    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


class TestPredefinedFilters:
    def test_all_presets_have_filters(self):
        for name, preset in PREDEFINED_FILTERS.items():
            assert "description" in preset
            assert "filters" in preset
            assert isinstance(preset["filters"], dict)

    def test_three_presets_exist(self):
        assert "低估值蓝筹" in PREDEFINED_FILTERS
        assert "近期强势" in PREDEFINED_FILTERS
        assert "高股息" in PREDEFINED_FILTERS


class TestApplyFilters:
    def test_pe_max_filter(self):
        stocks = [
            {"code": "A", "pe_ratio": 10, "price": 100},
            {"code": "B", "pe_ratio": 20, "price": 200},
            {"code": "C", "pe_ratio": 30, "price": 300},
        ]
        result = _apply_filters(stocks, {"pe_max": 15})
        assert len(result) == 1
        assert result[0]["code"] == "A"

    def test_change_pct_min_filter(self):
        stocks = [
            {"code": "A", "change_pct": 5.0},
            {"code": "B", "change_pct": 1.0},
            {"code": "C", "change_pct": -2.0},
        ]
        result = _apply_filters(stocks, {"change_pct_min": 3})
        assert len(result) == 1
        assert result[0]["code"] == "A"

    def test_combined_filters(self):
        stocks = [
            {"code": "A", "pe_ratio": 10, "pb_ratio": 1.5, "change_pct": 2},
            {"code": "B", "pe_ratio": 8, "pb_ratio": 3.0, "change_pct": 1},
            {"code": "C", "pe_ratio": 25, "pb_ratio": 1.0, "change_pct": 5},
        ]
        result = _apply_filters(stocks, {"pe_max": 15, "pb_max": 2})
        assert len(result) == 1
        assert result[0]["code"] == "A"

    def test_price_range_filter(self):
        stocks = [
            {"code": "A", "price": 50},
            {"code": "B", "price": 150},
            {"code": "C", "price": 300},
        ]
        result = _apply_filters(stocks, {"price_min": 100, "price_max": 200})
        assert len(result) == 1
        assert result[0]["code"] == "B"

    def test_empty_filters_pass_all(self):
        stocks = [{"code": "A"}, {"code": "B"}]
        result = _apply_filters(stocks, {})
        assert len(result) == 2

    def test_empty_stocks(self):
        result = _apply_filters([], {"pe_max": 10})
        assert result == []


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        assert await _check_rate_limit() is True

    @pytest.mark.asyncio
    async def test_blocks_after_limit(self):
        for _ in range(SCREEN_RATE_LIMIT):
            await _check_rate_limit()
        assert await _check_rate_limit() is False


class TestScreenStocks:
    @pytest.mark.asyncio
    async def test_no_criteria(self):
        result = await screen_stocks()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_preset_filter(self):
        am = AsyncMock
        mock_data = [
            {
                "code": "A", "name": "低估值", "price": 100,
                "change_pct": 1, "volume": 1000, "amount": 10000,
                "pe_ratio": 10, "pb_ratio": 1.5, "market_cap": 6e10,
            },
            {
                "code": "B", "name": "高估值", "price": 200,
                "change_pct": 2, "volume": 2000, "amount": 20000,
                "pe_ratio": 50, "pb_ratio": 5.0, "market_cap": 1e8,
            },
        ]
        with patch(
            "app.services.screener._get_market_snapshot",
            new_callable=am, return_value=mock_data,
        ):
            result = await screen_stocks(preset="低估值蓝筹")
            assert not result.get("error")
            codes = [s["code"] for s in result["stocks"]]
            assert "A" in codes
            assert "B" not in codes

    @pytest.mark.asyncio
    async def test_malformed_query_handled(self):
        """Malformed AI query should not crash."""
        am = AsyncMock
        with (
            patch(
                "app.services.screener._parse_criteria_with_ai",
                new_callable=am, return_value={},
            ),
            patch(
                "app.services.screener._get_market_snapshot",
                new_callable=am, return_value=[],
            ),
        ):
            result = await screen_stocks(query="随便写的条件")
            assert isinstance(result["stocks"], list)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Should return error when rate limited."""
        for _ in range(SCREEN_RATE_LIMIT):
            await _check_rate_limit()
        result = await screen_stocks(query="test")
        assert "error" in result
        assert "频繁" in result["error"]
