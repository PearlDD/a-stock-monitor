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
- **State**: Research complete, strategy pending
- **Current Score**: 0 (no source code yet)
- **Experiments Run**: 0
- **Kept**: 0, **Reverted**: 0

## Project Summary
Personal A-share stock monitoring tool. Auto-collects real-time quotes and news via AKShare, pushes WeChat alerts via PushPlus when price targets or news keywords are hit. Web UI for watchlist and alert management.

Stack: Python + FastAPI + AKShare (THS) + SQLite + HTMX/SSE + APScheduler + Docker.

## Research Findings (2026-07-14)
- **AKShare API instability**: East Money `push2*` endpoints broken since Feb 2026 (akfamily/akshare#7051). THS endpoints still working. DataProvider abstraction is critical insurance.
- **asyncio compatibility**: AKShare uses sync `requests` internally — must wrap with `asyncio.to_thread()` in FastAPI async context.
- **aiosqlite required**: Standard `sqlite3` blocks event loop. Use `aiosqlite` with WAL mode + busy_timeout.
- **HTMX patterns**: Route duality (full page vs fragment via HX-Request header), OOB swaps, underscore prefix convention for partials.
- **APScheduler**: Single worker constraint, lifespan pattern, trading hours double-gate with `chinese-calendar`.
- **PushPlus**: 200 msgs/day free tier, 400 attempts = 2-day ban — use 180 safety cap.
- **Cross-project validation**: All 6 similar projects use DataProvider abstraction with fallback sources.
- **Rate limiting**: No published limits from AKShare; 2-3s between requests, exponential backoff on errors.

## CEO Verdict on Research
- **PROCEED** — Research covers all critical implementation areas. Key findings on AKShare async conflict, aiosqlite requirement, and HTMX partial patterns are directly actionable.

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

## Recommended Build Priorities
1. Project scaffold + DataProvider ABC + MockProvider + basic tests
2. SQLite schema (5 tables) with aiosqlite + WAL mode
3. AKShare THS provider skeleton with rate limiting
4. Defer: SSE streaming, web UI templates, APScheduler jobs, Docker

## Timeline
- 2026-07-14: Research completed — 8 source notes archived
- 2026-07-14: CEO verdict: PROCEED to strategy
