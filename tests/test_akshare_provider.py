"""Tests for AKShareTHSProvider with mocked akshare module (no network)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.providers.akshare_ths import AKShareTHSProvider
from app.providers.rate_limiter import RateLimiter


@pytest.fixture
def provider():
    # Use a very short interval so tests run fast
    limiter = RateLimiter(min_interval=0.0)
    return AKShareTHSProvider(rate_limiter=limiter)


def _make_spot_df():
    """Fake stock_zh_a_spot response."""
    return pd.DataFrame(
        [
            {
                "代码": "000001",
                "名称": "平安银行",
                "最新价": 15.50,
                "涨跌幅": 1.23,
                "成交量": 500000,
            },
            {
                "代码": "600519",
                "名称": "贵州茅台",
                "最新价": 1800.00,
                "涨跌幅": -0.5,
                "成交量": 30000,
            },
        ]
    )


def _make_news_df():
    """Fake stock_news_em response."""
    return pd.DataFrame(
        [
            {
                "新闻标题": "平安银行发布年报",
                "新闻链接": "https://example.com/1",
                "文章来源": "证券时报",
                "发布时间": "2026-07-14 10:00:00",
            },
            {
                "新闻标题": "银行板块走强",
                "新闻链接": "https://example.com/2",
                "文章来源": "东方财富",
                "发布时间": "2026-07-14 09:30:00",
            },
        ]
    )


def _make_financial_df():
    """Fake stock_financial_abstract_ths response."""
    return pd.DataFrame(
        [
            {
                "报告期": "2026-03-31",
                "市盈率": 8.5,
                "营业总收入": 50_000_000_000,
                "净利润": 10_000_000_000,
                "毛利率": 45.0,
                "净利率": 20.0,
            }
        ]
    )


def _make_code_name_df():
    """Fake stock_info_a_code_name response."""
    return pd.DataFrame(
        [
            {"code": "000001", "name": "平安银行"},
            {"code": "000002", "name": "万科A"},
            {"code": "600519", "name": "贵州茅台"},
        ]
    )


class TestGetQuote:
    @patch("app.providers.akshare_ths.ak")
    async def test_get_quote_success(self, mock_ak, provider):
        mock_ak.stock_zh_a_spot = MagicMock(return_value=_make_spot_df())
        quote = await provider.get_quote("000001")
        assert quote.symbol == "000001"
        assert quote.name == "平安银行"
        assert quote.price == 15.50
        assert quote.change_pct == 1.23

    @patch("app.providers.akshare_ths.ak")
    async def test_get_quote_not_found(self, mock_ak, provider):
        mock_ak.stock_zh_a_spot = MagicMock(return_value=_make_spot_df())
        with pytest.raises(ValueError, match="999999"):
            await provider.get_quote("999999")


class TestGetNews:
    @patch("app.providers.akshare_ths.ak")
    async def test_get_news_success(self, mock_ak, provider):
        mock_ak.stock_news_em = MagicMock(return_value=_make_news_df())
        news = await provider.get_news("000001")
        assert len(news) == 2
        assert news[0].title == "平安银行发布年报"
        assert news[0].source == "证券时报"
        assert news[0].symbol == "000001"

    @patch("app.providers.akshare_ths.ak")
    async def test_get_news_limit(self, mock_ak, provider):
        mock_ak.stock_news_em = MagicMock(return_value=_make_news_df())
        news = await provider.get_news("000001", limit=1)
        assert len(news) == 1


class TestGetFinancials:
    @patch("app.providers.akshare_ths.ak")
    async def test_get_financials_success(self, mock_ak, provider):
        mock_ak.stock_financial_abstract_ths = MagicMock(
            return_value=_make_financial_df()
        )
        fin = await provider.get_financials("000001")
        assert fin.symbol == "000001"
        assert fin.pe_ratio == 8.5
        assert fin.revenue == 50_000_000_000

    @patch("app.providers.akshare_ths.ak")
    async def test_get_financials_empty(self, mock_ak, provider):
        mock_ak.stock_financial_abstract_ths = MagicMock(
            return_value=pd.DataFrame()
        )
        fin = await provider.get_financials("000001")
        assert fin.pe_ratio is None


class TestSearchStocks:
    @patch("app.providers.akshare_ths.ak")
    async def test_search_by_name(self, mock_ak, provider):
        mock_ak.stock_info_a_code_name = MagicMock(
            return_value=_make_code_name_df()
        )
        results = await provider.search_stocks("平安")
        assert len(results) == 1
        assert results[0].symbol == "000001"

    @patch("app.providers.akshare_ths.ak")
    async def test_search_by_code(self, mock_ak, provider):
        mock_ak.stock_info_a_code_name = MagicMock(
            return_value=_make_code_name_df()
        )
        results = await provider.search_stocks("600519")
        assert len(results) == 1
        assert results[0].name == "贵州茅台"


class TestRetry:
    @patch("app.providers.akshare_ths.ak")
    async def test_retry_on_http_error(self, mock_ak, provider):
        exc = Exception("HTTP 429 Too Many Requests")
        mock_ak.stock_zh_a_spot = MagicMock(
            side_effect=[exc, _make_spot_df()]
        )
        quote = await provider.get_quote("000001")
        assert quote.price == 15.50
        assert mock_ak.stock_zh_a_spot.call_count == 2

    @patch("app.providers.akshare_ths.ak")
    async def test_exhausted_retries_raises(self, mock_ak, provider):
        exc = Exception("HTTP 500 Server Error")
        mock_ak.stock_zh_a_spot = MagicMock(side_effect=exc)
        with pytest.raises(RuntimeError, match="failed after"):
            await provider.get_quote("000001")
