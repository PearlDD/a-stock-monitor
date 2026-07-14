## Strategy — 2026-07-14

### Observations
- Current composite score: 0.413
- Weakest eval dimensions: observability (0.0), capability_surface (0.04), research_grounding (0.32)
- Last 3 experiments: none — greenfield project with zero source code
- Pattern: Project has only `factory.md` and `eval/score.py`. No `src/`, no `tests/`, no `pyproject.toml`. Everything must be built from scratch.
- Backlog contains 5 items but all are human-action/operational items (token setup, server provisioning, stability verification) — none are code-implementable this cycle.
- CEO directive: scaffold first, then data layer. Must include MockProvider, rate limiting from day 1, structlog.
- Research report validated: FastAPI+HTMX patterns, AKShare THS interfaces, aiosqlite for async SQLite, APScheduler lifespan pattern, MockProvider abstraction.
- Guard patterns eval has 2 failures (templates/static glob patterns) — will resolve once real template/static files exist.

### Design Space
| Dimension | Score | Notes |
|---|---|---|
| Features | 0 | No code exists |
| Bug fixes | 0 | Nothing to fix yet |
| Instrumentation | 0 | No logging at all |
| Flow changes | 0 | No architecture to refactor |
| New agents | N/A | Not applicable to this project |
| Prompt engineering | N/A | Not applicable |
| Eval improvements | 1 | eval/score.py exists, config_parser scores 1.0 |
| Knowledge management | 1 | Research report complete, archive sources exist |
| Infrastructure | 0 | No Docker, no CI |
| Operational execution | 0 | Nothing to run |
| Self-evolution | N/A | Not a factory project |

**Underserved:** Features, Instrumentation, Infrastructure (all at 0 — but Features is the prerequisite for everything else)

### Hypotheses

#### H1: Project scaffold with app factory, config, data models, and structured logging
- **Category:** EXPLORE
- **Type:** code
- **New:** First build — no backlog items are code-implementable
- **Growth dimension:** capability_surface, observability
- **What:** Create the complete project scaffold: `pyproject.toml` with all dependencies, `src/app/` package with app factory (`create_app`), Pydantic Settings config, data models (StockQuote, NewsItem, StockInfo, FinancialSummary dataclasses), DataProvider ABC, MockProvider with `set_price()`/`inject_news()`, structured logging via structlog, `.env.example`, `CLAUDE.md`, and basic tests (`conftest.py` with MockProvider fixture, smoke test, provider tests).
- **Scope:**
  - `pyproject.toml` — Python 3.11+, deps: fastapi, uvicorn[standard], jinja2, sse-starlette, python-multipart, akshare, apscheduler, aiosqlite, python-dotenv, chinese-calendar, httpx, structlog. Dev: pytest, pytest-asyncio, pytest-cov, ruff, mypy
  - `src/app/__init__.py` — package init
  - `src/app/main.py` — `create_app()` FastAPI factory with structlog middleware
  - `src/app/config.py` — Pydantic Settings loading from `.env` (PUSHPLUS_TOKEN, DATABASE_PATH, LOG_LEVEL, etc.)
  - `src/app/models/market.py` — StockQuote, NewsItem, FinancialSummary, StockInfo dataclasses
  - `src/app/providers/base.py` — DataProvider ABC (get_quote, get_news, get_financials, search_stocks)
  - `src/app/providers/mock.py` — MockProvider with set_price(), inject_news()
  - `src/app/logging.py` — structlog configuration (JSON output, request context)
  - `.env.example` — all env vars with comments
  - `CLAUDE.md` — project conventions, dev commands, architecture
  - `tests/__init__.py`, `tests/conftest.py` — MockProvider fixture, async test setup
  - `tests/test_smoke.py` — import test, create_app test
  - `tests/test_providers.py` — MockProvider set_price/inject_news/get_quote/get_news tests
- **Why:** Nothing can be built or evaluated without the scaffold. Smoke test (`from app.main import create_app`) is the eval gate. Structlog from day 1 establishes observability baseline. MockProvider enables all future testing without network calls. Research report validates this exact structure across 6 similar projects.
- **Expected impact:** capability_surface 0.04→0.15 (modules+public_fns increase), observability 0.0→0.3 (structlog configured, function coverage starts), tests 0.5→0.8 (real test suite detected and passing), lint 0.5→0.8 (ruff configured), smoke_test passes
- **Priority:** high

#### H2: Data collection layer — AKShare THS provider, rate limiter, and database schema
- **Category:** EXPLORE
- **Type:** code
- **New:** Builds on H1 scaffold
- **Growth dimension:** capability_surface
- **What:** Implement the AKShare THS data provider with async wrapping and rate limiting, SQLite database layer with aiosqlite and WAL mode, and the 5-table schema (stocks, alert_rules, price_snapshots, push_history, news_cache). Includes rate limiter, exponential backoff, and database initialization in app lifespan.
- **Scope:**
  - `src/app/providers/akshare_ths.py` — AKShareTHSProvider implementing DataProvider ABC
    - `asyncio.to_thread()` wrapping for all sync AKShare calls
    - Uses THS interfaces: `stock_board_industry_name_ths()`, `stock_financial_abstract_ths()`
    - News via `stock_news_em()` (documented as East Money but only available source)
    - Structured logging for all requests with timestamps
  - `src/app/providers/rate_limiter.py` — Async-compatible rate limiter
    - Configurable min interval per source (default 3s)
    - asyncio.Lock-based concurrency safety
    - Exponential backoff on HTTP errors (401, 403, 429, 5xx)
  - `src/app/database.py` — Database layer
    - aiosqlite connection with WAL mode, PRAGMA tuning (synchronous=NORMAL, cache_size=10000, busy_timeout=5000)
    - Schema creation for 5 tables with indexes
    - FastAPI dependency injection (`get_db`)
    - DB init in app lifespan
  - `tests/test_rate_limiter.py` — Rate limiter timing and backoff tests
  - `tests/test_database.py` — Schema creation, CRUD operations, WAL mode verification
  - `tests/test_akshare_provider.py` — AKShare provider with mocked `ak` module (no network)
- **Why:** Data layer is the foundation for the monitoring engine. Rate limiting from day 1 prevents AKShare bans (research found opaque anti-crawling with 401 responses). aiosqlite prevents event loop blocking. WAL mode enables concurrent read/write for scheduler + web UI. All 6 reference projects use this DataProvider abstraction pattern.
- **Expected impact:** capability_surface 0.15→0.35 (significant new modules, public functions, entry points), observability 0.3→0.5 (logging in provider and DB layers), tests dimension improves (new test files), research_grounding improves (implementing researched patterns with citations)
- **Priority:** high

### Anti-patterns to Avoid
- Do not call East Money `stock_zh_a_hist()` or `stock_individual_info_em()` — broken since Feb 2026 (AKShare issue #7051)
- Do not call AKShare synchronously in async context — must use `asyncio.to_thread()` to avoid event loop blocking
- Do not skip rate limiting — AKShare has opaque anti-crawling that changes without notice
- Do not use standard `sqlite3` in async FastAPI — must use `aiosqlite` to prevent event loop blocking
- Do not hardcode any tokens or API keys — use environment variables per project guards

## New Backlog Items

- Monitoring engine: alert evaluation (price_above/below, change_pct, news_keyword), cooldown-based dedup, trading hours gate via chinese-calendar, APScheduler integration with lifespan pattern
- PushPlus notification client: POST to pushplus.plus/send, daily count tracking in DB (180/day cap), push history logging, --test CLI mode for end-to-end validation
- REST API endpoints: stock watchlist CRUD, alert rule CRUD, push history (paginated), test-push endpoint
- Web management UI: HTMX + Jinja2 dashboard with SSE real-time quotes, watchlist management, alert rule forms, push history view
- Docker deployment: multi-stage Dockerfile, docker-compose with SQLite volume persistence, /health endpoint, daily heartbeat push, restart policy
