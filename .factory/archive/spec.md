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
- **State**: Cycle 1 complete — scaffold + data layer shipped
- **Current Score**: 0.611
- **Experiments Run**: 2
- **Kept**: 1, **Reverted**: 1
- **Keep Rate**: 50%
- **Net Score Delta**: +0.118 (from 0.493 baseline)

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
- **Experiment #002:** KEEP — score +0.118 (0.493 → 0.611), combined H1+H2 delivery.

## Score History
| Experiment | Hypothesis | Verdict | Score Before | Score After | Delta |
|---|---|---|---|---|---|
| 001 | Project scaffold (H1) | REVERT | — | — | — |
| 002 | Combined H1+H2 scaffold + data layer | KEEP | 0.493 | 0.611 | +0.118 |

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
- Experiment 002 — Combined H1+H2 scaffold + data layer (KEEP, +0.118). Score 0.493 → 0.611. DataProvider ABC, AKShareTHSProvider, MockProvider, rate limiter, app factory, config, models, structlog. 23 tests passing.
- Experiment 001 — Project scaffold (REVERT). Precheck gate false negative on score_direction overrode CEO keep decision.

## Cycle Summary
- [Full cycle summary](cycle-summary-2026-07-14.md)

## Timeline
- 2026-07-14: Research completed — 8 source notes archived
- 2026-07-14: CEO verdict on research: PROCEED
- 2026-07-14: Strategy approved — H1 (scaffold) → H2 (data layer)
- 2026-07-14: Experiment 001 — scaffold attempt, REVERTED (precheck gate override)
- 2026-07-14: Experiment 002 — combined H1+H2, KEPT (+0.118, score 0.493 → 0.611)
- 2026-07-14: Cycle 1 archived
