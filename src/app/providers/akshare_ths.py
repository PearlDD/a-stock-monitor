"""AKShare THS data provider with rate limiting and retry."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import akshare as ak  # type: ignore[import-untyped]
import structlog

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider
from app.providers.rate_limiter import RateLimiter

logger = structlog.get_logger()

# HTTP status codes that trigger retry with backoff
_RETRYABLE_CODES = {401, 403, 429, 500, 502, 503, 504}

_MAX_RETRIES = 3
_BASE_BACKOFF = 2.0


class AKShareTHSProvider(DataProvider):
    """Data provider using AKShare's THS (同花顺) interfaces.

    All AKShare calls are synchronous internally and wrapped with
    asyncio.to_thread() to avoid blocking the event loop.
    """

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._limiter = rate_limiter or RateLimiter(min_interval=3.0)

    async def _call_akshare(self, func_name: str, **kwargs: Any) -> Any:
        """Execute an AKShare function with rate limiting and retry.

        Args:
            func_name: Name of the akshare function (e.g. "stock_news_em").
            **kwargs: Arguments forwarded to the akshare function.

        Returns:
            The DataFrame or result from the AKShare call.

        Raises:
            RuntimeError: After exhausting all retries.
        """
        func = getattr(ak, func_name)

        for attempt in range(1, _MAX_RETRIES + 1):
            await self._limiter.acquire()
            try:
                await logger.ainfo(
                    "akshare.request",
                    function=func_name,
                    attempt=attempt,
                    params=kwargs,
                )
                result = await asyncio.to_thread(func, **kwargs)
                await logger.ainfo(
                    "akshare.response",
                    function=func_name,
                    rows=len(result) if hasattr(result, "__len__") else None,
                )
                return result
            except Exception as exc:
                status = _extract_status_code(exc)
                if status in _RETRYABLE_CODES and attempt < _MAX_RETRIES:
                    wait = _BASE_BACKOFF**attempt
                    await logger.awarning(
                        "akshare.retry",
                        function=func_name,
                        attempt=attempt,
                        status=status,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait)
                    continue
                await logger.aerror(
                    "akshare.failed",
                    function=func_name,
                    attempt=attempt,
                    error=str(exc),
                )
                raise RuntimeError(
                    f"AKShare call {func_name} failed after {attempt} attempts: {exc}"
                ) from exc

        msg = f"AKShare call {func_name} failed after {_MAX_RETRIES} attempts"
        raise RuntimeError(msg)  # pragma: no cover

    async def get_quote(self, symbol: str) -> StockQuote:
        df = await self._call_akshare("stock_zh_a_spot")
        row = df[df["代码"] == symbol]
        if row.empty:
            raise ValueError(f"Symbol {symbol} not found in spot data")
        r = row.iloc[0]
        return StockQuote(
            symbol=symbol,
            name=str(r.get("名称", "")),
            price=float(r.get("最新价", 0)),
            change_pct=float(r.get("涨跌幅", 0)),
            volume=float(r.get("成交量", 0)),
            timestamp=datetime.now(tz=UTC),
        )

    async def get_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        df = await self._call_akshare("stock_news_em", stock=symbol)
        items: list[NewsItem] = []
        for _, row in df.head(limit).iterrows():
            items.append(
                NewsItem(
                    symbol=symbol,
                    title=str(row.get("新闻标题", "")),
                    url=str(row.get("新闻链接", "")),
                    source=str(row.get("文章来源", "")),
                    published_at=_parse_datetime(row.get("发布时间")),
                )
            )
        return items

    async def get_financials(self, symbol: str) -> FinancialSummary:
        df = await self._call_akshare(
            "stock_financial_abstract_ths",
            symbol=symbol,
            indicator="按报告期",
        )
        if df.empty:
            return FinancialSummary(symbol=symbol, name="")
        r = df.iloc[0]
        return FinancialSummary(
            symbol=symbol,
            name="",
            pe_ratio=_safe_float(r.get("市盈率")),
            revenue=_safe_float(r.get("营业总收入")),
            net_profit=_safe_float(r.get("净利润")),
            gross_margin=_safe_float(r.get("毛利率")),
            net_margin=_safe_float(r.get("净利率")),
            report_date=str(r.get("报告期", "")) or None,
        )

    async def search_stocks(self, keyword: str) -> list[StockInfo]:
        df = await self._call_akshare("stock_info_a_code_name")
        matches = df[
            df["name"].str.contains(keyword, na=False)
            | df["code"].str.contains(keyword, na=False)
        ]
        return [
            StockInfo(
                symbol=str(row["code"]),
                name=str(row["name"]),
            )
            for _, row in matches.head(20).iterrows()
        ]


def _extract_status_code(exc: Exception) -> int | None:
    """Try to extract an HTTP status code from an exception."""
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        return int(exc.response.status_code)
    msg = str(exc)
    for code in _RETRYABLE_CODES:
        if str(code) in msg:
            return code
    return None


def _parse_datetime(value: object) -> datetime:
    """Parse a datetime value, falling back to now on failure."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return datetime.now(tz=UTC)


def _safe_float(value: Any) -> float | None:
    """Convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
