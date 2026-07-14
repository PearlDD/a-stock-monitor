# Research Report — A股智能监控系统

## Project Summary

A personal A-share stock monitoring tool that auto-collects real-time quotes and news, pushes alerts to WeChat (via PushPlus) when price targets or news keywords are hit. Web UI for managing watchlists and alert rules. Stack: Python + FastAPI + AKShare (THS) + SQLite + HTMX/SSE + APScheduler + Docker.

Phase 1 (PushPlus push) is complete. Project is starting Phase 2 (data collection layer).

---

## Similar Projects

| Project | Stars | Relevance | Key Takeaway |
|---------|-------|-----------|--------------|
| [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | Active | High | LLM-driven multi-market analysis with AKShare fallback, multi-channel push (WeChat Work/Telegram/Slack), GitHub Actions scheduling. Architecture: modular data providers with fallback chain. |
| [stock-scanner](https://github.com/DR-lin-eng/stock-scanner) | Active | Medium | AI-enhanced A-share analysis, 25 financial indicators, news sentiment. Shows how to structure indicator calculations. |
| [aiagents-stock](https://github.com/oficcejo/aiagents-stock) | Active | Medium | Multi-agent monitoring with real-time alerts and notification services. Complex but shows alert engine patterns. |
| [pythonstock/stock](https://github.com/pythonstock/stock) | Mature | Medium | Full-stack Python stock system with Docker deployment, MySQL storage. Good reference for Docker packaging. |
| [adata](https://github.com/1nchaos/adata) | Active | Low-Med | Multi-source data fusion with dynamic proxy. Shows resilient data fetching patterns. |
| [Ashare](https://github.com/mpquant/Ashare) | Mature | Low | Minimal real-time data wrapper. Shows simplest possible quote fetching. |

**Key pattern across projects**: All successful ones use a DataProvider abstraction layer with fallback sources. This validates the spec's MockProvider + AKShare provider design.

---

## AKShare THS Interface — Usage & Pitfalls

### Verified Working Interfaces

Based on the spec's validation and AKShare docs:

```python
import akshare as ak

# Industry sector names (板块列表)
df = ak.stock_board_industry_name_ths()

# Financial abstract for a stock (财务摘要)
df = ak.stock_financial_abstract_ths(symbol="000001", indicator="按报告期")

# Stock news from East Money (新闻 — note: uses EM, not THS)
df = ak.stock_news_em(stock="000001")
```

### Critical: Rate Limiting

AKShare has **no built-in rate limiting**. The underlying data sources (THS, East Money) enforce anti-crawling:

- **No official rate limit numbers published** — thresholds are opaque and change without notice
- Users report getting blocked "mysteriously" with no clear recovery time ([akfamily/akshare#6990](https://github.com/akfamily/akshare/issues/6990))
- THS interfaces added 401 anti-crawling in early 2026 for some endpoints
- **2026 legal context**: China's modified Cybersecurity Law (effective 2026-01-01) tightens rules around web scraping

### Recommended Rate Limiting Strategy

```
- Minimum 2-3 seconds between requests to same data source
- Batch stock queries where API supports it (reduce total calls)
- Cache financial data aggressively (changes quarterly, not minutely)
- Cache news for 5+ minutes
- Real-time quotes: 1 request per stock per minute (spec says "每分钟刷新")
- For 20 stocks: ~20 requests/minute = 1 every 3 seconds (safe)
- For 50+ stocks: consider batching or longer intervals
- Log all request timestamps for debugging rate limit issues
- Implement exponential backoff on HTTP errors (401, 403, 429, 5xx)
```

### Data Freshness by Type

| Data Type | Update Frequency | Cache Duration |
|-----------|-----------------|----------------|
| Quotes/Prices | Real-time during trading | 60 seconds |
| News | Throughout day | 5 minutes |
| Financial abstracts | Quarterly | 24 hours |
| Industry sectors | Rarely changes | 1 week |

---

## FastAPI + Jinja2 + HTMX Architecture

### Recommended Project Structure

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Pydantic Settings (.env loading)
│   ├── database.py          # SQLite setup (aiosqlite)
│   ├── models.py            # SQLAlchemy/dataclass models
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # DataProvider ABC
│   │   ├── akshare_ths.py   # AKShare THS implementation
│   │   └── mock.py          # MockProvider for testing
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── monitor.py       # Price monitoring loop
│   │   ├── alerts.py        # Alert evaluation & dedup
│   │   ├── news.py          # News monitoring & keyword matching
│   │   └── scheduler.py     # APScheduler setup
│   ├── push/
│   │   ├── __init__.py
│   │   └── pushplus.py      # PushPlus API client
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py         # Full HTML page routes
│   │   ├── api.py           # REST API (JSON + HTMX fragments)
│   │   └── sse.py           # SSE streaming endpoints
│   └── templates/
│       ├── base.html
│       ├── components/      # Reusable Jinja2 partials
│       │   ├── stock_card.html
│       │   ├── alert_row.html
│       │   └── nav.html
│       └── pages/
│           ├── dashboard.html
│           ├── watchlist.html
│           ├── alerts.html
│           └── history.html
├── static/
│   ├── css/
│   ├── js/                  # htmx.min.js (self-hosted)
│   └── img/
├── tests/
│   ├── test_providers.py
│   ├── test_alerts.py
│   ├── test_engine.py
│   └── test_api.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

### SSE Real-Time Updates Pattern

The proven pattern for HTMX + SSE dashboards (from [Medium/CodeX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb)):

**Backend (FastAPI):**
```python
from sse_starlette.sse import EventSourceResponse

@app.get("/stream/quotes")
async def stream_quotes():
    async def event_generator():
        try:
            while True:
                quotes = await get_latest_quotes()  # from cache/DB
                html = templates.get_template(
                    "components/quote_table.html"
                ).render(quotes=quotes)
                yield {"event": "quote_update", "data": html}
                await asyncio.sleep(60)  # match monitoring interval
        except asyncio.CancelledError:
            pass
    return EventSourceResponse(event_generator())
```

**Frontend (HTMX):**
```html
<div hx-ext="sse" sse-connect="/stream/quotes">
    <div id="quotes" sse-swap="quote_update" hx-swap="innerHTML">
        <!-- Loading spinner -->
    </div>
</div>
```

**Key best practices:**
- Use `sse-starlette` package for SSE support
- Stream rendered HTML fragments, not JSON (let server do the rendering)
- Include `Vary: HX-Request` header for CDN/proxy compatibility
- Dual-response pattern: same route returns full page or fragment based on `HX-Request` header
- Self-host htmx.min.js (~14KB gzipped) — no CDN dependency
- Performance: expect sub-50ms partial updates

### Dependencies

```
fastapi
uvicorn[standard]
jinja2
sse-starlette
python-multipart    # form handling
```

---

## APScheduler + FastAPI Integration

### Setup Pattern (AsyncIOScheduler)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(monitor_quotes, "cron",
                      day_of_week="mon-fri",
                      hour="9-11,13-15",
                      minute="*/1")
    scheduler.add_job(monitor_news, "interval", minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### Critical Considerations

1. **Single worker only**: If using multiple uvicorn workers, scheduler runs in EACH worker. For this personal tool, single worker is fine. Document this constraint.
2. **Error handling**: Wrap every job in try/except — an unhandled exception kills the scheduler.
3. **Job persistence**: APScheduler's default MemoryJobStore loses jobs on restart. For this use case (cron-based, not dynamic), that's fine — jobs are defined in code.
4. **Trading hours**: Use cron expressions to restrict to A-share trading hours (9:30-11:30, 13:00-15:00 Beijing time). Add a `is_trading_day()` check inside the job as a second gate.

---

## PushPlus API Integration

### API Specification

```
POST http://www.pushplus.plus/send
Content-Type: application/json

{
    "token": "YOUR_TOKEN",
    "title": "股价预警: 贵州茅台",
    "content": "<h2>目标价位触发</h2><p>当前价: ¥1850.00</p>",
    "template": "html",
    "channel": "wechat"
}

Response: {"code": 200, "msg": "请求成功", "data": "serial_number"}
```

### Rate Limits

- **200 messages/day** free tier
- Exceeding 200: messages silently dropped
- Exceeding 400 attempts: **account blocked for 2 days**
- **Must track daily send count** to avoid the 400-attempt ban

### Recommended Implementation

```python
class PushPlusClient:
    MAX_DAILY = 180  # Safety margin below 200
    
    async def send(self, title: str, content: str) -> bool:
        if self.daily_count >= self.MAX_DAILY:
            logger.warning("Daily push limit approaching, skipping")
            return False
        # ... send request
        self.daily_count += 1
```

- Store daily count in DB, reset at midnight Beijing time
- Set safety threshold at 180 (not 200) to leave room for test pushes
- Log all push attempts with serial numbers for debugging
- `code: 200` means "server received it", NOT "delivered to WeChat" — query delivery status separately if needed

---

## SQLite Schema Design

### Recommended Tables

```sql
-- Watchlist stocks
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL,     -- e.g., "600519"
    name TEXT NOT NULL,              -- e.g., "贵州茅台"
    industry TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Alert rules
CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    rule_type TEXT NOT NULL,         -- 'price_above', 'price_below', 'change_pct', 'news_keyword'
    threshold REAL,                  -- price or percentage
    keyword TEXT,                    -- for news alerts
    cooldown_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price snapshots (latest + recent history)
CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    price REAL NOT NULL,
    change_pct REAL,
    volume REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_snapshots_stock_time ON price_snapshots(stock_id, timestamp);

-- Push notification history
CREATE TABLE push_history (
    id INTEGER PRIMARY KEY,
    alert_rule_id INTEGER REFERENCES alert_rules(id),
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    push_serial TEXT,               -- PushPlus serial number
    status TEXT DEFAULT 'sent',     -- 'sent', 'failed', 'rate_limited'
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_push_stock_time ON push_history(stock_id, sent_at);

-- News cache
CREATE TABLE news_cache (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    url TEXT,
    source TEXT,
    content_hash TEXT UNIQUE,       -- dedup by content hash
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_news_stock ON news_cache(stock_id, fetched_at);
```

### Design Decisions

- **WAL mode**: Enable `PRAGMA journal_mode=WAL` for concurrent read/write (scheduler writes while web UI reads)
- **Price snapshot retention**: Keep 30 days, purge older. With 20 stocks × 240 minutes/day ≈ 4800 rows/day — negligible for SQLite
- **News dedup**: Use `content_hash` (MD5 of title+url) to avoid duplicate entries
- **No ORM overhead for reads**: Use raw SQL for dashboard queries (performance), SQLAlchemy for schema management only

---

## Trading Calendar & Hours

### Recommended Approach

Use `chinese-calendar` or `cn-stock-holidays` package:

```python
from chinese_calendar import is_workday, is_holiday
from datetime import datetime, time
import pytz

SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")

def is_trading_time() -> bool:
    now = datetime.now(SHANGHAI_TZ)
    if is_holiday(now.date()):
        return False
    t = now.time()
    morning = time(9, 30) <= t <= time(11, 30)
    afternoon = time(13, 0) <= t <= time(15, 0)
    return morning or afternoon
```

### Pitfalls

- **Chinese holidays are irregular**: Spring Festival, National Day dates change yearly. The `chinese-calendar` package updates annually (supports through 2026).
- **Saturday/Sunday trading**: Never happens for A-shares, but some years have "补班" (make-up workdays on weekends) that are NOT trading days. `chinese-calendar` handles this correctly.
- **Pre-market/after-hours**: A-shares have a call auction 9:15-9:25 — decide if you want to monitor this period.
- **Half-day sessions**: Rare but possible (e.g., typhoon warnings in Shenzhen). Not worth coding for MVP.

---

## Mock/Test Provider Pattern

### Recommended Design

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class StockQuote:
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    timestamp: datetime

class DataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> StockQuote: ...
    
    @abstractmethod
    async def get_news(self, symbol: str, limit: int = 10) -> list[NewsItem]: ...
    
    @abstractmethod
    async def get_financials(self, symbol: str) -> FinancialSummary: ...
    
    @abstractmethod
    async def search_stocks(self, keyword: str) -> list[StockInfo]: ...

class MockProvider(DataProvider):
    """Controllable provider for testing. Supports:
    - set_price(symbol, price) — manually set price for trigger testing
    - inject_news(symbol, title, keywords) — inject fake news
    - simulate_day(symbol) — replay a full trading day
    """
```

This pattern allows `--test` mode to run the complete pipeline without any network calls.

---

## Potential Pitfalls & Mitigations

| Pitfall | Impact | Mitigation |
|---------|--------|------------|
| AKShare THS 401 errors (anti-crawling) | Data collection stops | Exponential backoff + rate limiting + log alerts |
| PushPlus 400-attempt ban | 2-day push blackout | Track daily count, hard stop at 180 |
| Holiday calendar outdated | False alerts on holidays | Pin `chinese-calendar` version, check for updates annually |
| SQLite write contention | Slow dashboard during data writes | Enable WAL mode, separate read/write connections |
| SSE connection drops | Dashboard freezes | HTMX auto-reconnects SSE; add visual "disconnected" indicator |
| AKShare API changes | Breaking interface changes | Pin akshare version, add integration test that calls each API |
| Overseas network to THS | Intermittent connectivity | Retry logic, graceful degradation with cached data |
| Large watchlist (50+ stocks) | Rate limit hit | Batch requests where possible, stagger fetches |

---

## MVP Scope Recommendation

Aligned with the 5-phase plan, the MVP path (Phases 2-3) should deliver:

### Phase 2 Minimum Viable:
1. `DataProvider` ABC with `get_quote()`, `get_news()`, `get_financials()`
2. `AKShareTHSProvider` — real implementation with rate limiting
3. `MockProvider` — controllable test data
4. Rate limiter utility (token bucket or simple sleep-based)
5. Unit tests for providers

### Phase 3 Minimum Viable:
1. SQLite schema (5 tables above)
2. Alert engine: price trigger + change% trigger + news keyword trigger
3. Dedup logic (cooldown-based, per-rule)
4. Trading hours gate
5. PushPlus integration (with daily count tracking)
6. `--test` CLI flag → MockProvider + real push
7. REST API endpoints for Phase 4

### What to defer:
- Industry sector monitoring (nice-to-have, not core)
- Financial data display (can use cached data from initial fetch)
- Multi-channel push (PushPlus is sufficient for MVP)
- Historical price charts (Phase 4+ feature)

---

## References

- [AKShare GitHub](https://github.com/akfamily/akshare)
- [AKShare Documentation](https://akshare.akfamily.xyz/introduction.html)
- [AKShare Rate Limit Issue #6990](https://github.com/akfamily/akshare/issues/6990)
- [PushPlus API Docs](https://www.pushplus.plus/doc/guide/api.html)
- [PushPlus Rate Limits](https://www.pushplus.plus/doc/help/limit.html)
- [FastAPI + HTMX Guide (Blake Crosley)](https://blakecrosley.com/guides/fastapi-htmx)
- [Real-Time Dashboards with FastAPI + HTMX (Medium/CodeX)](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb)
- [FastAPI + HTMX (TestDriven.io)](https://testdriven.io/blog/fastapi-htmx/)
- [APScheduler + FastAPI (Sentry)](https://sentry.io/answers/schedule-tasks-with-fastapi/)
- [FastAPI Scheduling Guide (Medium)](https://medium.com/@rasifrazak123/fastapi-scheduling-background-tasks-backgroundtasks-vs-apscheduler-vs-celery-complete-guide-ff90d6be524b)
- [cn-stock-holidays PyPI](https://pypi.org/project/cn-stock-holidays/)
- [chinesecalendar PyPI](https://pypi.org/project/chinesecalendar/)
- [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)
- [stock-scanner](https://github.com/DR-lin-eng/stock-scanner)
- [2026 Data Compliance Guide](https://www.cnblogs.com/kobe-tech/p/19774887)
