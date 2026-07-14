"""Tests for AKShare THS provider with mocked ak module (no network)."""

from unittest.mock import patch

import akshare
import pandas as pd
import pytest

from app.providers.akshare_ths import AKShareTHSProvider
from app.providers.rate_limiter import RateLimiter


@pytest.fixture
def provider():
    return AKShareTHSProvider()


@pytest.fixture(autouse=True)
def fast_rate_limiter():
    """Use a fast rate limiter for tests."""
    limiter = RateLimiter(min_interval=0.0)
    with patch("app.providers.akshare_ths.get_rate_limiter", return_value=limiter):
        yield limiter


def _spot_df():
    """Standard mock DataFrame for stock_zh_a_spot_em."""
    return pd.DataFrame(
        {
            "代码": ["600519", "000858", "000001"],
            "名称": ["贵州茅台", "五粮液", "平安银行"],
            "最新价": [1800.0, 168.0, 50.0],
            "涨跌幅": [3.5, -1.2, 0.5],
            "成交量": [10000, 20000, 30000],
            "成交额": [1e9, 2e8, 5e7],
            "最高": [1820, 170, 51],
            "最低": [1780, 165, 49],
            "今开": [1790, 169, 50],
            "昨收": [1750, 170, 49.5],
        }
    )


class TestGetRealtimeQuotes:
    @pytest.mark.asyncio
    async def test_returns_filtered_quotes(self, provider, monkeypatch):
        mock_df = _spot_df()
        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", lambda: mock_df)
        quotes = await provider.get_realtime_quotes(["600519", "000001"])
        assert len(quotes) == 2
        codes = {q.code for q in quotes}
        assert codes == {"600519", "000001"}
        maotai = next(q for q in quotes if q.code == "600519")
        assert maotai.price == 1800.0
        assert maotai.name == "贵州茅台"
        assert maotai.change_pct == 3.5
        assert maotai.timestamp is not None

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, provider, monkeypatch):
        def _raise():
            raise Exception("Network error")

        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", _raise)
        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes == []

    @pytest.mark.asyncio
    async def test_empty_codes_returns_empty(self, provider, monkeypatch):
        mock_df = _spot_df()
        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", lambda: mock_df)
        quotes = await provider.get_realtime_quotes(["999999"])
        assert quotes == []


class TestGetStockInfo:
    @pytest.mark.asyncio
    async def test_returns_info(self, provider, monkeypatch):
        mock_df = _spot_df()
        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", lambda: mock_df)
        info = await provider.get_stock_info("600519")
        assert info is not None
        assert info.name == "贵州茅台"
        assert info.code == "600519"

    @pytest.mark.asyncio
    async def test_returns_none_on_not_found(self, provider, monkeypatch):
        mock_df = pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["平安银行"],
                "最新价": [50.0],
                "涨跌幅": [0],
                "成交量": [0],
                "成交额": [0],
                "最高": [0],
                "最低": [0],
                "今开": [0],
                "昨收": [0],
            }
        )
        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", lambda: mock_df)
        info = await provider.get_stock_info("999999")
        assert info is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, provider, monkeypatch):
        def _raise():
            raise Exception("fail")

        monkeypatch.setattr(akshare, "stock_zh_a_spot_em", _raise)
        info = await provider.get_stock_info("600519")
        assert info is None


class TestGetStockNews:
    @pytest.mark.asyncio
    async def test_returns_news(self, provider, monkeypatch):
        mock_df = pd.DataFrame(
            {
                "新闻标题": ["茅台涨停", "茅台业绩"],
                "新闻来源": ["新浪", "东财"],
                "新闻链接": ["http://a.com", "http://b.com"],
                "发布时间": ["2026-07-14 10:30:00", "2026-07-14 09:00:00"],
            }
        )
        monkeypatch.setattr(akshare, "stock_news_em", lambda **kw: mock_df)
        news = await provider.get_stock_news("600519", limit=10)
        assert len(news) == 2
        assert news[0].title == "茅台涨停"
        assert news[0].source == "新浪"
        assert news[0].stock_code == "600519"
        assert news[0].publish_time is not None

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, provider, monkeypatch):
        def _raise(**kw):
            raise Exception("fail")

        monkeypatch.setattr(akshare, "stock_news_em", _raise)
        news = await provider.get_stock_news("600519")
        assert news == []

    @pytest.mark.asyncio
    async def test_limit_respected(self, provider, monkeypatch):
        mock_df = pd.DataFrame(
            {
                "新闻标题": [f"News {i}" for i in range(20)],
                "新闻来源": ["src"] * 20,
                "新闻链接": [f"http://n{i}.com" for i in range(20)],
                "发布时间": [""] * 20,
            }
        )
        monkeypatch.setattr(akshare, "stock_news_em", lambda **kw: mock_df)
        news = await provider.get_stock_news("600519", limit=5)
        assert len(news) == 5


class TestGetFinancialSummary:
    @pytest.mark.asyncio
    async def test_returns_summary(self, provider, monkeypatch):
        mock_df = pd.DataFrame(
            {
                "股票简称": ["贵州茅台"],
                "市盈率": [35.2],
                "市净率": [12.5],
                "营业总收入": [1.5e10],
                "净利润": [7e9],
            }
        )
        monkeypatch.setattr(
            akshare, "stock_financial_abstract_ths", lambda **kw: mock_df
        )
        summary = await provider.get_financial_summary("600519")
        assert summary is not None
        assert summary.pe_ratio == 35.2
        assert summary.net_profit == 7e9

    @pytest.mark.asyncio
    async def test_returns_none_on_empty(self, provider, monkeypatch):
        mock_df = pd.DataFrame()
        monkeypatch.setattr(
            akshare, "stock_financial_abstract_ths", lambda **kw: mock_df
        )
        summary = await provider.get_financial_summary("600519")
        assert summary is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, provider, monkeypatch):
        def _raise(**kw):
            raise Exception("fail")

        monkeypatch.setattr(akshare, "stock_financial_abstract_ths", _raise)
        summary = await provider.get_financial_summary("600519")
        assert summary is None
