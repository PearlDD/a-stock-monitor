"""AI-powered stock screening service.

User inputs Chinese criteria, DeepSeek parses to structured filters,
applied against market data. Includes predefined quick-filters.
Rate limited: max 10 screening queries per hour.
"""

from __future__ import annotations

import json
import time

from app.config import get_settings
from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("screener")

SCREEN_RATE_LIMIT = 10  # max queries per hour
RATE_WINDOW = 3600  # 1 hour in seconds

# Predefined quick-filters with structured criteria
PREDEFINED_FILTERS: dict[str, dict] = {
    "低估值蓝筹": {
        "description": "低市盈率、低市净率的大盘蓝筹股",
        "filters": {
            "pe_max": 15,
            "pb_max": 2,
            "min_market_cap": 500,  # 亿
        },
    },
    "近期强势": {
        "description": "近期涨幅较大的强势股",
        "filters": {
            "change_pct_min": 3,
        },
    },
    "高股息": {
        "description": "股息率较高的价值股",
        "filters": {
            "pe_max": 20,
            "pb_max": 3,
        },
    },
}


async def _check_rate_limit() -> bool:
    """Check if screening rate limit is exceeded. Returns True if allowed."""
    cache = get_cache()
    key = "screen_rate_limit"
    timestamps = await cache.get(key) or []
    now = time.monotonic()
    # Keep only requests within the window
    recent = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(recent) >= SCREEN_RATE_LIMIT:
        log.warning("screen_rate_limited", count=len(recent))
        return False
    recent.append(now)
    await cache.set(key, recent, RATE_WINDOW)
    return True


def _apply_filters(stocks: list[dict], filters: dict) -> list[dict]:
    """Apply structured filters to stock list."""
    result = []
    for s in stocks:
        if "pe_max" in filters and s.get("pe_ratio", 999) > filters["pe_max"]:
            continue
        if "pe_min" in filters and s.get("pe_ratio", 0) < filters["pe_min"]:
            continue
        if "pb_max" in filters and s.get("pb_ratio", 999) > filters["pb_max"]:
            continue
        if "pb_min" in filters and s.get("pb_ratio", 0) < filters["pb_min"]:
            continue
        if "change_pct_min" in filters:
            if s.get("change_pct", 0) < filters["change_pct_min"]:
                continue
        if "change_pct_max" in filters:
            if s.get("change_pct", 0) > filters["change_pct_max"]:
                continue
        if "min_market_cap" in filters:
            cap = s.get("market_cap", 0)
            if cap < filters["min_market_cap"] * 1e8:
                continue
        if "price_max" in filters and s.get("price", 999999) > filters["price_max"]:
            continue
        if "price_min" in filters and s.get("price", 0) < filters["price_min"]:
            continue
        result.append(s)
    return result


async def _parse_criteria_with_ai(query: str) -> dict:
    """Use DeepSeek to parse natural language criteria to structured filters."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not configured")

    import asyncio

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
    )

    prompt = (
        "将以下中文选股条件转换为JSON过滤器。"
        "可用字段: pe_max, pe_min, pb_max, pb_min, "
        "change_pct_min, change_pct_max, price_max, price_min, "
        "min_market_cap(亿元)。"
        "只返回JSON，不要其他文字。\n\n"
        f"条件: {query}"
    )

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )

    text = response.choices[0].message.content or "{}"
    # Extract JSON from response
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    try:
        filters = json.loads(text)
        if not isinstance(filters, dict):
            filters = {}
    except json.JSONDecodeError:
        log.warning("ai_filter_parse_failed", raw=text[:200])
        filters = {}

    return filters


async def _get_market_snapshot() -> list[dict]:
    """Get current market data as list of dicts for filtering."""

    cache = get_cache()
    cached = await cache.get("quotes:all")
    if cached:
        return [
            {
                "code": q.code,
                "name": q.name,
                "price": q.price,
                "change_pct": q.change_pct,
                "volume": q.volume,
                "amount": q.amount,
                "pe_ratio": 0,
                "pb_ratio": 0,
                "market_cap": 0,
            }
            for q in cached
        ]
    return []


async def screen_stocks(
    query: str | None = None, preset: str | None = None
) -> dict:
    """Screen stocks by AI-parsed criteria or predefined filter.

    Returns dict with 'stocks' list and 'filter_used'.
    """
    if not await _check_rate_limit():
        return {
            "stocks": [],
            "filter_used": {},
            "error": "筛选请求过于频繁，每小时最多10次，请稍后再试。",
        }

    if preset and preset in PREDEFINED_FILTERS:
        filters = PREDEFINED_FILTERS[preset]["filters"]
        log.info("screen_preset", preset=preset)
    elif query:
        try:
            filters = await _parse_criteria_with_ai(query)
        except ValueError as e:
            return {"stocks": [], "filter_used": {}, "error": str(e)}
        except Exception:
            log.error("screen_ai_parse_failed", exc_info=True)
            return {
                "stocks": [],
                "filter_used": {},
                "error": "AI解析条件失败，请重新描述或使用预设筛选。",
            }
        log.info("screen_ai", query=query, filters=filters)
    else:
        return {"stocks": [], "filter_used": {}, "error": "请输入筛选条件或选择预设。"}

    market_data = await _get_market_snapshot()
    if not market_data:
        return {
            "stocks": [],
            "filter_used": filters,
            "error": "暂无行情数据，请稍后重试。",
        }

    results = _apply_filters(market_data, filters)
    # Limit results and sort by change_pct descending
    results.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
    results = results[:50]

    log.info("screen_complete", total_stocks=len(market_data), matched=len(results))
    return {"stocks": results, "filter_used": filters}
