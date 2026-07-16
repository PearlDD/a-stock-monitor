"""Trading calendar and hours check for A-share market.

All times use Asia/Shanghai timezone. Trading sessions:
  Morning:   09:30 - 11:30
  Afternoon: 13:00 - 15:00
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.logging import get_logger
from app.services.cache import CALENDAR_TTL, get_cache

log = get_logger("trading_calendar")

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

MORNING_OPEN = time(9, 30)
MORNING_CLOSE = time(11, 30)
AFTERNOON_OPEN = time(13, 0)
AFTERNOON_CLOSE = time(15, 0)

# Cache key for trade dates set
_TRADE_DATES_KEY = "trade_dates"


async def load_trade_dates() -> set[str]:
    """Load trading dates from AKShare, with cache."""
    cache = get_cache()
    cached = await cache.get(_TRADE_DATES_KEY)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    try:
        import akshare as ak

        df = await asyncio.to_thread(ak.tool_trade_date_hist_sina)
        dates = {str(d) for d in df["trade_date"].tolist()}
        await cache.set(_TRADE_DATES_KEY, dates, CALENDAR_TTL)
        log.info("trade_dates_loaded", count=len(dates))
        return dates
    except Exception:
        log.warning("trade_dates_load_failed", exc_info=True)
        return set()


def _now_shanghai() -> datetime:
    return datetime.now(tz=SHANGHAI_TZ)


async def is_trade_date(d: date | None = None) -> bool:
    """Check if a date is a trading day."""
    if d is None:
        d = _now_shanghai().date()
    # Weekends are never trading days
    if d.weekday() >= 5:
        return False
    dates = await load_trade_dates()
    if not dates:
        # Fallback: assume weekdays are trading days if calendar unavailable
        return True
    return d.isoformat() in dates


def is_trading_hours(now: datetime | None = None) -> bool:
    """Check if current time is within A-share trading hours.

    Morning session:   09:30 - 11:30 CST
    Afternoon session: 13:00 - 15:00 CST
    """
    if now is None:
        now = _now_shanghai()
    else:
        now = now.astimezone(SHANGHAI_TZ)
    t = now.time()
    return (MORNING_OPEN <= t <= MORNING_CLOSE) or (
        AFTERNOON_OPEN <= t <= AFTERNOON_CLOSE
    )


async def get_market_status(now: datetime | None = None) -> str:
    """Return 'trading' if market is open, 'closed' otherwise."""
    if now is None:
        now = _now_shanghai()
    if is_trading_hours(now) and await is_trade_date(now.date()):
        return "trading"
    return "closed"


async def should_poll(now: datetime | None = None) -> bool:
    """Check if we should poll market data right now (trading day + trading hours)."""
    if now is None:
        now = _now_shanghai()
    if not is_trading_hours(now):
        return False
    return await is_trade_date(now.date())
