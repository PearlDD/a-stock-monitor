---
tags:
  - factory
  - experiment
  - spec
project: spec
experiment_id: 002
verdict: KEEP
score_delta: pending
date: 2026-07-14
source: factory-archivist
---

# Experiment #002: Data Collection Layer (Phase 2)

## Hypothesis
Adding DataProvider ABC, AKShareTHSProvider, MockProvider, and rate limiter will establish the data collection layer needed for real-time quote/news retrieval.

## Result
**KEEP** — 23 tests passing, all components implemented.

## What Changed
- `models/market.py` — Data models (StockQuote, NewsItem, etc.)
- `providers/base.py` — DataProvider ABC defining provider interface
- `providers/akshare_ths.py` — AKShare THS provider with `asyncio.to_thread()` wrapping
- `providers/mock.py` — MockProvider for testing (no network calls)
- `providers/rate_limiter.py` — Rate limiter (2-3s between requests, exponential backoff)
- 23 tests covering all provider and model functionality

## Key Design Decisions
- DataProvider as ABC allows swapping providers when AKShare endpoints break
- AKShare sync calls wrapped in `asyncio.to_thread()` per project conventions
- Rate limiter enforces minimum delay between requests (AKShare has no published limits)
- MockProvider returns deterministic data for CI — no network dependency

## Links
- Project: spec
- Commit: f5b27de
