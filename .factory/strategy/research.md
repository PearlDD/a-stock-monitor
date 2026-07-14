# Research Report — A股智能监控系统

## Project Summary

A personal A-share stock monitoring tool that auto-collects real-time quotes and news, pushes alerts to WeChat (via PushPlus) when price targets or news keywords are hit. Web UI for managing watchlists and alert rules. Stack: Python + FastAPI + AKShare (THS) + SQLite + HTMX/SSE + APScheduler + Docker.

Phase 1 (PushPlus push) is complete. Project has NO source code yet — first Improve cycle must build project scaffold and core data layer (Phase 2).

---

## External Research Findings (Web Search 2026-07-14)

### 1. FastAPI + Jinja2 + HTMX Project Structure

**Source**: [Blake Crosley FastAPI+HTMX Guide](https://blakecrosley.com/guides/fastapi-htmx), [TestDriven.io](https://testdriven.io/courses/fastapi-htmx/fastapi-setup/), [Medium Production Guide](https://medium.com/@sylvesterranjithfrancis/complete-guide-building-production-ready-web-apps-with-fastapi-and-htmx-from-setup-to-deployment-3010b1c8ff5c)

**Recommended directory layout** (organize by type, not feature):

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Pydantic Settings (.env loading)
│   ├── database.py          # SQLite setup (aiosqlite)
│   ├── models.py            # Dataclass models (StockQuote, AlertRule, etc.)
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
│       ├── components/      # Reusable Jinja2 partials (_prefixed)
│       │   ├── _stock_card.html
│       │   ├── _alert_row.html
│       │   └── _nav.html
│       └── pages/
│           ├── dashboard.html
│           ├── watchlist.html
│           ├── alerts.html
│           └── history.html
├── static/
│   ├── css/
│   ├── js/                  # htmx.min.js (self-hosted, ~14KB gzipped)
│   └── img/
├── tests/
│   ├── conftest.py
│   ├── test_providers.py
│   ├── test_alerts.py
│   ├── test_engine.py
│   └── test_api.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

**Key patterns discovered**:

1. **Route duality** — Same route returns full page OR fragment based on `HX-Request` header:
   ```python
   @router.get("/dashboard")
   async def dashboard(request: Request):
       data = await get_dashboard_data()
       if request.headers.get("HX-Request"):
           return templates.TemplateResponse("components/_quote_table.html", {"quotes": data})
       return templates.TemplateResponse("pages/dashboard.html", {"quotes": data})
   ```

2. **Underscore prefix convention** — Components never rendered standalone use `_` prefix (`_stock_card.html`), distinguishing fragments from pages.

3. **OOB (Out-of-Band) swaps** — Single response updates multiple DOM elements. Critical for stock dashboard: update quote table AND alert count badge in one response:
   ```html
   <div id="quotes">…updated table…</div>
   <span id="alert-count" hx-swap-oob="true">3</span>
   ```

4. **`Vary: HX-Request` header** — Essential for CDN/proxy compatibility when same URL serves full page vs fragment.

5. **Self-host htmx.min.js** — No CDN dependency for reliability.

6. **Jinja2 globals** — Register translation, CSRF, asset URL functions as globals so every template can use them without route-handler passing.

**Dependencies**: `fastapi`, `uvicorn[standard]`, `jinja2`, `sse-starlette`, `python-multipart`

---

### 2. AKShare THS API — Critical 2026 Findings

**Sources**: [AKShare GitHub](https://github.com/akfamily/akshare), [Issue #7051](https://github.com/akfamily/akshare/issues/7051), [AKShare Docs](https://akshare.akfamily.xyz/data/stock/stock.html)

#### API Instability Alert (NEW FINDING)

As of February 2026, **East Money `push2*` API endpoints are broken**:
- `stock_zh_a_hist()` — BROKEN (connection abort)
- `stock_individual_info_em()` — BROKEN (connection abort)

**Still working**:
- `stock_zh_a_spot()` — Real-time A-share market data (5,483+ stocks)
- `stock_info_a_code_name()` — A-share stock code/name listing
- `stock_zh_a_spot_em()` — Works via direct Python call, but has **asyncio event loop conflict** in async environments ("asyncio.run() cannot be called from a running event loop")

#### Verified THS Interfaces (from project validation)

```python
import akshare as ak

# Industry sector names
df = ak.stock_board_industry_name_ths()

# Financial abstract for a stock
df = ak.stock_financial_abstract_ths(symbol="000001", indicator="按报告期")

# Stock news (uses East Money, NOT THS)
df = ak.stock_news_em(stock="000001")
```

#### Critical: asyncio Compatibility

**AKShare uses `requests` (synchronous) internally**. In a FastAPI async context, calling AKShare directly will block the event loop. Two solutions:

1. **`asyncio.to_thread()`** (Python 3.9+) — Run AKShare calls in thread pool:
   ```python
   import asyncio
   result = await asyncio.to_thread(ak.stock_zh_a_spot_em)
   ```

2. **Dedicated thread executor** — For rate-limited sequential calls

This is essential for the DataProvider's async interface.

#### Rate Limiting Strategy

- **No official rate limits published** — thresholds are opaque and change without notice
- THS added 401 anti-crawling in early 2026
- **Recommended**: Minimum 2-3 seconds between requests to same source
- For 20 stocks: ~1 request/3 seconds (safe margin)
- Exponential backoff on HTTP errors (401, 403, 429, 5xx)
- Log all request timestamps for debugging

#### Data Freshness by Type

| Data Type | Update Frequency | Cache Duration |
|-----------|-----------------|----------------|
| Quotes/Prices | Real-time during trading | 60 seconds |
| News | Throughout day | 5 minutes |
| Financial abstracts | Quarterly | 24 hours |
| Industry sectors | Rarely changes | 1 week |

---

### 3. SQLite Schema Design

**Sources**: [SQLite WAL Tutorial](https://tech-insider.org/sqlite-python-tutorial-fts5-wal-mode-2026/), [aiosqlitepool](https://github.com/slaily/aiosqlitepool), [FastAPI async DB guide](https://oneuptime.com/blog/post/2026-02-02-fastapi-async-database/view)

#### aiosqlite for Async Access (NEW FINDING)

Standard `sqlite3` is synchronous and **blocks the event loop**. Must use `aiosqlite`:

```python
import aiosqlite

async def get_db():
    db = await aiosqlite.connect("stock_monitor.db")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA cache_size=10000")  # ~40MB cache
    await db.execute("PRAGMA busy_timeout=5000")  # 5s busy timeout
    try:
        yield db
    finally:
        await db.close()
```

Use FastAPI dependency injection: `async def route(db=Depends(get_db))`.

#### Write Contention Mitigation

SQLite uses a database-level lock for writes. With APScheduler writing price snapshots every minute while the web UI reads:
- **WAL mode** allows concurrent readers with one writer
- **busy_timeout** prevents immediate SQLITE_BUSY errors
- For this personal tool's scale (~4800 rows/day), contention is negligible

#### Recommended Tables (5 total)

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

-- News cache (deduplicated by content_hash)
CREATE TABLE news_cache (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    url TEXT,
    source TEXT,
    content_hash TEXT UNIQUE,       -- MD5 of title+url
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_news_stock ON news_cache(stock_id, fetched_at);
```

**Design decisions**:
- WAL mode for concurrent read/write
- Price snapshot retention: 30 days (purge older)
- News dedup via content_hash (MD5 of title+url)
- Raw SQL for read queries (performance), schema management via migrations

---

### 4. APScheduler + FastAPI Integration

**Sources**: [Sentry Guide](https://sentry.io/answers/schedule-tasks-with-fastapi/), [APScheduler Discussion #1088](https://github.com/agronholm/apscheduler/discussions/1088), [fastapi-scheduler](https://github.com/amisadmin/fastapi-scheduler)

#### Lifespan Pattern

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Quote monitoring: every minute during trading hours
    scheduler.add_job(monitor_quotes, "cron",
                      day_of_week="mon-fri",
                      hour="9-11,13-14",
                      minute="*/1",
                      id="quote_monitor")
    # News monitoring: every 5 minutes during trading hours
    scheduler.add_job(monitor_news, "cron",
                      day_of_week="mon-fri",
                      hour="9-15",
                      minute="*/5",
                      id="news_monitor")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

#### Critical Considerations

1. **Single worker only** — Scheduler runs in EACH uvicorn worker. Single worker is fine for personal tool. Document constraint.
2. **Error handling** — Every job MUST be wrapped in try/except. Unhandled exceptions kill the scheduler silently.
3. **Job persistence** — Default MemoryJobStore loses jobs on restart. For cron jobs defined in code, this is acceptable.
4. **Trading hours double-gate** — Use cron expressions for rough time windows + `is_trading_day()` check inside the job as a second gate (handles holidays).

---

### 5. MockProvider Pattern for Testing

**Sources**: [pytest external API testing](https://pytest-with-eric.com/api-testing/pytest-external-api-testing/), archive cross-project analysis

#### Recommended Design

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StockQuote:
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    timestamp: datetime

@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    keywords: list[str]

class DataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> StockQuote: ...

    @abstractmethod
    async def get_news(self, symbol: str, limit: int = 10) -> list[NewsItem]: ...

    @abstractmethod
    async def get_financials(self, symbol: str) -> dict: ...

    @abstractmethod
    async def search_stocks(self, keyword: str) -> list[dict]: ...

class MockProvider(DataProvider):
    """Controllable fake provider for testing without network."""

    def __init__(self):
        self._prices: dict[str, float] = {}
        self._news: dict[str, list[NewsItem]] = {}

    def set_price(self, symbol: str, price: float, change_pct: float = 0.0):
        """Manually set price for trigger testing."""
        self._prices[symbol] = (price, change_pct)

    def inject_news(self, symbol: str, title: str, keywords: list[str] = None):
        """Inject fake news item for keyword alert testing."""
        ...

    async def get_quote(self, symbol: str) -> StockQuote:
        price, change = self._prices.get(symbol, (100.0, 0.0))
        return StockQuote(symbol=symbol, name=f"Mock-{symbol}",
                          price=price, change_pct=change,
                          volume=1000000, timestamp=datetime.now())
```

**Key insight from cross-project analysis**: All 6 successful A-share monitoring projects use this DataProvider abstraction pattern. The abstraction enables:
1. Testing without network via MockProvider
2. Swapping data sources when APIs break (critical given AKShare instability)
3. `--test` CLI mode runs the complete pipeline (monitoring → alert → push) without network
4. Gradual migration between data providers

**Test strategy**:
- Unit tests use MockProvider exclusively
- Integration tests: `conftest.py` fixture provides MockProvider by default
- Optional `--live` pytest marker for AKShare integration tests (CI skips these)

---

## Similar Projects (Archive)

| Project | Relevance | Key Takeaway |
|---------|-----------|--------------|
| [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | High | LLM-driven multi-market analysis with AKShare fallback, multi-channel push, GitHub Actions scheduling. Modular data providers with fallback chain. |
| [stock-scanner](https://github.com/DR-lin-eng/stock-scanner) | Medium | AI-enhanced A-share analysis, 25 financial indicators, news sentiment. Good indicator calculation structure. |
| [aiagents-stock](https://github.com/oficcejo/aiagents-stock) | Medium | Multi-agent monitoring with real-time alerts. Shows alert engine patterns. |

**Cross-project pattern**: All use DataProvider abstraction with fallback sources.

---

## PushPlus API (Archive)

- POST `http://www.pushplus.plus/send` with JSON (token, title, content, template, channel)
- **200 messages/day** free tier; exceeding 400 attempts = 2-day account ban
- Safety threshold: 180 messages/day (not 200)
- Track daily count in DB, reset at midnight Beijing time
- `code: 200` = server received, NOT delivered to WeChat

---

## Trading Calendar (Archive)

- Use `chinese-calendar` package (supports through 2026)
- Trading hours: 9:30–11:30, 13:00–15:00 Beijing time
- **Pitfall**: Saturday 补班 (make-up workdays) are NOT trading days
- Pin package version, check for updates annually

---

## Recommended Focus Areas for First Build Cycle

### Priority 1: Project Scaffold + DataProvider Interface
- Create project structure (directory layout above)
- Define `DataProvider` ABC with `StockQuote`, `NewsItem`, `FinancialSummary` dataclasses
- Implement `MockProvider` with `set_price()`, `inject_news()` methods
- Basic `conftest.py` with MockProvider fixture

### Priority 2: Database Layer
- SQLite schema (5 tables) with aiosqlite
- WAL mode + PRAGMA configuration
- DB initialization on app startup (lifespan)
- FastAPI dependency injection for DB connections

### Priority 3: AKShare THS Provider (Skeleton)
- Implement `AKShareTHSProvider` with rate limiting
- Use `asyncio.to_thread()` for sync AKShare calls
- Token-bucket or simple sleep-based rate limiter
- Exponential backoff on errors

### What to Defer
- SSE streaming (Phase 4)
- Web UI templates (Phase 4)
- APScheduler jobs (Phase 3 — needs alert engine first)
- Docker packaging (Phase 5)
- Industry sector monitoring (nice-to-have)

---

## Key Risks for Builder

1. **AKShare asyncio conflict** — Must use `asyncio.to_thread()` wrapping; direct calls will block FastAPI's event loop or raise "cannot call asyncio.run() from running event loop"
2. **AKShare API instability** — Some East Money endpoints broken since Feb 2026. THS endpoints still working but may change. DataProvider abstraction is critical insurance.
3. **Rate limiting from day 1** — No published limits; opaque blocking. Build rate limiter into provider, not as afterthought.
4. **PushPlus daily cap** — Hard-code 180 limit with DB-tracked counter. Going over 400 attempts = 2-day ban.

---

## References

- [AKShare GitHub](https://github.com/akfamily/akshare)
- [AKShare Docs v1.18.64](https://akshare.akfamily.xyz/data/stock/stock.html)
- [AKShare Issue #7051 — Broken endpoints](https://github.com/akfamily/akshare/issues/7051)
- [AKShare Issue #6990 — Rate limiting](https://github.com/akfamily/akshare/issues/6990)
- [FastAPI + HTMX Guide (Blake Crosley)](https://blakecrosley.com/guides/fastapi-htmx)
- [Production FastAPI + HTMX (Medium)](https://medium.com/@sylvesterranjithfrancis/complete-guide-building-production-ready-web-apps-with-fastapi-and-htmx-from-setup-to-deployment-3010b1c8ff5c)
- [FastAPI + HTMX (TestDriven.io)](https://testdriven.io/courses/fastapi-htmx/fastapi-setup/)
- [APScheduler + FastAPI (Sentry)](https://sentry.io/answers/schedule-tasks-with-fastapi/)
- [APScheduler Multi-Worker Discussion](https://github.com/agronholm/apscheduler/discussions/1088)
- [aiosqlitepool](https://github.com/slaily/aiosqlitepool)
- [FastAPI Async DB Connections](https://oneuptime.com/blog/post/2026-02-02-fastapi-async-database/view)
- [SQLite WAL Tutorial 2026](https://tech-insider.org/sqlite-python-tutorial-fts5-wal-mode-2026/)
- [PushPlus API Docs](https://www.pushplus.plus/doc/guide/api.html)
- [PushPlus Rate Limits](https://www.pushplus.plus/doc/help/limit.html)
- [chinesecalendar PyPI](https://pypi.org/project/chinesecalendar/)
- [pytest External API Testing](https://pytest-with-eric.com/api-testing/pytest-external-api-testing/)
