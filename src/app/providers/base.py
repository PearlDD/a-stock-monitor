"""Abstract base class for data providers."""

from abc import ABC, abstractmethod

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote


class DataProvider(ABC):
    """Interface for stock data sources."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> StockQuote:
        """Fetch real-time quote for a stock symbol."""
        ...

    @abstractmethod
    async def get_news(self, symbol: str, limit: int = 10) -> list[NewsItem]:
        """Fetch recent news for a stock symbol."""
        ...

    @abstractmethod
    async def get_financials(self, symbol: str) -> FinancialSummary:
        """Fetch financial summary for a stock symbol."""
        ...

    @abstractmethod
    async def search_stocks(self, keyword: str) -> list[StockInfo]:
        """Search stocks by name or keyword."""
        ...
