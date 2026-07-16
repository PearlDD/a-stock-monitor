"""Tests for the DemoProvider and demo mode integration."""

from __future__ import annotations

import pytest

from app.providers.demo import DemoProvider


class TestDemoProvider:
    @pytest.fixture
    def provider(self):
        return DemoProvider()

    @pytest.mark.asyncio
    async def test_get_realtime_quotes_returns_data(self, provider):
        quotes = await provider.get_realtime_quotes(["600519", "000858"])
        assert len(quotes) == 2
        codes = {q.code for q in quotes}
        assert codes == {"600519", "000858"}

    @pytest.mark.asyncio
    async def test_quotes_have_demo_market_status(self, provider):
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes[0].market_status == "demo"

    @pytest.mark.asyncio
    async def test_quotes_have_realistic_prices(self, provider):
        quotes = await provider.get_realtime_quotes(["600519"])
        price = quotes[0].price
        # Should be near ¥1823 (±1%)
        assert 1800 < price < 1850

    @pytest.mark.asyncio
    async def test_price_jitter(self, provider):
        """Prices should vary slightly between fetches."""
        prices = set()
        for _ in range(10):
            quotes = await provider.get_realtime_quotes(["600519"])
            prices.add(quotes[0].price)
        # With ±0.5% jitter, 10 fetches should produce at least 2 distinct prices
        assert len(prices) >= 2

    @pytest.mark.asyncio
    async def test_unknown_code_returns_empty(self, provider):
        quotes = await provider.get_realtime_quotes(["999999"])
        assert quotes == []

    @pytest.mark.asyncio
    async def test_get_stock_info(self, provider):
        info = await provider.get_stock_info("600519")
        assert info is not None
        assert info.name == "贵州茅台"
        assert info.sector == "白酒"

    @pytest.mark.asyncio
    async def test_get_stock_info_unknown(self, provider):
        info = await provider.get_stock_info("999999")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_stock_news(self, provider):
        news = await provider.get_stock_news("600519")
        assert len(news) > 0
        assert news[0].stock_code == "600519"

    @pytest.mark.asyncio
    async def test_get_stock_news_generic(self, provider):
        """Stocks without specific news get generic headlines."""
        news = await provider.get_stock_news("601012")
        assert len(news) > 0

    @pytest.mark.asyncio
    async def test_get_financial_summary(self, provider):
        fin = await provider.get_financial_summary("600519")
        assert fin is not None
        assert fin.pe_ratio == 33.5
        assert fin.market_cap > 0

    @pytest.mark.asyncio
    async def test_get_financial_summary_generic(self, provider):
        """Stocks without specific financials get random but valid data."""
        fin = await provider.get_financial_summary("601012")
        assert fin is not None
        assert fin.pe_ratio > 0

    @pytest.mark.asyncio
    async def test_all_demo_stocks_accessible(self, provider):
        """All 23 demo stocks should return quotes."""
        all_codes = [
            "600519", "000858", "300750", "601318", "000001",
            "601899", "002594", "600036", "601012", "000333",
            "600900", "002475", "601888", "300059", "600276",
            "002304", "601398", "600030", "000568", "002714",
            "300124", "601166", "002415",
        ]
        quotes = await provider.get_realtime_quotes(all_codes)
        assert len(quotes) == 23


class TestDemoModeIntegration:
    @pytest.fixture(autouse=True)
    def _mock_settings(self, monkeypatch):
        from app.config import Settings

        mock = Settings(data_mode="mock")
        monkeypatch.setattr(
            "app.config.get_settings", lambda: mock,
        )

    @pytest.mark.asyncio
    async def test_market_status_returns_demo(self):
        from app.services.trading_calendar import get_market_status

        status = await get_market_status()
        assert status == "demo"

    @pytest.mark.asyncio
    async def test_sector_rotation_returns_demo(self):
        from app.services.sector_rotation import predict_sector_rotation

        result = await predict_sector_rotation()
        assert len(result["predictions"]) > 0
        assert "演示数据" in result["disclaimer"]

    @pytest.mark.asyncio
    async def test_capital_flow_returns_demo(self):
        from app.services.capital_flow import get_top_capital_flow

        result = await get_top_capital_flow()
        assert len(result["stocks"]) == 10
