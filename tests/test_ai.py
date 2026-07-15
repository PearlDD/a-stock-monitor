"""Tests for multi-provider AI analysis service."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai import (
    AI_DISCLAIMER,
    MAX_RESPONSE_CHARS,
    OPENAI_COMPATIBLE_PROVIDERS,
    _call_ai,
    _call_provider,
    _get_fallback_provider,
    _get_provider_api_key,
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


def _mock_claude_call(response_text: str):
    """Create mock Anthropic client for Claude."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(return_value=mock_response)
    return mock_client


def _make_settings(
    deepseek_key="test-deepseek-key",
    claude_key="test-claude-key",
    analysis_provider="claude",
    screening_provider="deepseek",
):
    """Create a mock settings object."""
    s = MagicMock()
    s.deepseek_api_key = deepseek_key
    s.claude_api_key = claude_key
    s.anthropic_api_key = ""
    s.effective_claude_api_key = claude_key
    s.ai_provider_analysis = analysis_provider
    s.ai_provider_screening = screening_provider
    return s


@contextmanager
def _ai_patches(
    mock_openai_client=None,
    mock_anthropic_client=None,
    settings=None,
):
    """Patch AI providers + market data for AI tests."""
    if settings is None:
        settings = _make_settings()
    if mock_openai_client is None:
        mock_openai_client = _mock_deepseek_call("测试结果")
    if mock_anthropic_client is None:
        mock_anthropic_client = _mock_claude_call("测试结果")

    am = AsyncMock
    with (
        patch("app.services.ai.get_settings", return_value=settings),
        patch(f"{_MKT}.get_realtime_quotes", new_callable=am, return_value=[]),
        patch(
            f"{_MKT}.get_financial_summary", new_callable=am, return_value=None
        ),
        patch(f"{_MKT}.get_stock_news", new_callable=am, return_value=[]),
        patch("openai.OpenAI", return_value=mock_openai_client),
        patch("anthropic.Anthropic", return_value=mock_anthropic_client),
        patch("app.services.ai._log_ai_call", new_callable=am),
    ):
        yield


class TestProviderSelection:
    """Test that different tasks route to the correct provider."""

    def test_get_provider_api_key_deepseek(self):
        s = _make_settings(deepseek_key="dk")
        assert _get_provider_api_key("deepseek", s) == "dk"

    def test_get_provider_api_key_claude(self):
        s = _make_settings(claude_key="ck")
        assert _get_provider_api_key("claude", s) == "ck"

    def test_fallback_claude_to_deepseek(self):
        assert _get_fallback_provider("claude") == "deepseek"

    def test_fallback_deepseek_to_claude(self):
        assert _get_fallback_provider("deepseek") == "claude"

    def test_fallback_openai_to_deepseek(self):
        assert _get_fallback_provider("openai") == "deepseek"

    @pytest.mark.asyncio
    async def test_analysis_uses_claude_provider(self):
        """analyze_stock should use AI_PROVIDER_ANALYSIS (claude by default)."""
        mc = _mock_claude_call("Claude分析结果")
        settings = _make_settings(analysis_provider="claude")
        with _ai_patches(mock_anthropic_client=mc, settings=settings):
            result = await analyze_stock("600519")
            assert "Claude分析结果" in result["analysis"]
            mc.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_screening_uses_deepseek_provider(self):
        """summarize_news should use AI_PROVIDER_SCREENING (deepseek by default)."""
        mc = _mock_deepseek_call("DeepSeek摘要")
        from app.models.market import NewsItem

        mock_news = [
            NewsItem(title="测试新闻", source="测试", url="u1"),
        ]
        settings = _make_settings(screening_provider="deepseek")
        am = AsyncMock
        with (
            patch("app.services.ai.get_settings", return_value=settings),
            patch(
                f"{_MKT}.get_stock_news",
                new_callable=am,
                return_value=mock_news,
            ),
            patch("openai.OpenAI", return_value=mc),
            patch("app.services.ai._log_ai_call", new_callable=am),
        ):
            result = await summarize_news("600519")
            assert "DeepSeek摘要" in result["summary"]
            mc.chat.completions.create.assert_called_once()


class TestProviderFallback:
    """Test fallback behavior when primary provider fails."""

    @pytest.mark.asyncio
    async def test_claude_fails_falls_back_to_deepseek(self):
        """If Claude fails, should fall back to DeepSeek."""
        claude_client = MagicMock()
        claude_client.messages.create = MagicMock(
            side_effect=Exception("Claude error")
        )
        deepseek_client = _mock_deepseek_call("DeepSeek回退结果")
        settings = _make_settings(analysis_provider="claude")

        with _ai_patches(
            mock_openai_client=deepseek_client,
            mock_anthropic_client=claude_client,
            settings=settings,
        ):
            result = await analyze_stock("600519")
            assert "DeepSeek回退结果" in result["analysis"]

    @pytest.mark.asyncio
    async def test_no_primary_key_uses_fallback(self):
        """If primary provider has no key, should try fallback."""
        deepseek_client = _mock_deepseek_call("回退结果")
        settings = _make_settings(
            claude_key="", analysis_provider="claude"
        )

        with _ai_patches(
            mock_openai_client=deepseek_client,
            settings=settings,
        ):
            result = await analyze_stock("600519")
            assert "回退结果" in result["analysis"]

    @pytest.mark.asyncio
    async def test_no_keys_at_all(self):
        """If no provider has keys, should return error."""
        settings = _make_settings(
            deepseek_key="", claude_key="", analysis_provider="claude"
        )
        with _ai_patches(settings=settings):
            result = await analyze_stock("600519")
            # Should get error message (not crash)
            assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_deepseek_fails_falls_back_to_claude(self):
        """If DeepSeek fails for screening, should fall back to Claude."""
        deepseek_client = MagicMock()
        deepseek_client.chat = MagicMock()
        deepseek_client.chat.completions = MagicMock()
        deepseek_client.chat.completions.create = MagicMock(
            side_effect=Exception("DeepSeek error")
        )
        claude_client = _mock_claude_call("Claude回退摘要")
        from app.models.market import NewsItem

        mock_news = [
            NewsItem(title="测试新闻", source="测试", url="u1"),
        ]
        settings = _make_settings(screening_provider="deepseek")
        am = AsyncMock
        with (
            patch("app.services.ai.get_settings", return_value=settings),
            patch(
                f"{_MKT}.get_stock_news",
                new_callable=am,
                return_value=mock_news,
            ),
            patch("openai.OpenAI", return_value=deepseek_client),
            patch("anthropic.Anthropic", return_value=claude_client),
            patch("app.services.ai._log_ai_call", new_callable=am),
        ):
            result = await summarize_news("600519")
            assert "Claude回退摘要" in result["summary"]


class TestClientConstruction:
    """Test that each provider constructs the right client."""

    @pytest.mark.asyncio
    async def test_deepseek_client_construction(self):
        mc = _mock_deepseek_call("test")
        with patch("openai.OpenAI", return_value=mc) as mock_cls:
            await _call_provider("deepseek", "test prompt", "dk-key")
            mock_cls.assert_called_once_with(
                api_key="dk-key",
                base_url="https://api.deepseek.com",
            )

    @pytest.mark.asyncio
    async def test_claude_client_construction(self):
        mc = _mock_claude_call("test")
        with patch("anthropic.Anthropic", return_value=mc) as mock_cls:
            await _call_provider("claude", "test prompt", "ck-key")
            mock_cls.assert_called_once_with(api_key="ck-key")

    @pytest.mark.asyncio
    async def test_openai_client_construction(self):
        mc = _mock_deepseek_call("test")
        with patch("openai.OpenAI", return_value=mc) as mock_cls:
            await _call_provider("openai", "test prompt", "ok-key")
            mock_cls.assert_called_once_with(
                api_key="ok-key",
                base_url="https://api.openai.com/v1",
            )

    @pytest.mark.asyncio
    async def test_qwen_client_construction(self):
        mc = _mock_deepseek_call("test")
        with patch("openai.OpenAI", return_value=mc) as mock_cls:
            await _call_provider("qwen", "test prompt", "qk-key")
            mock_cls.assert_called_once_with(
                api_key="qk-key",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

    @pytest.mark.asyncio
    async def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            await _call_provider("unknown", "test", "key")

    def test_openai_compatible_providers_defined(self):
        assert "deepseek" in OPENAI_COMPATIBLE_PROVIDERS
        assert "openai" in OPENAI_COMPATIBLE_PROVIDERS
        assert "qwen" in OPENAI_COMPATIBLE_PROVIDERS


class TestAnalyzeStock:
    @pytest.mark.asyncio
    async def test_no_api_key(self):
        settings = _make_settings(deepseek_key="", claude_key="")
        with patch("app.services.ai.get_settings", return_value=settings):
            result = await analyze_stock("600519")
            txt = result["analysis"]
            assert "not configured" in txt.lower() or "API" in txt or "配置" in txt
            assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_disclaimer_always_appended(self):
        mc = _mock_claude_call("测试分析结果")
        with _ai_patches(mock_anthropic_client=mc):
            result = await analyze_stock("600519")
            assert AI_DISCLAIMER in result["analysis"]

    @pytest.mark.asyncio
    async def test_response_length_cap(self):
        long_text = "分析" * 500
        mc = _mock_claude_call(long_text)
        with _ai_patches(mock_anthropic_client=mc):
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
        settings = _make_settings(screening_provider="deepseek")
        am = AsyncMock
        with (
            patch(
                f"{_MKT}.get_stock_news",
                new_callable=am,
                return_value=mock_news,
            ),
            patch("app.services.ai.get_settings", return_value=settings),
            patch("openai.OpenAI", return_value=mc),
            patch("app.services.ai._log_ai_call", new_callable=am),
        ):
            result = await summarize_news("600519")
            assert AI_DISCLAIMER in result["summary"]


class TestCallAI:
    """Test _call_ai routing logic."""

    @pytest.mark.asyncio
    async def test_analysis_routes_to_analysis_provider(self):
        mc = _mock_claude_call("分析")
        settings = _make_settings(analysis_provider="claude")
        with (
            patch("app.services.ai.get_settings", return_value=settings),
            patch("anthropic.Anthropic", return_value=mc),
        ):
            result = await _call_ai("test", task_type="analysis")
            assert result == "分析"

    @pytest.mark.asyncio
    async def test_screening_routes_to_screening_provider(self):
        mc = _mock_deepseek_call("筛选")
        settings = _make_settings(screening_provider="deepseek")
        with (
            patch("app.services.ai.get_settings", return_value=settings),
            patch("openai.OpenAI", return_value=mc),
        ):
            result = await _call_ai("test", task_type="screening")
            assert result == "筛选"
