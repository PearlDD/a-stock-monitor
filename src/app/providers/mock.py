"""Mock data provider for testing."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider

_SHANGHAI_OFFSET = timezone(offset=__import__("datetime").timedelta(hours=8))


class MockProvider(DataProvider):
    """In-memory mock provider for tests. No network calls."""

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        self._names: dict[str, str] = {}
        self._news: dict[str, list[NewsItem]] = {}
        self._info: dict[str, StockInfo] = {}
        self._financials: dict[str, FinancialSummary] = {}

    # -- Test helpers --

    def set_price(
        self,
        code: str,
        price: float,
        *,
        name: str = "",
        change_pct: float = 0.0,
        prev_close: float = 0.0,
    ) -> None:
        """Set or update the price for a stock code."""
        self._prices[code] = price
        if name:
            self._names[code] = name
        if not self._names.get(code):
            self._names[code] = f"Mock-{code}"
        # Store extra fields for quote construction
        self._quote_extras: dict[str, dict] = getattr(self, "_quote_extras", {})
        self._quote_extras[code] = {
            "change_pct": change_pct,
            "prev_close": prev_close or price,
        }

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
        now = datetime.now(tz=_SHANGHAI_OFFSET)
        quotes: list[StockQuote] = []
        extras = getattr(self, "_quote_extras", {})
        for code in codes:
            if code not in self._prices:
                continue
            price = self._prices[code]
            ext = extras.get(code, {})
            prev_close = ext.get("prev_close", price)
            quotes.append(
                StockQuote(
                    code=code,
                    name=self._names.get(code, f"Mock-{code}"),
                    price=price,
                    change_pct=ext.get("change_pct", 0.0),
                    volume=0.0,
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
