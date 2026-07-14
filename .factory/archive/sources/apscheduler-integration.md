---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# APScheduler + FastAPI Integration

## Setup Pattern

- Use `AsyncIOScheduler` with FastAPI's `lifespan` context manager
- Set timezone to "Asia/Shanghai"
- Define jobs with cron expressions for trading hours

## Critical Considerations

1. **Single worker only** — scheduler runs in EACH uvicorn worker. For personal tool, single worker is fine. Document this constraint.
2. **Error handling** — wrap every job in try/except; unhandled exceptions kill the scheduler.
3. **Job persistence** — default MemoryJobStore loses jobs on restart. For cron-based jobs defined in code, this is acceptable.
4. **Trading hours** — use cron expressions to restrict to 9:30-11:30 and 13:00-15:00 Beijing time. Add `is_trading_day()` as a second gate inside the job.

## Sources

- Sentry: APScheduler + FastAPI
- Medium: FastAPI Scheduling Guide (BackgroundTasks vs APScheduler vs Celery)
