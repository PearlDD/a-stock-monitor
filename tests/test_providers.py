"""Tests for MockProvider."""

import pytest

from app.models.market import FinancialSummary, StockInfo
from app.providers.mock import MockProvider


@pytest.fixture
def provider():
    return MockProvider()


@pytest.mark.asyncio
async def test_get_quote_default_price(provider):
    """Unset symbols return the default price."""
    quote = await provider.get_quote("000001")
    assert quote.symbol == "000001"
    assert quote.price == 100.0


@pytest.mark.asyncio
async def test_set_price(provider):
    """set_price controls the price returned by get_quote."""
    provider.set_price("000001", 25.5, change_pct=1.2)
    quote = await provider.get_quote("000001")
    assert quote.price == 25.5
    assert quote.change_pct == 1.2


@pytest.mark.asyncio
async def test_inject_news(provider):
    """inject_news adds retrievable news items."""
    provider.inject_news("000001", "Test headline", keywords=["test"])
    news = await provider.get_news("000001")
    assert len(news) == 1
    assert news[0].title == "Test headline"
    assert news[0].keywords == ["test"]


@pytest.mark.asyncio
async def test_get_news_empty(provider):
    """Symbols with no injected news return empty list."""
    news = await provider.get_news("999999")
    assert news == []


@pytest.mark.asyncio
async def test_get_news_limit(provider):
    """get_news respects the limit parameter."""
    for i in range(5):
        provider.inject_news("000001", f"News {i}")
    news = await provider.get_news("000001", limit=3)
    assert len(news) == 3


@pytest.mark.asyncio
async def test_get_financials_default(provider):
    """Default financials return stub with None fields."""
    fin = await provider.get_financials("000001")
    assert fin.symbol == "000001"
    assert fin.pe_ratio is None


@pytest.mark.asyncio
async def test_set_financials(provider):
    """set_financials controls returned data."""
    summary = FinancialSummary(symbol="000001", name="TestCo", pe_ratio=15.0)
    provider.set_financials(summary)
    fin = await provider.get_financials("000001")
    assert fin.pe_ratio == 15.0


@pytest.mark.asyncio
async def test_search_stocks(provider):
    """search_stocks finds added stocks matching keyword."""
    provider.add_stock(StockInfo(symbol="000001", name="平安银行"))
    results = await provider.search_stocks("平安")
    assert len(results) == 1
    assert results[0].symbol == "000001"


@pytest.mark.asyncio
async def test_search_stocks_no_match(provider):
    """search_stocks returns empty for non-matching keywords."""
    provider.add_stock(StockInfo(symbol="000001", name="平安银行"))
    results = await provider.search_stocks("贵州茅台")
    assert results == []
