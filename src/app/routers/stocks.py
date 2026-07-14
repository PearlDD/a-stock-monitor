"""Stock market data API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.logging import get_logger
from app.services import market_data

log = get_logger("api.stocks")

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/quotes")
async def get_quotes(
    codes: str = Query(..., description="Comma-separated stock codes"),
):
    """Get real-time quotes for specified stocks."""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return {"quotes": []}

    quotes = await market_data.get_realtime_quotes(code_list)
    return {
        "quotes": [
            {
                "code": q.code,
                "name": q.name,
                "price": q.price,
                "change_pct": q.change_pct,
                "volume": q.volume,
                "amount": q.amount,
                "high": q.high,
                "low": q.low,
                "open": q.open,
                "prev_close": q.prev_close,
                "timestamp": q.timestamp.isoformat() if q.timestamp else None,
            }
            for q in quotes
        ]
    }


@router.get("/{code}/info")
async def get_stock_info(code: str):
    """Get basic company info for a stock."""
    info = await market_data.get_stock_info(code)
    if info is None:
        return {"info": None}
    return {
        "info": {
            "code": info.code,
            "name": info.name,
            "sector": info.sector,
            "market": info.market,
            "list_date": info.list_date,
            "tags": info.tags,
        }
    }


@router.get("/{code}/news")
async def get_stock_news(code: str, limit: int = Query(10, ge=1, le=50)):
    """Get recent news for a stock."""
    items = await market_data.get_stock_news(code, limit=limit)
    return {
        "news": [
            {
                "title": n.title,
                "source": n.source,
                "url": n.url,
                "publish_time": n.publish_time.isoformat() if n.publish_time else None,
                "stock_code": n.stock_code,
            }
            for n in items
        ]
    }


@router.get("/{code}/financials")
async def get_financials(code: str):
    """Get key financial metrics for a stock."""
    summary = await market_data.get_financial_summary(code)
    if summary is None:
        return {"financials": None}
    return {
        "financials": {
            "code": summary.code,
            "name": summary.name,
            "market_cap": summary.market_cap,
            "pe_ratio": summary.pe_ratio,
            "pb_ratio": summary.pb_ratio,
            "revenue": summary.revenue,
            "net_profit": summary.net_profit,
        }
    }


@router.get("/{code}/history")
async def get_price_history(code: str, days: int = Query(5, ge=1, le=30)):
    """Get recent daily price history for a stock."""
    history = await market_data.get_price_history(code, days=days)
    return {"history": history}


@router.get("/{code}/announcements")
async def get_announcements(code: str, limit: int = Query(10, ge=1, le=50)):
    """Get company announcements for a stock."""
    items = await market_data.get_announcements(code, limit=limit)
    return {"announcements": items}
