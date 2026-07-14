"""Abstract base class for data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote


class DataProvider(ABC):
    """Abstract data provider for stock market data."""

    @abstractmethod
    async def get_realtime_quotes(self, codes: list[str]) -> list[StockQuote]:
        """Fetch real-time quotes for the given stock codes."""

    @abstractmethod
    async def get_stock_info(self, code: str) -> StockInfo | None:
        """Fetch basic company information for a stock."""

    @abstractmethod
    async def get_stock_news(self, code: str, limit: int = 10) -> list[NewsItem]:
        """Fetch recent news for a stock."""

    @abstractmethod
    async def get_financial_summary(self, code: str) -> FinancialSummary | None:
        """Fetch key financial metrics for a stock."""
