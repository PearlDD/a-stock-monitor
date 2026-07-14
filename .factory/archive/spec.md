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
- **State**: Research Complete → Strategy Phase
- **Current Score**: Not yet evaluated
- **Experiments Run**: 0
- **Kept**: 0, **Reverted**: 0

## Project Summary
Personal A-share stock monitoring tool. Auto-collects real-time quotes and news via AKShare, pushes WeChat alerts via PushPlus when price targets or news keywords are hit. Web UI for watchlist and alert management.

Stack: Python + FastAPI + AKShare (THS) + SQLite + HTMX/SSE + APScheduler + Docker.

Phase 1 (PushPlus push) is complete. Starting Phase 2 (data collection layer).

## Research Findings (2026-07-14)
- 6 similar projects analyzed; all use DataProvider abstraction with fallback sources
- AKShare THS has no published rate limits; 401 anti-crawling added in 2026 — rate limiting from day 1 is critical
- PushPlus free tier: 200 msgs/day, 400 attempts = 2-day ban — use 180 cap
- SQLite with WAL mode for concurrent access
- Trading calendar via `chinese-calendar` package
- HTMX + SSE for real-time dashboard updates

## Key Risks
1. AKShare rate limiting (opaque, changes without notice)
2. PushPlus account ban from exceeding attempt threshold
3. 2026 China Cybersecurity Law tightens scraping rules
