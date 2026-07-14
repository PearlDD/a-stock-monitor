"""Mock data provider for testing without network calls."""

from datetime import UTC, datetime

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider


class MockProvider(DataProvider):
    """Controllable fake provider for deterministic testing."""

    def __init__(self) -> None:
        self._prices: dict[str, tuple[float, float]] = {}
        self._news: dict[str, list[NewsItem]] = {}
        self._financials: dict[str, FinancialSummary] = {}
        self._stocks: list[StockInfo] = []

    def set_price(
        self, symbol: str, price: float, change_pct: float = 0.0
    ) -> None:
        """Set the price returned by get_quote for a symbol."""
        self._prices[symbol] = (price, change_pct)

    def inject_news(
        self,
        symbol: str,
        title: str,
        keywords: list[str] | None = None,
        url: str = "https://example.com/news",
        source: str = "mock",
    ) -> None:
        """Add a fake news item for a symbol."""
        item = NewsItem(
            symbol=symbol,
            title=title,
            url=url,
            source=source,
            published_at=datetime.now(tz=UTC),
            keywords=keywords or [],
        )
        self._news.setdefault(symbol, []).append(item)

    def set_financials(self, summary: FinancialSummary) -> None:
        """Set the financial summary returned for a symbol."""
        self._financials[summary.symbol] = summary

    def add_stock(self, info: StockInfo) -> None:
        """Add a stock to search results."""
        self._stocks.append(info)

    async def get_quote(self, symbol: str) -> StockQuote:
        price, change_pct = self._prices.get(symbol, (100.0, 0.0))
        return StockQuote(
            symbol=symbol,
            name=f"Mock-{symbol}",
            price=price,
            change_pct=change_pct,
            volume=1_000_000.0,
            timestamp=datetime.now(tz=UTC),
        )

    async def get_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        return self._news.get(symbol, [])[:limit]

    async def get_financials(self, symbol: str) -> FinancialSummary:
        if symbol in self._financials:
            return self._financials[symbol]
        return FinancialSummary(symbol=symbol, name=f"Mock-{symbol}")

    async def search_stocks(self, keyword: str) -> list[StockInfo]:
        return [
            s
            for s in self._stocks
            if keyword in s.name or keyword in s.symbol
        ]
