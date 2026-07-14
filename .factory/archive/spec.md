---
tags:
  - factory
  - project
  - spec
source: factory-archivist
date: 2026-07-14
---

# Factory: spec (A股智能监控系统)

## Status
- **State**: Phase 2 complete (Data Collection Layer)
- **Current Score**: 0.493 (post-Phase 2 eval)
- **Experiments Run**: 2
- **Kept**: 2, **Reverted**: 0

## Project Summary
Personal A-share stock monitoring tool. Auto-collects real-time quotes and news via AKShare, pushes WeChat alerts via PushPlus when price targets or news keywords are hit. Web UI for watchlist and alert management.

Stack: Python + FastAPI + AKShare (THS) + SQLite + HTMX/SSE + APScheduler + Docker.

## Strategy (Approved 2026-07-14)
CEO approved 2-hypothesis plan with priority ordering H1 → H2:
- **H1:** Project scaffold — app factory, config, models, MockProvider, structlog, tests
- **H2:** Data layer — AKShare THS provider, rate limiter, aiosqlite DB with 5-table schema

5 backlog items queued for future cycles: monitoring engine, PushPlus client, REST API, web UI, Docker deployment.

## Research Findings (2026-07-14)
- **AKShare API instability**: East Money `push2*` endpoints broken since Feb 2026 (akfamily/akshare#7051). THS endpoints still working. DataProvider abstraction is critical insurance.
- **asyncio compatibility**: AKShare uses sync `requests` internally — must wrap with `asyncio.to_thread()` in FastAPI async context.
- **aiosqlite required**: Standard `sqlite3` blocks event loop. Use `aiosqlite` with WAL mode + busy_timeout.
- **HTMX patterns**: Route duality (full page vs fragment via HX-Request header), OOB swaps, underscore prefix convention for partials.
- **APScheduler**: Single worker constraint, lifespan pattern, trading hours double-gate with `chinese-calendar`.
- **PushPlus**: 200 msgs/day free tier, 400 attempts = 2-day ban — use 180 safety cap.
- **Cross-project validation**: All 6 similar projects use DataProvider abstraction with fallback sources.
- **Rate limiting**: No published limits from AKShare; 2-3s between requests, exponential backoff on errors.

## CEO Verdicts
- **Research:** PROCEED — Research covers all critical implementation areas.
- **Strategy:** PROCEED — 2 hypotheses approved, well-scoped with growth dimension tags.

## Source Notes
- [AKShare THS API](sources/akshare-ths-api.md) — API instability, rate limiting, asyncio compatibility
- [SQLite Schema](sources/sqlite-schema.md) — 5-table design, aiosqlite async access, WAL mode
- [FastAPI + HTMX/SSE](sources/fastapi-htmx-sse.md) — Route duality, OOB swaps, project structure
- [APScheduler Integration](sources/apscheduler-integration.md) — Lifespan pattern, single worker constraint
- [MockProvider Pattern](sources/mock-provider-pattern.md) — DataProvider ABC, testing strategy
- [PushPlus API](sources/pushplus-api.md) — Rate limits, safety threshold
- [Similar Projects](sources/similar-projects.md) — 6 projects analyzed, cross-project patterns
- [Trading Calendar](sources/trading-calendar.md) — chinese-calendar, 补班 pitfalls

## Key Risks
1. AKShare API instability — East Money endpoints breaking, THS anti-crawling
2. PushPlus account ban from exceeding attempt threshold
3. AKShare asyncio conflict if not properly wrapped
4. Rate limiting opacity — no published limits, opaque blocking

## Recent Experiments
- Experiment 002 — Data Collection Layer (KEEP). DataProvider ABC, AKShareTHSProvider, MockProvider, rate limiter. 23 tests passing.
- Experiment 001 — Project scaffold (KEEP, +0.387). PR #2. Builder delivered H1 scope (app factory, config, models, MockProvider, structlog, logging middleware) plus bonus H2 work (AKShareTHSProvider, RateLimiter). 23 tests, ruff/mypy clean.

## Builder Notes (Experiment #1)
- AKShare calls wrapped with `asyncio.to_thread()` + retry (3 attempts, exponential backoff)
- Rate limiter: async-safe with `asyncio.Lock`, 3s default interval
- MockProvider: controllable prices, injectable news, financials, stock search
- CLI `--test --dry-run` mode for eval mock_mode compatibility
- Structured JSON logging middleware on all HTTP requests

## Timeline
- 2026-07-14: Research completed — 8 source notes archived
- 2026-07-14: CEO verdict on research: PROCEED
- 2026-07-14: Strategy approved — H1 (scaffold) → H2 (data layer)
- 2026-07-14: Phase 1 build complete — scaffold KEEP, score 0.413 → 0.8
- 2026-07-14: CEO verdict on build: PROCEED to Phase 2
- 2026-07-14: Builder implementation archived — PR #2, 23 tests, bonus H2 work included
- 2026-07-14: Phase 2 build complete — Data Collection Layer (DataProvider ABC, AKShareTHSProvider, MockProvider, rate limiter), 23 tests
