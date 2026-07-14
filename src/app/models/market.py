"""Market data models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StockQuote:
    """Real-time stock quote snapshot."""

    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    timestamp: datetime


@dataclass
class NewsItem:
    """Stock news article."""

    symbol: str
    title: str
    url: str
    source: str
    published_at: datetime
    keywords: list[str] = field(default_factory=list)


@dataclass
class FinancialSummary:
    """Quarterly financial abstract for a stock."""

    symbol: str
    name: str
    pe_ratio: float | None = None
    revenue: float | None = None
    net_profit: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    report_date: str | None = None


@dataclass
class StockInfo:
    """Basic stock information (search results)."""

    symbol: str
    name: str
    industry: str = ""
