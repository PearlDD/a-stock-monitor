"""Tests for quote fallback behavior outside trading hours."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from app.models.market import StockQuote
from app.services.cache import get_cache
from app.services.market_data import (
    _fallback_hist_quotes,
    _stamp_market_status,
    get_realtime_quotes,
)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    from app.services.market_data import get_circuit_breaker

    get_circuit_breaker().reset()


@pytest.fixture(autouse=True)
def use_akshare_source(monkeypatch):
    """Force AKShare path so these tests exercise the AKShare fallback logic."""
    import app.services.market_data as md

    monkeypatch.setattr(md, "_use_tencent", lambda: False)


class TestMarketStatusStamping:
    def test_stamp_market_status_trading(self):
        quotes = [
            StockQuote(
                code="600519", name="茅台", price=1800,
                change_pct=0, volume=0, amount=0,
                high=0, low=0, open=0, prev_close=0,
            )
        ]
        result = _stamp_market_status(quotes, "trading")
        assert result[0].market_status == "trading"

    def test_stamp_market_status_closed(self):
        quotes = [
            StockQuote(
                code="600519", name="茅台", price=1800,
                change_pct=0, volume=0, amount=0,
                high=0, low=0, open=0, prev_close=0,
            )
        ]
        result = _stamp_market_status(quotes, "closed")
        assert result[0].market_status == "closed"

    def test_stamp_empty_list(self):
        result = _stamp_market_status([], "closed")
        assert result == []


class TestQuotesDuringTradingHours:
    @pytest.mark.asyncio
    async def test_quotes_have_trading_status(self, monkeypatch):
        """During trading hours, quotes should have market_status='trading'."""
        import pandas as pd

        import app.services.market_data as md

        df = pd.DataFrame([{
            "代码": "600519", "名称": "茅台", "最新价": 1800,
            "涨跌幅": 1.5, "成交量": 100000, "成交额": 1e8,
            "最高": 1810, "最低": 1790, "今开": 1795, "昨收": 1773,
        }])

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)
        monkeypatch.setattr(
            "app.services.trading_calendar.get_market_status",
            AsyncMock(return_value="trading"),
        )

        quotes = await get_realtime_quotes(["600519"])
        assert len(quotes) == 1
        assert quotes[0].market_status == "trading"
        assert quotes[0].price == 1800


class TestQuotesOutsideTradingHours:
    @pytest.mark.asyncio
    async def test_spot_data_returns_last_close(self, monkeypatch):
        """Outside hours, spot_em returns data with status='closed'."""
        import pandas as pd

        import app.services.market_data as md

        df = pd.DataFrame([{
            "代码": "600519", "名称": "茅台", "最新价": 1800,
            "涨跌幅": 1.5, "成交量": 100000, "成交额": 1e8,
            "最高": 1810, "最低": 1790, "今开": 1795, "昨收": 1773,
        }])

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)
        monkeypatch.setattr(
            "app.services.trading_calendar.get_market_status",
            AsyncMock(return_value="closed"),
        )

        quotes = await get_realtime_quotes(["600519"])
        assert len(quotes) == 1
        assert quotes[0].market_status == "closed"
        assert quotes[0].price == 1800

    @pytest.mark.asyncio
    async def test_hist_fallback_when_spot_missing_codes(self, monkeypatch):
        """If spot data doesn't contain a requested code, fall back to hist."""
        import pandas as pd

        import app.services.market_data as md

        # Spot data has 600519 but not 000858
        spot_df = pd.DataFrame([{
            "代码": "600519", "名称": "茅台", "最新价": 1800,
            "涨跌幅": 1.5, "成交量": 100000, "成交额": 1e8,
            "最高": 1810, "最低": 1790, "今开": 1795, "昨收": 1773,
        }])

        # Hist data for 000858
        hist_df = pd.DataFrame([
            {"日期": "2026-07-14", "收盘": 165, "开盘": 163,
             "最高": 167, "最低": 162, "成交量": 50000, "成交额": 5e7},
            {"日期": "2026-07-15", "收盘": 168, "开盘": 166,
             "最高": 170, "最低": 165, "成交量": 60000, "成交额": 6e7},
        ])

        call_count = 0

        async def mock_retry(func, *a, **kw):
            nonlocal call_count
            md.get_circuit_breaker().record_success()
            call_count += 1
            if call_count == 1:
                return spot_df
            return hist_df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)
        monkeypatch.setattr(
            "app.services.trading_calendar.get_market_status",
            AsyncMock(return_value="closed"),
        )

        quotes = await get_realtime_quotes(["600519", "000858"])
        assert len(quotes) == 2
        codes = {q.code for q in quotes}
        assert "600519" in codes
        assert "000858" in codes

        hist_q = next(q for q in quotes if q.code == "000858")
        assert hist_q.price == 168
        assert hist_q.market_status == "closed"
        # change_pct should be calculated from prev close
        assert abs(hist_q.change_pct - round((168 - 165) / 165 * 100, 2)) < 0.1

    @pytest.mark.asyncio
    async def test_full_hist_fallback_when_spot_fails(self, monkeypatch):
        """If spot_em entirely fails outside hours, fall back to hist for all codes."""
        import pandas as pd

        import app.services.market_data as md

        hist_df = pd.DataFrame([
            {"日期": "2026-07-15", "收盘": 1800, "开盘": 1790,
             "最高": 1810, "最低": 1785, "成交量": 80000, "成交额": 1e8},
        ])

        call_count = 0

        async def mock_retry(func, *a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("network error")
            md.get_circuit_breaker().record_success()
            return hist_df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)
        monkeypatch.setattr(
            "app.services.trading_calendar.get_market_status",
            AsyncMock(return_value="closed"),
        )

        quotes = await get_realtime_quotes(["600519"])
        assert len(quotes) == 1
        assert quotes[0].price == 1800
        assert quotes[0].market_status == "closed"

    @pytest.mark.asyncio
    async def test_no_fallback_during_trading_hours(self, monkeypatch):
        """During trading hours, don't fall back to hist even if spot is empty."""
        import pandas as pd

        import app.services.market_data as md

        # Spot returns empty for requested codes
        spot_df = pd.DataFrame([{
            "代码": "999999", "名称": "Other", "最新价": 10,
            "涨跌幅": 0, "成交量": 0, "成交额": 0,
            "最高": 0, "最低": 0, "今开": 0, "昨收": 0,
        }])

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return spot_df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)
        monkeypatch.setattr(
            "app.services.trading_calendar.get_market_status",
            AsyncMock(return_value="trading"),
        )

        quotes = await get_realtime_quotes(["600519"])
        assert len(quotes) == 0  # no fallback during trading


class TestFallbackHistQuotes:
    @pytest.mark.asyncio
    async def test_hist_returns_last_day(self, monkeypatch):
        import pandas as pd

        import app.services.market_data as md

        hist_df = pd.DataFrame([
            {"日期": "2026-07-14", "收盘": 165, "开盘": 163,
             "最高": 167, "最低": 162, "成交量": 50000, "成交额": 5e7},
            {"日期": "2026-07-15", "收盘": 168, "开盘": 166,
             "最高": 170, "最低": 165, "成交量": 60000, "成交额": 6e7},
        ])

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return hist_df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)

        now = datetime.now(tz=SHANGHAI_TZ)
        quotes = await _fallback_hist_quotes(["000858"], now)
        assert len(quotes) == 1
        assert quotes[0].code == "000858"
        assert quotes[0].price == 168
        assert quotes[0].prev_close == 165

    @pytest.mark.asyncio
    async def test_hist_empty_returns_nothing(self, monkeypatch):
        import pandas as pd

        import app.services.market_data as md

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return pd.DataFrame()

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)

        now = datetime.now(tz=SHANGHAI_TZ)
        quotes = await _fallback_hist_quotes(["000858"], now)
        assert quotes == []

    @pytest.mark.asyncio
    async def test_hist_single_row(self, monkeypatch):
        """With only one row of history, prev_close should equal close."""
        import pandas as pd

        import app.services.market_data as md

        hist_df = pd.DataFrame([
            {"日期": "2026-07-15", "收盘": 100, "开盘": 99,
             "最高": 101, "最低": 98, "成交量": 10000, "成交额": 1e6},
        ])

        async def mock_retry(func, *a, **kw):
            md.get_circuit_breaker().record_success()
            return hist_df

        monkeypatch.setattr(md, "_retry_akshare", mock_retry)

        now = datetime.now(tz=SHANGHAI_TZ)
        quotes = await _fallback_hist_quotes(["600519"], now)
        assert len(quotes) == 1
        assert quotes[0].prev_close == 100  # same as close when only 1 row


class TestQuoteRouterMarketStatus:
    @pytest.mark.asyncio
    async def test_router_includes_market_status(self, monkeypatch):
        """The /api/stocks/quotes response should include market_status."""
        import app.services.market_data as md

        async def _mock_quotes(codes):
            return [
                StockQuote(
                    code="600519", name="茅台", price=1800,
                    change_pct=0, volume=0, amount=0,
                    high=0, low=0, open=0, prev_close=0,
                    market_status="closed",
                )
            ]

        monkeypatch.setattr(md, "get_realtime_quotes", _mock_quotes)

        from fastapi.testclient import TestClient

        from app.main import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/stocks/quotes", params={"codes": "600519"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["market_status"] == "closed"
        assert data["quotes"][0]["market_status"] == "closed"
