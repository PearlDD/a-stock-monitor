"""DeepSeek AI integration for stock analysis.

Uses OpenAI-compatible SDK with base_url='https://api.deepseek.com'.
All AI outputs include mandatory disclaimer.
"""

from __future__ import annotations

from app.config import get_settings
from app.database import get_db
from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("ai")

AI_DISCLAIMER = "以上由AI生成，仅供参考，不构成投资建议。"
MAX_RESPONSE_CHARS = 500
CACHE_TTL = 1800  # 30 minutes


async def _call_deepseek(prompt: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """Call DeepSeek API via OpenAI SDK."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not configured")

    import asyncio

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
    )

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )

    text = response.choices[0].message.content or ""
    # Cap response length
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


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


async def analyze_stock(code: str) -> dict:
    """Analyze a stock using DeepSeek AI.

    Gathers quotes + financials + news, sends to DeepSeek for analysis.
    Returns dict with 'analysis' text and 'cached' flag.
    """
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

    context_parts = []

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
        analysis = await _call_deepseek(prompt)
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


async def summarize_news(code: str) -> dict:
    """Summarize recent news for a stock using DeepSeek AI."""
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
        summary = await _call_deepseek(prompt)
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
