"""AKShare market data service with circuit breaker and retry.

Wraps AKShare (synchronous) calls via asyncio.to_thread().
Implements:
  - Exponential backoff retry (3 attempts, 2/4/8s)
  - Circuit breaker (3 failures → 10-min cooldown, serve cached data)
  - All results cached via TTLCache
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.logging import get_logger
from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.services.cache import (
    FINANCIALS_TTL,
    NEWS_TTL,
    QUOTE_TTL,
    get_cache,
)

log = get_logger("market_data")

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

# Circuit breaker settings
_CB_FAILURE_THRESHOLD = 3
_CB_COOLDOWN_SECONDS = 600  # 10 minutes

# Retry settings
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds


class CircuitBreaker:
    """Simple circuit breaker: opens after consecutive failures, auto-resets."""

    def __init__(
        self,
        threshold: int = _CB_FAILURE_THRESHOLD,
        cooldown: float = _CB_COOLDOWN_SECONDS,
    ) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at > self.cooldown:
            self.reset()
            return False
        return True

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()
            log.warning(
                "circuit_breaker_opened",
                failures=self._failures,
                cooldown_s=self.cooldown,
            )

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def reset(self) -> None:
        self._failures = 0
        self._opened_at = None
        log.info("circuit_breaker_reset")


# Module-level circuit breaker
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker


async def _retry_akshare(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Call an AKShare function with retry and exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            result = await asyncio.to_thread(func, *args, **kwargs)
            _circuit_breaker.record_success()
            return result
        except Exception as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2**attempt)
            log.warning(
                "akshare_retry",
                attempt=attempt + 1,
                delay_s=delay,
                error=str(exc),
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(delay)
    _circuit_breaker.record_failure()
    raise last_exc  # type: ignore[misc]


async def get_realtime_quotes(codes: list[str]) -> list[StockQuote]:
    """Fetch real-time quotes for given stock codes.

    Uses ak.stock_zh_a_spot_em() and filters to watchlist codes.
    """
    cache = get_cache()
    cache_key = "quotes:all"

    if _circuit_breaker.is_open:
        log.info("circuit_breaker_open_serving_cache", func="quotes")
        cached = await cache.get(cache_key)
        return _filter_quotes(cached, codes) if cached else []

    cached = await cache.get(cache_key)
    if cached is not None:
        return _filter_quotes(cached, codes)

    try:
        import akshare as ak

        df = await _retry_akshare(ak.stock_zh_a_spot_em)
        now = datetime.now(tz=SHANGHAI_TZ)
        all_quotes: list[StockQuote] = []
        for _, row in df.iterrows():
            try:
                all_quotes.append(
                    StockQuote(
                        code=str(row.get("代码", "")),
                        name=str(row.get("名称", "")),
                        price=float(row.get("最新价", 0) or 0),
                        change_pct=float(row.get("涨跌幅", 0) or 0),
                        volume=float(row.get("成交量", 0) or 0),
                        amount=float(row.get("成交额", 0) or 0),
                        high=float(row.get("最高", 0) or 0),
                        low=float(row.get("最低", 0) or 0),
                        open=float(row.get("今开", 0) or 0),
                        prev_close=float(row.get("昨收", 0) or 0),
                        timestamp=now,
                    )
                )
            except (ValueError, TypeError):
                continue

        await cache.set(cache_key, all_quotes, QUOTE_TTL)
        log.info("quotes_fetched", total=len(all_quotes))
        return _filter_quotes(all_quotes, codes)
    except Exception:
        log.error("quotes_fetch_failed", exc_info=True)
        cached = await cache.get(cache_key)
        return _filter_quotes(cached, codes) if cached else []


def _filter_quotes(
    quotes: list[StockQuote] | None, codes: list[str]
) -> list[StockQuote]:
    if not quotes:
        return []
    code_set = set(codes)
    return [q for q in quotes if q.code in code_set]


async def get_stock_info(code: str) -> StockInfo | None:
    """Fetch basic info for a stock."""
    cache = get_cache()
    cache_key = f"info:{code}"

    if _circuit_breaker.is_open:
        return await cache.get(cache_key)  # type: ignore[no-any-return]

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    try:
        import akshare as ak

        df = await _retry_akshare(ak.stock_zh_a_spot_em)
        row = df[df["代码"] == code]
        if row.empty:
            return None
        r = row.iloc[0]
        info = StockInfo(
            code=code,
            name=str(r.get("名称", "")),
            sector="",
            market="",
            list_date="",
        )
        await cache.set(cache_key, info, FINANCIALS_TTL)
        log.info("stock_info_fetched", code=code)
        return info
    except Exception:
        log.error("stock_info_failed", code=code, exc_info=True)
        return await cache.get(cache_key)  # type: ignore[return-value]


async def get_stock_news(code: str, limit: int = 10) -> list[NewsItem]:
    """Fetch recent news for a stock via ak.stock_news_em()."""
    cache = get_cache()
    cache_key = f"news:{code}"

    if _circuit_breaker.is_open:
        cached = await cache.get(cache_key)
        return (cached or [])[:limit]  # type: ignore[no-any-return]

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached[:limit]  # type: ignore[no-any-return]

    try:
        import akshare as ak

        df = await _retry_akshare(ak.stock_news_em, symbol=code)
        items: list[NewsItem] = []
        for _, row in df.head(50).iterrows():
            pub_time = None
            raw_time = row.get("发布时间", "")
            if raw_time:
                try:
                    pub_time = datetime.strptime(
                        str(raw_time), "%Y-%m-%d %H:%M:%S"
                    ).replace(tzinfo=SHANGHAI_TZ)
                except ValueError:
                    pass
            items.append(
                NewsItem(
                    title=str(row.get("新闻标题", "")),
                    source=str(row.get("新闻来源", "")),
                    url=str(row.get("新闻链接", "")),
                    publish_time=pub_time,
                    stock_code=code,
                )
            )
        await cache.set(cache_key, items, NEWS_TTL)
        log.info("news_fetched", code=code, count=len(items))
        return items[:limit]
    except Exception:
        log.error("news_fetch_failed", code=code, exc_info=True)
        cached = await cache.get(cache_key)
        return (cached or [])[:limit]


async def get_price_history(code: str, days: int = 5) -> list[dict]:
    """Fetch recent daily price history via ak.stock_zh_a_hist()."""
    cache = get_cache()
    cache_key = f"history:{code}:{days}"

    if _circuit_breaker.is_open:
        cached = await cache.get(cache_key)
        return cached or []

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        import akshare as ak

        df = await _retry_akshare(
            ak.stock_zh_a_hist,
            symbol=code,
            period="daily",
            adjust="qfq",
        )
        if df is None or df.empty:
            return []
        rows = df.tail(days)
        history = []
        for _, row in rows.iterrows():
            history.append(
                {
                    "date": str(row.get("日期", "")),
                    "open": float(row.get("开盘", 0) or 0),
                    "close": float(row.get("收盘", 0) or 0),
                    "high": float(row.get("最高", 0) or 0),
                    "low": float(row.get("最低", 0) or 0),
                    "volume": float(row.get("成交量", 0) or 0),
                }
            )
        await cache.set(cache_key, history, QUOTE_TTL * 10)
        log.info("price_history_fetched", code=code, days=len(history))
        return history
    except Exception:
        log.error("price_history_failed", code=code, exc_info=True)
        return []


async def get_announcements(code: str, limit: int = 10) -> list[dict]:
    """Fetch company announcements via ak.stock_notice_report()."""
    cache = get_cache()
    cache_key = f"announcements:{code}"

    if _circuit_breaker.is_open:
        cached = await cache.get(cache_key)
        return (cached or [])[:limit]

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached[:limit]  # type: ignore[return-value]

    try:
        import akshare as ak

        df = await _retry_akshare(ak.stock_notice_report, symbol=code)
        if df is None or df.empty:
            return []
        items = []
        for _, row in df.head(50).iterrows():
            items.append(
                {
                    "title": str(row.get("公告标题", row.get("标题", ""))),
                    "date": str(row.get("公告日期", row.get("日期", ""))),
                    "url": str(row.get("公告链接", row.get("链接", ""))),
                }
            )
        await cache.set(cache_key, items, NEWS_TTL)
        log.info("announcements_fetched", code=code, count=len(items))
        return items[:limit]
    except Exception:
        log.error("announcements_failed", code=code, exc_info=True)
        return []


async def get_financial_summary(code: str) -> FinancialSummary | None:
    """Fetch key financials via ak.stock_financial_abstract_ths()."""
    cache = get_cache()
    cache_key = f"financials:{code}"

    if _circuit_breaker.is_open:
        return await cache.get(cache_key)  # type: ignore[no-any-return]

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    try:
        import akshare as ak

        df = await _retry_akshare(ak.stock_financial_abstract_ths, symbol=code)
        if df.empty:
            return None
        row = df.iloc[0]
        summary = FinancialSummary(
            code=code,
            name=str(row.get("股票简称", "")),
            pe_ratio=float(row.get("市盈率", 0) or 0),
            pb_ratio=float(row.get("市净率", 0) or 0),
            revenue=float(row.get("营业总收入", 0) or 0),
            net_profit=float(row.get("净利润", 0) or 0),
        )
        await cache.set(cache_key, summary, FINANCIALS_TTL)
        log.info("financials_fetched", code=code)
        return summary
    except Exception:
        log.error("financials_fetch_failed", code=code, exc_info=True)
        return await cache.get(cache_key)
