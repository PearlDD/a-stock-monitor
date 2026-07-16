"""Multi-provider AI integration for stock analysis.

Supports DeepSeek, Claude (Anthropic), OpenAI, and Qwen providers.
Routes different tasks to different providers for cost/quality optimization.
All AI outputs include mandatory disclaimer.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import Settings, get_settings
from app.database import get_db
from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("ai")

AI_DISCLAIMER = "以上由AI生成，仅供参考，不构成投资建议。"
MAX_RESPONSE_CHARS = 500
CACHE_TTL = 1800  # 30 minutes

# Provider configurations: (base_url, default_model)
OPENAI_COMPATIBLE_PROVIDERS: dict[str, tuple[str, str]] = {
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "openai": ("https://api.openai.com/v1", "gpt-4.1"),
    "qwen": (
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
}


def _get_provider_api_key(provider: str, settings: Settings) -> str:
    """Get the API key for a provider from settings."""
    if provider == "deepseek":
        return settings.deepseek_api_key
    if provider == "claude":
        return settings.effective_claude_api_key
    if provider == "openai":
        return settings.deepseek_api_key  # reuse deepseek key field for now
    if provider == "qwen":
        return settings.deepseek_api_key  # reuse deepseek key field for now
    return ""


def _get_fallback_provider(primary: str) -> str | None:
    """Get fallback provider for the given primary."""
    if primary == "claude":
        return "deepseek"
    if primary == "deepseek":
        return "claude"
    # For openai/qwen, fall back to deepseek
    return "deepseek"


async def _call_claude(
    prompt: str, api_key: str, max_chars: int = MAX_RESPONSE_CHARS
) -> str:
    """Call Claude API via anthropic SDK."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text if response.content else ""
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


async def _call_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    max_chars: int = MAX_RESPONSE_CHARS,
) -> str:
    """Call an OpenAI-compatible API (DeepSeek, OpenAI, Qwen)."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )

    text = response.choices[0].message.content or ""
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


async def _call_provider(
    provider: str, prompt: str, api_key: str, max_chars: int = MAX_RESPONSE_CHARS
) -> str:
    """Call the specified AI provider."""
    if provider == "claude":
        return await _call_claude(prompt, api_key, max_chars)

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        base_url, model = OPENAI_COMPATIBLE_PROVIDERS[provider]
        return await _call_openai_compatible(
            prompt, api_key, base_url, model, max_chars
        )

    raise ValueError(f"Unknown AI provider: {provider}")


async def _call_ai(
    prompt: str,
    task_type: str,
    max_chars: int = MAX_RESPONSE_CHARS,
) -> str:
    """Call AI with provider routing and fallback.

    Args:
        prompt: The prompt to send.
        task_type: Either 'analysis' or 'screening' to determine provider.
        max_chars: Maximum response characters.
    """
    settings = get_settings()

    if task_type == "analysis":
        primary = settings.ai_provider_analysis
    else:
        primary = settings.ai_provider_screening

    primary_key = _get_provider_api_key(primary, settings)
    if not primary_key:
        # Try fallback immediately if primary has no key
        fallback = _get_fallback_provider(primary)
        if fallback:
            fallback_key = _get_provider_api_key(fallback, settings)
            if fallback_key:
                log.info(
                    "ai_primary_no_key_fallback",
                    primary=primary,
                    fallback=fallback,
                )
                return await _call_provider(fallback, prompt, fallback_key, max_chars)
        raise ValueError(f"No API key configured for {primary} (or fallback)")

    try:
        return await _call_provider(primary, prompt, primary_key, max_chars)
    except Exception:
        log.warning("ai_primary_failed", provider=primary, exc_info=True)
        fallback = _get_fallback_provider(primary)
        if fallback:
            fallback_key = _get_provider_api_key(fallback, settings)
            if fallback_key:
                log.info("ai_fallback_attempt", fallback=fallback)
                return await _call_provider(
                    fallback, prompt, fallback_key, max_chars
                )
        raise


async def _log_ai_call(
    stock_code: str, request_type: str, prompt: str, response: str
) -> None:
    """Log AI call to database."""
    try:
        async with get_db() as db:
            await db.execute(
                "INSERT INTO ai_log (stock_code, request_type, prompt, response)"
                " VALUES (?, ?, ?, ?)",
                (stock_code, request_type, prompt[:500], response[:1000]),
            )
            await db.commit()
    except Exception:
        log.warning("ai_log_failed", stock_code=stock_code, exc_info=True)


async def analyze_stock(code: str) -> dict[str, Any]:
    """Analyze a stock using AI (provider from AI_PROVIDER_ANALYSIS).

    Gathers quotes + financials + news, sends to AI for analysis.
    Returns dict with 'analysis' text and 'cached' flag.
    In demo mode, returns a pre-built analysis.
    """
    settings = get_settings()
    if settings.data_mode == "mock":
        demo_text = (
            "近期走势：该股近5日震荡整理，成交量温和。\n"
            "基本面：公司营收稳健，市盈率处于行业中等水平。\n"
            "风险提示：注意大盘系统性风险。\n\n"
            f"{AI_DISCLAIMER}"
        )
        return {"analysis": demo_text, "cached": False}

    cache = get_cache()
    cache_key = f"ai_analysis:{code}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return {"analysis": cached, "cached": True}

    # Gather context data
    from app.services.market_data import (
        get_financial_summary,
        get_realtime_quotes,
        get_stock_news,
    )

    context_parts: list[str] = []

    quotes = await get_realtime_quotes([code])
    if quotes:
        q = quotes[0]
        context_parts.append(
            f"股票: {q.name}({q.code}), 当前价: ¥{q.price:.2f}, "
            f"涨跌幅: {q.change_pct:+.2f}%, "
            f"成交量: {q.volume:.0f}, 今开: ¥{q.open:.2f}, "
            f"最高: ¥{q.high:.2f}, 最低: ¥{q.low:.2f}"
        )

    financials = await get_financial_summary(code)
    if financials:
        context_parts.append(
            f"财务摘要: 市盈率={financials.pe_ratio:.1f}, "
            f"市净率={financials.pb_ratio:.1f}, "
            f"营收={financials.revenue:.0f}万, "
            f"净利润={financials.net_profit:.0f}万"
        )

    news = await get_stock_news(code, limit=5)
    if news:
        headlines = [n.title for n in news]
        context_parts.append("近期资讯: " + "; ".join(headlines))

    context = "\n".join(context_parts) if context_parts else f"股票代码: {code}"

    prompt = (
        f"请分析以下A股股票，用中文输出3-5个要点，"
        f"包括: 近期走势、基本面、风险提示、资讯摘要。\n\n{context}"
    )

    try:
        analysis = await _call_ai(prompt, task_type="analysis")
    except ValueError as e:
        return {"analysis": str(e), "cached": False}
    except Exception:
        log.error("ai_analyze_failed", code=code, exc_info=True)
        return {"analysis": "AI分析暂时不可用，请稍后重试。", "cached": False}

    # Always append disclaimer
    full_analysis = f"{analysis}\n\n{AI_DISCLAIMER}"
    await cache.set(cache_key, full_analysis, CACHE_TTL)
    await _log_ai_call(code, "analyze", prompt, full_analysis)

    log.info("ai_analysis_complete", code=code, chars=len(full_analysis))
    return {"analysis": full_analysis, "cached": False}


async def summarize_news(code: str) -> dict[str, Any]:
    """Summarize recent news using AI (screening provider)."""
    cache = get_cache()
    cache_key = f"ai_news_summary:{code}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return {"summary": cached, "cached": True}

    from app.services.market_data import get_stock_news

    news = await get_stock_news(code, limit=15)
    if not news:
        return {"summary": "暂无相关资讯可供总结。", "cached": False}

    headlines = "\n".join(f"- {n.title}" for n in news)
    prompt = (
        f"请将以下股票资讯标题浓缩为3句中文摘要，突出重点信息:\n\n{headlines}"
    )

    try:
        summary = await _call_ai(prompt, task_type="screening")
    except ValueError as e:
        return {"summary": str(e), "cached": False}
    except Exception:
        log.error("ai_summarize_failed", code=code, exc_info=True)
        return {"summary": "AI总结暂时不可用，请稍后重试。", "cached": False}

    full_summary = f"{summary}\n\n{AI_DISCLAIMER}"
    await cache.set(cache_key, full_summary, CACHE_TTL)
    await _log_ai_call(code, "summarize", prompt, full_summary)

    log.info("ai_summarize_complete", code=code, chars=len(full_summary))
    return {"summary": full_summary, "cached": False}
