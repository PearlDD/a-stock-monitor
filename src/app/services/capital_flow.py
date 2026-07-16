"""Large capital flow monitoring service (大资金监控).

Monitors all stocks for unusual large capital inflow using AKShare.
Threshold: net inflow > top 1% of all stocks, OR net inflow > 5000万.
Dedup: only alert once per stock per day (daily reset at 09:30).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.database import get_db
from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("capital_flow")

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
LARGE_INFLOW_THRESHOLD = 5000_0000  # 5000万 in yuan
TOP_PERCENTILE = 0.01  # top 1%

CAPITAL_FLOW_CACHE_KEY = "capital_flow:top"
CAPITAL_FLOW_CACHE_TTL = 300  # 5 minutes


async def fetch_capital_flow_rank() -> list[dict[str, Any]]:
    """Fetch today's capital flow ranking from AKShare."""
    try:
        import akshare as ak

        df = await asyncio.to_thread(
            ak.stock_individual_fund_flow_rank, indicator="今日"
        )
        if df is None or df.empty:
            return []

        results: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            net_inflow = float(row.get("今日主力净流入-净额", 0) or 0)
            results.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "net_inflow": net_inflow,
                "change_pct": float(row.get("今日涨跌幅", row.get("涨跌幅", 0)) or 0),
            })

        log.info("capital_flow_rank_fetched", count=len(results))
        return results
    except Exception:
        log.error("capital_flow_rank_fetch_failed", exc_info=True)
        return []


def identify_large_inflows(
    stocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identify stocks with unusually large capital inflow.

    Threshold: net inflow > top 1% of all stocks, OR net inflow > 5000万.
    """
    if not stocks:
        return []

    # Filter only positive inflows
    positive = [s for s in stocks if s["net_inflow"] > 0]
    if not positive:
        return []

    # Sort by net inflow descending
    positive.sort(key=lambda x: x["net_inflow"], reverse=True)

    # Calculate top 1% threshold
    top_idx = max(1, int(len(positive) * TOP_PERCENTILE))
    if top_idx <= len(positive):
        percentile_threshold = positive[top_idx - 1]["net_inflow"]
    else:
        percentile_threshold = 0

    # Apply dual threshold
    threshold = min(percentile_threshold, LARGE_INFLOW_THRESHOLD)

    large = [s for s in positive if s["net_inflow"] >= threshold]
    return large


async def check_and_alert_capital_flow() -> list[dict[str, Any]]:
    """Check for large capital inflows and send alerts.

    Returns list of newly alerted stocks.
    """
    from app.services.push import PushPlusClient
    from app.services.trading_calendar import should_poll

    if not await should_poll():
        return []

    stocks = await fetch_capital_flow_rank()
    if not stocks:
        return []

    large = identify_large_inflows(stocks)
    if not large:
        return []

    # Cache top list for API
    cache = get_cache()
    await cache.set(CAPITAL_FLOW_CACHE_KEY, large[:50], CAPITAL_FLOW_CACHE_TTL)

    # Store snapshots
    await _store_snapshots(large[:50])

    # Dedup: only alert once per stock per day
    today = datetime.now(tz=SHANGHAI_TZ).strftime("%Y-%m-%d")
    new_alerts: list[dict[str, Any]] = []

    async with get_db() as db:
        for stock in large[:20]:  # limit to top 20
            cursor = await db.execute(
                "SELECT 1 FROM capital_flow_alerts_seen"
                " WHERE stock_code = ? AND alert_date = ?",
                (stock["code"], today),
            )
            if await cursor.fetchone():
                continue

            await db.execute(
                "INSERT OR IGNORE INTO capital_flow_alerts_seen"
                " (stock_code, alert_date) VALUES (?, ?)",
                (stock["code"], today),
            )
            new_alerts.append(stock)

        await db.commit()

    if not new_alerts:
        return []

    # Send push alerts
    from app.config import get_settings

    settings = get_settings()
    if not settings.pushplus_token:
        return new_alerts

    client = PushPlusClient(settings.pushplus_token)
    now_str = datetime.now(tz=SHANGHAI_TZ).strftime("%H:%M")

    # Batch alerts into single message
    lines = ["💰 大资金流入提醒\n"]
    for s in new_alerts[:10]:
        amount_yi = s["net_inflow"] / 1e8
        lines.append(
            f"{s['name']}({s['code']})\n"
            f"净流入: {amount_yi:.2f}亿"
        )
    lines.append(f"\n⏰ {now_str}")
    lines.append("以上仅供参考，不构成投资建议")

    await client.send_alert("💰 大资金流入提醒", "\n".join(lines))
    log.info("capital_flow_alerts_sent", count=len(new_alerts))

    return new_alerts


async def get_top_capital_flow() -> dict[str, Any]:
    """Get today's top capital inflow stocks (for API endpoint)."""
    cache = get_cache()
    cached = await cache.get(CAPITAL_FLOW_CACHE_KEY)
    if cached is not None:
        return {"stocks": cached, "cached": True}

    stocks = await fetch_capital_flow_rank()
    if not stocks:
        return {"stocks": [], "cached": False}

    large = identify_large_inflows(stocks)
    top = large[:50] if large else stocks[:20]
    await cache.set(CAPITAL_FLOW_CACHE_KEY, top, CAPITAL_FLOW_CACHE_TTL)
    return {"stocks": top, "cached": False}


async def _store_snapshots(stocks: list[dict[str, Any]]) -> None:
    """Store capital flow snapshots in DB for trend analysis."""
    try:
        async with get_db() as db:
            for s in stocks[:50]:
                await db.execute(
                    "INSERT INTO capital_flow_snapshots"
                    " (stock_code, stock_name, net_inflow, change_pct)"
                    " VALUES (?, ?, ?, ?)",
                    (s["code"], s["name"], s["net_inflow"], s["change_pct"]),
                )
            await db.commit()
        log.info("capital_flow_snapshots_stored", count=len(stocks))
    except Exception:
        log.error("capital_flow_snapshots_store_failed", exc_info=True)
