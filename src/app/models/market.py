"""Market data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StockQuote:
    """Real-time stock quote."""

    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    high: float
    low: float
    open: float
    prev_close: float
    timestamp: datetime | None = None
    market_status: str = "trading"  # "trading" or "closed"


@dataclass
class NewsItem:
    """A stock-related news headline."""

    title: str
    source: str
    url: str
    publish_time: datetime | None = None
    stock_code: str = ""


@dataclass
class FinancialSummary:
    """Key financial metrics for a stock."""

    code: str
    name: str
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    revenue: float = 0.0
    net_profit: float = 0.0


@dataclass
class StockInfo:
    """Basic company information."""

    code: str
    name: str
    sector: str = ""
    market: str = ""
    list_date: str = ""
    tags: list[str] = field(default_factory=list)
