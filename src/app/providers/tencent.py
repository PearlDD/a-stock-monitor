"""Tencent Finance (腾讯财经) data provider for real-time A-share quotes.

Uses http://qt.gtimg.cn/q= API which works reliably from US servers.
For non-quote data (news, financials, stock info), falls back to AKShare.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.logging import get_logger
from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider

log = get_logger("tencent_provider")

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
TENCENT_QT_URL = "http://qt.gtimg.cn/q="


def _market_prefix(code: str) -> str:
    """Return 'sh' or 'sz' prefix based on stock code."""
    if code.startswith("6"):
        return "sh"
    return "sz"


def _parse_tencent_response(text: str) -> list[StockQuote]:
    """Parse Tencent Finance GBK response into StockQuote objects.

    Each stock line looks like: v_sh600519="1~贵州茅台~600519~1800.00~...~";
    Fields are separated by '~'.
    """
    quotes: list[StockQuote] = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or '="' not in line:
            continue

        # Extract the data between quotes
        try:
            data_part = line.split('="', 1)[1].rstrip('";')
        except IndexError:
            continue

        if not data_part:
            continue

        fields = data_part.split("~")
        if len(fields) < 38:
            log.warning("tencent_parse_short_line", field_count=len(fields))
            continue

        try:
            code = fields[2]
            name = fields[1]
            price = float(fields[3]) if fields[3] else 0.0
            prev_close = float(fields[4]) if fields[4] else 0.0
            open_price = float(fields[5]) if fields[5] else 0.0
            volume = float(fields[6]) if fields[6] else 0.0
            high = float(fields[33]) if fields[33] else 0.0
            low = float(fields[34]) if fields[34] else 0.0
            amount = float(fields[37]) if fields[37] else 0.0

            # change_pct is field [32]
            change_pct_str = fields[32].replace("%", "")
            change_pct = float(change_pct_str) if change_pct_str else 0.0

            # Timestamp from field [30], e.g. "2026-07-18 15:00:03"
            timestamp = None
            if fields[30]:
                try:
                    timestamp = datetime.strptime(
                        fields[30], "%Y%m%d%H%M%S"
                    ).replace(tzinfo=SHANGHAI_TZ)
                except ValueError:
                    try:
                        timestamp = datetime.strptime(
                            fields[30], "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=SHANGHAI_TZ)
                    except ValueError:
                        timestamp = datetime.now(tz=SHANGHAI_TZ)

            if price <= 0:
                continue

            quotes.append(
                StockQuote(
                    code=code,
                    name=name,
                    price=price,
                    change_pct=change_pct,
                    volume=volume,
                    amount=amount,
                    high=high,
                    low=low,
                    open=open_price,
                    prev_close=prev_close,
                    timestamp=timestamp or datetime.now(tz=SHANGHAI_TZ),
                )
            )
        except (ValueError, IndexError):
            log.warning("tencent_parse_error", line=line[:80], exc_info=True)
            continue

    return quotes


class TencentProvider(DataProvider):
    """Tencent Finance provider for real-time quotes.

    Uses qt.gtimg.cn for quotes (works from US servers).
    Falls back to AKShare for news, financials, and stock info.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def get_realtime_quotes(self, codes: list[str]) -> list[StockQuote]:
        """Fetch real-time quotes from Tencent Finance API."""
        if not codes:
            return []

        symbols = ",".join(f"{_market_prefix(c)}{c}" for c in codes)
        url = f"{TENCENT_QT_URL}{symbols}"

        try:
            client = await self._get_client()
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.content.decode("gbk", errors="replace")
            quotes = _parse_tencent_response(text)
            log.info(
                "tencent_quotes_fetched",
                requested=len(codes),
                returned=len(quotes),
            )
            return quotes
        except Exception:
            log.error("tencent_quotes_failed", exc_info=True)
            return []

    async def get_stock_info(self, code: str) -> StockInfo | None:
        """Delegate to AKShare for stock info."""
        try:
            from app.providers.akshare_ths import AKShareTHSProvider

            return await AKShareTHSProvider().get_stock_info(code)
        except Exception:
            log.warning("akshare_stock_info_fallback_failed", code=code)
            return None

    async def get_stock_news(self, code: str, limit: int = 10) -> list[NewsItem]:
        """Delegate to AKShare for news."""
        try:
            from app.providers.akshare_ths import AKShareTHSProvider

            return await AKShareTHSProvider().get_stock_news(code, limit=limit)
        except Exception:
            log.warning("akshare_news_fallback_failed", code=code)
            return []

    async def get_financial_summary(self, code: str) -> FinancialSummary | None:
        """Delegate to AKShare for financials."""
        try:
            from app.providers.akshare_ths import AKShareTHSProvider

            return await AKShareTHSProvider().get_financial_summary(code)
        except Exception:
            log.warning("akshare_financials_fallback_failed", code=code)
            return None
