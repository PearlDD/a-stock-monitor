"""Tests for MockProvider."""

import pytest

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.mock import MockProvider


@pytest.fixture
def provider():
    return MockProvider()


class TestMockProviderSetPrice:
    """Test set_price and get_realtime_quotes."""

    @pytest.mark.asyncio
    async def test_set_and_get_price(self, provider: MockProvider):
        provider.set_price("600519", 1823.50, name="贵州茅台")
        quotes = await provider.get_realtime_quotes(["600519"])
        assert len(quotes) == 1
        assert quotes[0].code == "600519"
        assert quotes[0].price == 1823.50
        assert quotes[0].name == "贵州茅台"

    @pytest.mark.asyncio
    async def test_unknown_code_returns_empty(self, provider: MockProvider):
        quotes = await provider.get_realtime_quotes(["999999"])
        assert quotes == []

    @pytest.mark.asyncio
    async def test_multiple_codes(self, provider: MockProvider):
        provider.set_price("600519", 1823.50, name="贵州茅台")
        provider.set_price("000858", 168.20, name="五粮液")
        quotes = await provider.get_realtime_quotes(["600519", "000858"])
        assert len(quotes) == 2
        codes = {q.code for q in quotes}
        assert codes == {"600519", "000858"}

    @pytest.mark.asyncio
    async def test_change_pct_and_prev_close(self, provider: MockProvider):
        provider.set_price("600519", 1823.50, change_pct=3.84, prev_close=1756.0)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes[0].change_pct == 3.84
        assert quotes[0].prev_close == 1756.0

    @pytest.mark.asyncio
    async def test_quote_has_timestamp(self, provider: MockProvider):
        provider.set_price("600519", 100.0)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes[0].timestamp is not None

    @pytest.mark.asyncio
    async def test_default_name(self, provider: MockProvider):
        provider.set_price("600519", 100.0)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes[0].name == "Mock-600519"

    @pytest.mark.asyncio
    async def test_update_price(self, provider: MockProvider):
        provider.set_price("600519", 100.0)
        provider.set_price("600519", 200.0)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes[0].price == 200.0

    @pytest.mark.asyncio
    async def test_quote_is_stockquote(self, provider: MockProvider):
        provider.set_price("600519", 100.0)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert isinstance(quotes[0], StockQuote)


class TestMockProviderNews:
    """Test inject_news and get_stock_news."""

    @pytest.mark.asyncio
    async def test_inject_and_get_news(self, provider: MockProvider):
        items = [
            NewsItem(title="茅台涨停", source="新浪", url="http://example.com"),
            NewsItem(title="茅台财报", source="东财", url="http://example.com/2"),
        ]
        provider.inject_news("600519", items)
        news = await provider.get_stock_news("600519")
        assert len(news) == 2
        assert news[0].title == "茅台涨停"

    @pytest.mark.asyncio
    async def test_news_limit(self, provider: MockProvider):
        items = [NewsItem(title=f"News {i}", source="src", url="u") for i in range(20)]
        provider.inject_news("600519", items)
        news = await provider.get_stock_news("600519", limit=5)
        assert len(news) == 5

    @pytest.mark.asyncio
    async def test_no_news_returns_empty(self, provider: MockProvider):
        news = await provider.get_stock_news("600519")
        assert news == []


class TestMockProviderInfo:
    """Test set_info and get_stock_info."""

    @pytest.mark.asyncio
    async def test_set_and_get_info(self, provider: MockProvider):
        info = StockInfo(code="600519", name="贵州茅台", sector="白酒", market="上海")
        provider.set_info("600519", info)
        result = await provider.get_stock_info("600519")
        assert result is not None
        assert result.sector == "白酒"

    @pytest.mark.asyncio
    async def test_unknown_info_returns_none(self, provider: MockProvider):
        result = await provider.get_stock_info("999999")
        assert result is None


class TestMockProviderFinancials:
    """Test set_financials and get_financial_summary."""

    @pytest.mark.asyncio
    async def test_set_and_get_financials(self, provider: MockProvider):
        fs = FinancialSummary(
            code="600519", name="贵州茅台", pe_ratio=35.2, market_cap=2.3e12,
        )
        provider.set_financials("600519", fs)
        result = await provider.get_financial_summary("600519")
        assert result is not None
        assert result.pe_ratio == 35.2

    @pytest.mark.asyncio
    async def test_unknown_financials_returns_none(self, provider: MockProvider):
        result = await provider.get_financial_summary("999999")
        assert result is None
