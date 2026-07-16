"""Demo data provider with realistic pre-populated A-share data.

Used when DATA_MODE=mock — provides realistic stock data with price jitter
so the app is usable for development outside China where AKShare cannot connect.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.market import FinancialSummary, NewsItem, StockInfo, StockQuote
from app.providers.base import DataProvider

_SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

# Realistic A-share stock data: (code, name, base_price, change_pct, sector)
_DEMO_STOCKS: list[tuple[str, str, float, float, str]] = [
    ("600519", "贵州茅台", 1823.0, 1.5, "白酒"),
    ("000858", "五粮液", 168.0, -0.8, "白酒"),
    ("300750", "宁德时代", 215.0, 2.3, "新能源"),
    ("601318", "中国平安", 48.0, 0.5, "保险"),
    ("000001", "平安银行", 12.5, -0.3, "银行"),
    ("601899", "紫金矿业", 18.8, 3.2, "有色金属"),
    ("002594", "比亚迪", 285.0, 1.8, "新能源汽车"),
    ("600036", "招商银行", 35.0, -0.2, "银行"),
    ("601012", "隆基绿能", 22.5, -1.2, "光伏"),
    ("000333", "美的集团", 62.0, 0.8, "家电"),
    ("600900", "长江电力", 28.5, 0.3, "电力"),
    ("002475", "立讯精密", 35.8, 1.5, "电子"),
    ("601888", "中国中免", 82.0, -0.6, "免税"),
    ("300059", "东方财富", 18.5, 2.1, "券商"),
    ("600276", "恒瑞医药", 45.0, 0.9, "医药"),
    ("002304", "洋河股份", 98.5, -0.4, "白酒"),
    ("601398", "工商银行", 5.8, 0.2, "银行"),
    ("600030", "中信证券", 22.0, 1.1, "券商"),
    ("000568", "泸州老窖", 178.0, -0.5, "白酒"),
    ("002714", "牧原股份", 42.0, -1.8, "养殖"),
    ("300124", "汇川技术", 65.0, 1.3, "工控"),
    ("601166", "兴业银行", 18.2, 0.4, "银行"),
    ("002415", "海康威视", 32.0, -0.7, "安防"),
]

# Mock news headlines
_DEMO_NEWS: dict[str, list[tuple[str, str]]] = {
    "600519": [
        ("贵州茅台一季度净利润同比增长18.5%", "证券时报"),
        ("茅台冰淇淋全国门店突破100家", "新浪财经"),
        ("贵州茅台股东大会:坚持稳价策略", "东方财富"),
    ],
    "000858": [
        ("五粮液发布新品浓香系列 主打年轻市场", "中国证券报"),
        ("五粮液与多家大型商超签订战略合作", "上海证券报"),
    ],
    "300750": [
        ("宁德时代发布新一代麒麟电池 能量密度再创新高", "第一财经"),
        ("宁德时代海外工厂投产进展顺利", "证券日报"),
        ("锂电池行业景气度持续回升", "中国证券报"),
    ],
    "002594": [
        ("比亚迪6月销量突破30万辆 再创历史新高", "新浪财经"),
        ("比亚迪出海战略加速 欧洲市场份额扩大", "第一财经"),
    ],
    "601318": [
        ("中国平安上半年寿险新业务价值增长20%", "证券时报"),
        ("平安科技板块加速发展 AI应用落地多场景", "上海证券报"),
    ],
}

# Mock financial data: (pe, pb, revenue_yi, net_profit_yi, market_cap_yi)
_DEMO_FINANCIALS: dict[str, tuple[float, float, float, float, float]] = {
    "600519": (33.5, 12.8, 1505.0, 747.0, 22890.0),
    "000858": (22.1, 5.6, 832.0, 302.0, 6520.0),
    "300750": (28.4, 5.2, 4009.0, 441.0, 9450.0),
    "601318": (8.9, 1.1, 9572.0, 1179.0, 8760.0),
    "000001": (5.5, 0.6, 1799.0, 465.0, 2430.0),
    "601899": (15.2, 3.8, 2934.0, 283.0, 4920.0),
    "002594": (25.8, 6.1, 6023.0, 300.0, 8280.0),
    "600036": (6.2, 0.9, 3447.0, 1380.0, 8820.0),
}


class DemoProvider(DataProvider):
    """Demo provider with realistic pre-populated A-share data.

    Prices jitter ±0.5% on each fetch to simulate market movement.
    """

    def __init__(self) -> None:
        self._base_prices: dict[str, float] = {}
        self._stocks: dict[str, tuple[str, float, str]] = {}  # name, change_pct, sector
        for code, name, price, change_pct, sector in _DEMO_STOCKS:
            self._base_prices[code] = price
            self._stocks[code] = (name, change_pct, sector)

    def _jittered_price(self, code: str) -> float:
        base = self._base_prices[code]
        jitter = random.uniform(-0.005, 0.005)
        return round(base * (1 + jitter), 2)

    async def get_realtime_quotes(self, codes: list[str]) -> list[StockQuote]:
        now = datetime.now(tz=_SHANGHAI_TZ)
        quotes: list[StockQuote] = []
        for code in codes:
            if code not in self._stocks:
                continue
            name, change_pct, _sector = self._stocks[code]
            price = self._jittered_price(code)
            base = self._base_prices[code]
            prev_close = round(base / (1 + change_pct / 100), 2)
            quotes.append(
                StockQuote(
                    code=code,
                    name=name,
                    price=price,
                    change_pct=round(change_pct + random.uniform(-0.3, 0.3), 2),
                    volume=round(random.uniform(50000, 500000), 0),
                    amount=round(random.uniform(1e8, 5e9), 0),
                    high=round(price * 1.01, 2),
                    low=round(price * 0.99, 2),
                    open=round(prev_close * (1 + random.uniform(-0.005, 0.005)), 2),
                    prev_close=prev_close,
                    timestamp=now,
                    market_status="demo",
                ),
            )
        return quotes

    async def get_stock_info(self, code: str) -> StockInfo | None:
        if code not in self._stocks:
            return None
        name, _, sector = self._stocks[code]
        return StockInfo(
            code=code,
            name=name,
            sector=sector,
            market="SH" if code.startswith("6") else "SZ",
            list_date="",
        )

    async def get_stock_news(self, code: str, limit: int = 10) -> list[NewsItem]:
        raw = _DEMO_NEWS.get(code, [])
        if not raw:
            # Generate generic news for stocks without specific entries
            if code not in self._stocks:
                return []
            name = self._stocks[code][0]
            raw = [
                (f"{name}最新研报:维持买入评级", "证券时报"),
                (f"{name}发布投资者关系活动记录表", "上海证券报"),
            ]
        now = datetime.now(tz=_SHANGHAI_TZ)
        items: list[NewsItem] = []
        for i, (title, source) in enumerate(raw[:limit]):
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    url="",
                    publish_time=now - timedelta(hours=i * 2),
                    stock_code=code,
                )
            )
        return items

    async def get_financial_summary(self, code: str) -> FinancialSummary | None:
        fin = _DEMO_FINANCIALS.get(code)
        if fin is None:
            if code not in self._stocks:
                return None
            name = self._stocks[code][0]
            return FinancialSummary(
                code=code,
                name=name,
                pe_ratio=round(random.uniform(8, 40), 1),
                pb_ratio=round(random.uniform(0.5, 8), 1),
                revenue=round(random.uniform(100, 3000) * 1e8, 0),
                net_profit=round(random.uniform(10, 500) * 1e8, 0),
            )
        pe, pb, rev, profit, cap = fin
        name = self._stocks[code][0]
        return FinancialSummary(
            code=code,
            name=name,
            market_cap=cap * 1e8,
            pe_ratio=pe,
            pb_ratio=pb,
            revenue=rev * 1e8,
            net_profit=profit * 1e8,
        )
