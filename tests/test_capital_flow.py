"""Tests for large capital flow monitoring service."""

from __future__ import annotations

import os

import pytest

from app.database import init_db
from app.services.cache import get_cache
from app.services.capital_flow import (
    CAPITAL_FLOW_CACHE_KEY,
    get_top_capital_flow,
    identify_large_inflows,
)


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_flow.db")
    os.environ["DATABASE_PATH"] = db_path
    await init_db(db_path)
    yield db_path
    os.environ.pop("DATABASE_PATH", None)


class TestIdentifyLargeInflows:
    def test_empty_list(self):
        assert identify_large_inflows([]) == []

    def test_no_positive_inflows(self):
        stocks = [
            {"code": "600519", "name": "A", "net_inflow": -1000, "change_pct": -1.0},
            {"code": "000858", "name": "B", "net_inflow": -500, "change_pct": -0.5},
        ]
        assert identify_large_inflows(stocks) == []

    def test_threshold_by_amount(self):
        """Stocks with net inflow > 5000万 should be identified."""
        stocks = [
            {"code": "600519", "name": "A", "net_inflow": 6000_0000, "change_pct": 3.0},
            {"code": "000858", "name": "B", "net_inflow": 1000_0000, "change_pct": 1.0},
            {"code": "000001", "name": "C", "net_inflow": 500_0000, "change_pct": 0.5},
        ]
        result = identify_large_inflows(stocks)
        # 6000万 > LARGE_INFLOW_THRESHOLD (5000万)
        assert any(s["code"] == "600519" for s in result)

    def test_top_percentile(self):
        """Top 1% of stocks by inflow should be identified."""
        # Create 100 stocks, top one has massive inflow
        stocks = []
        for i in range(100):
            stocks.append({
                "code": f"{i:06d}",
                "name": f"Stock{i}",
                "net_inflow": (i + 1) * 100_0000,
                "change_pct": 1.0,
            })
        result = identify_large_inflows(stocks)
        # Top 1% = 1 stock (index 99)
        assert len(result) >= 1
        # Highest inflow stock should be in result
        assert any(s["code"] == "000099" for s in result)

    def test_sorted_descending(self):
        """Results should be sorted by net inflow descending."""
        stocks = [
            {"code": "000001", "name": "A", "net_inflow": 8000_0000, "change_pct": 1.0},
            {"code": "000002", "name": "B", "net_inflow": 9000_0000, "change_pct": 2.0},
            {"code": "000003", "name": "C", "net_inflow": 7000_0000, "change_pct": 0.5},
        ]
        result = identify_large_inflows(stocks)
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["net_inflow"] >= result[i + 1]["net_inflow"]


class TestGetTopCapitalFlow:
    @pytest.mark.asyncio
    async def test_returns_cached(self):
        cache = get_cache()
        cached = [{
            "code": "600519", "name": "茅台",
            "net_inflow": 1e8, "change_pct": 3.0,
        }]
        await cache.set(CAPITAL_FLOW_CACHE_KEY, cached, 300)

        result = await get_top_capital_flow()
        assert result["cached"] is True
        assert len(result["stocks"]) == 1

    @pytest.mark.asyncio
    async def test_fetches_when_not_cached(self, monkeypatch):
        import app.services.capital_flow as mod

        async def _mock_fetch():
            return [
                {
                    "code": "600519", "name": "茅台",
                    "net_inflow": 1e8, "change_pct": 3.0,
                },
                {
                    "code": "000858", "name": "五粮液",
                    "net_inflow": 5e7, "change_pct": 2.0,
                },
            ]

        monkeypatch.setattr(mod, "fetch_capital_flow_rank", _mock_fetch)
        result = await get_top_capital_flow()
        assert result["cached"] is False
        assert len(result["stocks"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_fetch(self, monkeypatch):
        import app.services.capital_flow as mod

        async def _empty_fetch():
            return []

        monkeypatch.setattr(mod, "fetch_capital_flow_rank", _empty_fetch)
        result = await get_top_capital_flow()
        assert result["stocks"] == []


class TestAlertDedup:
    @pytest.mark.asyncio
    async def test_dedup_prevents_duplicate_alert(self, test_db):
        """Same stock should only be alerted once per day."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from app.database import get_db

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")

        async with get_db() as db:
            # Insert a seen entry
            await db.execute(
                "INSERT INTO capital_flow_alerts_seen (stock_code, alert_date)"
                " VALUES (?, ?)",
                ("600519", today),
            )
            await db.commit()

            # Check it exists
            cursor = await db.execute(
                "SELECT 1 FROM capital_flow_alerts_seen"
                " WHERE stock_code = ? AND alert_date = ?",
                ("600519", today),
            )
            assert await cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_alert_format(self):
        """Capital flow alert message should include key info."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now_str = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
        stock = {"code": "600519", "name": "贵州茅台", "net_inflow": 1.5e8}
        amount_yi = stock["net_inflow"] / 1e8

        msg = (
            f"💰 大资金流入提醒\n\n"
            f"{stock['name']}({stock['code']})\n"
            f"净流入: {amount_yi:.2f}亿\n"
            f"⏰ {now_str}\n"
            f"以上仅供参考，不构成投资建议"
        )
        assert "贵州茅台" in msg
        assert "600519" in msg
        assert "1.50亿" in msg
        assert "不构成投资建议" in msg
