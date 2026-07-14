"""Tests for AI analysis service (DeepSeek integration)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai import (
    AI_DISCLAIMER,
    MAX_RESPONSE_CHARS,
    analyze_stock,
    summarize_news,
)

_MKT = "app.services.market_data"


@pytest.fixture(autouse=True)
def clear_cache():
    from app.services.cache import get_cache

    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


def _mock_deepseek_call(response_text: str):
    """Create mock OpenAI client for DeepSeek."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=response_text))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create = MagicMock(
        return_value=mock_response
    )
    return mock_client


@contextmanager
def _ai_patches(mock_client, api_key="test-key"):
    """Patch DeepSeek + market data for AI tests."""
    am = AsyncMock
    with (
        patch("app.services.ai.get_settings") as ms,
        patch(f"{_MKT}.get_realtime_quotes", new_callable=am, return_value=[]),
        patch(f"{_MKT}.get_financial_summary", new_callable=am, return_value=None),
        patch(f"{_MKT}.get_stock_news", new_callable=am, return_value=[]),
        patch("openai.OpenAI", return_value=mock_client),
        patch("app.services.ai._log_ai_call", new_callable=am),
    ):
        ms.return_value = MagicMock(deepseek_api_key=api_key)
        yield ms


class TestAnalyzeStock:
    @pytest.mark.asyncio
    async def test_no_api_key(self):
        with patch("app.services.ai.get_settings") as ms:
            ms.return_value = MagicMock(deepseek_api_key="")
            result = await analyze_stock("600519")
            txt = result["analysis"]
            assert "not configured" in txt.lower() or "DEEPSEEK" in txt
            assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_disclaimer_always_appended(self):
        mc = _mock_deepseek_call("测试分析结果")
        with _ai_patches(mc):
            result = await analyze_stock("600519")
            assert AI_DISCLAIMER in result["analysis"]

    @pytest.mark.asyncio
    async def test_response_length_cap(self):
        long_text = "分析" * 500
        mc = _mock_deepseek_call(long_text)
        with _ai_patches(mc):
            result = await analyze_stock("600519")
            analysis = result["analysis"]
            before = analysis.split(AI_DISCLAIMER)[0].strip()
            assert len(before) <= MAX_RESPONSE_CHARS + 10

    @pytest.mark.asyncio
    async def test_cached_result(self):
        from app.services.cache import get_cache

        cache = get_cache()
        await cache.set("ai_analysis:600519", "cached", 300)
        result = await analyze_stock("600519")
        assert result["analysis"] == "cached"
        assert result["cached"] is True


class TestSummarizeNews:
    @pytest.mark.asyncio
    async def test_no_news(self):
        with patch(
            f"{_MKT}.get_stock_news",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await summarize_news("600519")
            assert "暂无" in result["summary"]

    @pytest.mark.asyncio
    async def test_disclaimer_in_summary(self):
        from app.models.market import NewsItem

        mock_news = [
            NewsItem(title="茅台发布年报", source="证券时报", url="u1"),
            NewsItem(title="白酒行业分析", source="财经网", url="u2"),
        ]
        mc = _mock_deepseek_call("新闻摘要测试")
        am = AsyncMock
        with (
            patch(f"{_MKT}.get_stock_news", new_callable=am, return_value=mock_news),
            patch("app.services.ai.get_settings") as ms,
            patch("openai.OpenAI", return_value=mc),
            patch("app.services.ai._log_ai_call", new_callable=am),
        ):
            ms.return_value = MagicMock(deepseek_api_key="k")
            result = await summarize_news("600519")
            assert AI_DISCLAIMER in result["summary"]
