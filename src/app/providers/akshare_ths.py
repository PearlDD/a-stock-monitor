"""AKShare THS data provider implementing DataProvider ABC.

All AKShare calls go through asyncio.to_thread() since AKShare is synchronous.
Uses rate limiter to prevent bans and circuit breaker for resilience.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.logging import get_logger
from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider
from app.providers.rate_limiter import get_rate_limiter

log = get_logger("akshare_ths")

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class AKShareTHSProvider(DataProvider):
    """AKShare provider using THS interfaces for A-share data.

    All calls wrapped in asyncio.to_thread() for async safety.
    Rate limited to prevent AKShare anti-crawling bans.
    """

    async def get_realtime_quotes(self, codes: list[str]) -> list[StockQuote]:
        """Fetch real-time quotes via ak.stock_zh_a_spot_em(), filter to watchlist."""
        limiter = get_rate_limiter()
        await limiter.acquire()

        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            limiter.record_success()
        except Exception:
            limiter.record_error()
            log.error("akshare_quotes_failed", exc_info=True)
            return []

        now = datetime.now(tz=SHANGHAI_TZ)
        code_set = set(codes)
        quotes: list[StockQuote] = []

        for _, row in df.iterrows():
            stock_code = str(row.get("代码", ""))
            if stock_code not in code_set:
                continue
            try:
                quotes.append(
                    StockQuote(
                        code=stock_code,
                        name=str(row.get("名称", "")),
                        price=float(row.get("最新价", 0) or 0),
                        change_pct=float(row.get("涨跌幅", 0) or 0),
                        volume=float(row.get("成交量", 0) or 0),
                        amount=float(row.get("成交额", 0) or 0),
                        high=float(row.get("最高", 0) or 0),
                        low=float(row.get("最低", 0) or 0),
                        open=float(row.get("今开", 0) or 0),
                        prev_close=float(row.get("昨收", 0) or 0),
                        timestamp=now,
                    )
                )
            except (ValueError, TypeError):
                continue

        log.info("quotes_fetched", requested=len(codes), returned=len(quotes))
        return quotes

    async def get_stock_info(self, code: str) -> StockInfo | None:
        """Fetch basic stock info via ak.stock_individual_info_em()."""
        limiter = get_rate_limiter()
        await limiter.acquire()

        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=code)
            limiter.record_success()

            info_dict = dict(zip(df["item"], df["value"]))
            info = StockInfo(
                code=code,
                name=str(info_dict.get("股票简称", "")),
                sector=str(info_dict.get("行业", "")),
                market=str(info_dict.get("上市时间", ""))[:4],
                list_date=str(info_dict.get("上市时间", "")),
            )
            log.info("stock_info_fetched", code=code)
            return info
        except Exception:
            limiter.record_error()
            log.error("stock_info_failed", code=code, exc_info=True)
            return None

    async def get_stock_news(self, code: str, limit: int = 10) -> list[NewsItem]:
        """Fetch recent news via ak.stock_news_em()."""
        limiter = get_rate_limiter()
        await limiter.acquire()

        try:
            import akshare as ak

            df = await asyncio.to_thread(ak.stock_news_em, symbol=code)
            limiter.record_success()

            items: list[NewsItem] = []
            for _, row in df.head(50).iterrows():
                pub_time = None
                raw_time = row.get("发布时间", "")
                if raw_time:
                    try:
                        pub_time = datetime.strptime(
                            str(raw_time), "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=SHANGHAI_TZ)
                    except ValueError:
                        pass
                items.append(
                    NewsItem(
                        title=str(row.get("新闻标题", "")),
                        source=str(row.get("新闻来源", "")),
                        url=str(row.get("新闻链接", "")),
                        publish_time=pub_time,
                        stock_code=code,
                    )
                )
            log.info("news_fetched", code=code, count=len(items))
            return items[:limit]
        except Exception:
            limiter.record_error()
            log.error("news_fetch_failed", code=code, exc_info=True)
            return []

    async def get_financial_summary(self, code: str) -> FinancialSummary | None:
        """Fetch key financials via ak.stock_financial_abstract_ths()."""
        limiter = get_rate_limiter()
        await limiter.acquire()

        try:
            import akshare as ak

            df = await asyncio.to_thread(
                ak.stock_financial_abstract_ths, symbol=code
            )
            limiter.record_success()

            if df.empty:
                return None
            row = df.iloc[0]
            summary = FinancialSummary(
                code=code,
                name=str(row.get("股票简称", "")),
                pe_ratio=float(row.get("市盈率", 0) or 0),
                pb_ratio=float(row.get("市净率", 0) or 0),
                revenue=float(row.get("营业总收入", 0) or 0),
                net_profit=float(row.get("净利润", 0) or 0),
            )
            log.info("financials_fetched", code=code)
            return summary
        except Exception:
            limiter.record_error()
            log.error("financials_fetch_failed", code=code, exc_info=True)
            return None
