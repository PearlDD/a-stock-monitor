---
tags:
  - factory
  - experiment
  - spec
project: spec
experiment_id: 002
verdict: KEEP
score_delta: "+0.118"
date: 2026-07-14
source: factory-archivist
---

# Experiment #002: Project Scaffold + Data Layer (Combined H1+H2)

## Hypothesis
Project scaffold + data layer (combined H1+H2). Adding DataProvider ABC, AKShareTHSProvider, MockProvider, and rate limiter alongside complete project scaffold will establish both the foundation and data collection layer.

## Result
**KEEP** — score changed from 0.493 to 0.611 (+0.118)

## What Changed
- `src/app/main.py` — FastAPI app factory with lifespan, HTTP logging middleware, CLI `--test --dry-run` mode
- `src/app/logging.py` — structlog JSON logging with ISO timestamps
- `src/app/providers/base.py` — DataProvider ABC defining provider interface
- `src/app/providers/akshare_ths.py` — AKShare THS provider with `asyncio.to_thread()` wrapping, retry with exponential backoff
- `src/app/providers/mock.py` — MockProvider for testing (no network calls)
- `src/app/providers/rate_limiter.py` — Rate limiter (3s default interval, async-safe with `asyncio.Lock`)
- `src/app/engine/alerts.py` — Alert engine module
- `src/app/engine/monitor.py` — Monitoring engine module
- `src/app/engine/news.py` — News engine module
- `src/app/engine/scheduler.py` — Scheduler module
- `src/app/push/pushplus.py` — PushPlus client
- `src/app/routes/api.py` — REST API routes
- `tests/test_alerts.py` — Alert tests
- 23 tests covering all provider and model functionality

## Key Design Decisions
- DataProvider as ABC allows swapping providers when AKShare endpoints break
- AKShare sync calls wrapped in `asyncio.to_thread()` per project conventions
- Rate limiter enforces minimum delay between requests (AKShare has no published limits)
- MockProvider returns deterministic data for CI — no network dependency
- CLI `--test --dry-run` mode for eval mock_mode compatibility

## Decision Rationale
Score improved +0.118 (0.493 → 0.611). Combined H1+H2 delivery: scaffold + data layer in single experiment. Builder delivered beyond original H1 scope into H2 territory. CEO approved keep — meaningful score improvement with solid test coverage. Experiment 001 (predecessor attempt at same scope) was reverted due to precheck gate false negative on score_direction.

## Links
- Project: spec
- Issue: #1
- PR: #2
