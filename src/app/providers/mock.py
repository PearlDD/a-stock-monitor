"""Mock data provider for testing."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider

_SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class MockProvider(DataProvider):
    """In-memory mock provider for tests. No network calls."""

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        self._names: dict[str, str] = {}
        self._news: dict[str, list[NewsItem]] = {}
        self._info: dict[str, StockInfo] = {}
        self._financials: dict[str, FinancialSummary] = {}
        self._quote_extras: dict[str, dict] = {}
        self._volumes: dict[str, float] = {}

    # -- Test helpers --

    def set_price(
        self,
        code: str,
        price: float,
        *,
        name: str = "",
        change_pct: float = 0.0,
        prev_close: float = 0.0,
        volume: float = 0.0,
    ) -> None:
        """Set or update the price for a stock code."""
        self._prices[code] = price
        if name:
            self._names[code] = name
        if not self._names.get(code):
            self._names[code] = f"Mock-{code}"
        self._quote_extras[code] = {
            "change_pct": change_pct,
            "prev_close": prev_close or price,
        }
        if volume > 0:
            self._volumes[code] = volume

    def inject_news(self, code: str, items: list[NewsItem]) -> None:
        """Inject news items for a stock code."""
        self._news.setdefault(code, []).extend(items)

    def set_info(self, code: str, info: StockInfo) -> None:
        """Set company info for a stock code."""
        self._info[code] = info

    def set_financials(self, code: str, summary: FinancialSummary) -> None:
        """Set financial summary for a stock code."""
        self._financials[code] = summary

    # -- DataProvider implementation --

    async def get_realtime_quotes(self, codes: list[str]) -> list[StockQuote]:
        now = datetime.now(tz=_SHANGHAI_TZ)
        quotes: list[StockQuote] = []
        for code in codes:
            if code not in self._prices:
                continue
            price = self._prices[code]
            ext = self._quote_extras.get(code, {})
            prev_close = ext.get("prev_close", price)
            volume = self._volumes.get(code, 0.0)
            quotes.append(
                StockQuote(
                    code=code,
                    name=self._names.get(code, f"Mock-{code}"),
                    price=price,
                    change_pct=ext.get("change_pct", 0.0),
                    volume=volume,
                    amount=0.0,
                    high=price,
                    low=price,
                    open=prev_close,
                    prev_close=prev_close,
                    timestamp=now,
                ),
            )
        return quotes

    async def get_stock_info(self, code: str) -> StockInfo | None:
        return self._info.get(code)

    async def get_stock_news(self, code: str, limit: int = 10) -> list[NewsItem]:
        return self._news.get(code, [])[:limit]

    async def get_financial_summary(self, code: str) -> FinancialSummary | None:
        return self._financials.get(code)
