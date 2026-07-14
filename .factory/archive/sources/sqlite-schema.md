---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# SQLite Schema Design

## Tables (5 total)

1. **stocks** — watchlist (symbol, name, industry, is_active)
2. **alert_rules** — per-stock rules (price_above/below, change_pct, news_keyword, cooldown)
3. **price_snapshots** — indexed by (stock_id, timestamp)
4. **push_history** — notification log with PushPlus serial numbers and status
5. **news_cache** — deduplicated by content_hash (MD5 of title+url)

## Async Access — aiosqlite (Required)

Standard `sqlite3` blocks the event loop. Must use `aiosqlite`:
```python
db = await aiosqlite.connect("stock_monitor.db")
await db.execute("PRAGMA journal_mode=WAL")
await db.execute("PRAGMA synchronous=NORMAL")
await db.execute("PRAGMA cache_size=10000")  # ~40MB cache
await db.execute("PRAGMA busy_timeout=5000")  # 5s busy timeout
```
Use FastAPI dependency injection: `async def route(db=Depends(get_db))`.

Sources: aiosqlitepool GitHub, FastAPI async DB guide (oneuptime.com), SQLite WAL Tutorial 2026

## Design Decisions

- **WAL mode**: `PRAGMA journal_mode=WAL` for concurrent read/write (scheduler writes while web UI reads)
- **busy_timeout**: 5000ms prevents immediate SQLITE_BUSY errors
- **Price snapshot retention**: 30 days. 20 stocks × 240 min/day ≈ 4800 rows/day — negligible for SQLite
- **News dedup**: content_hash (MD5 of title+url)
- **Raw SQL for reads**: no ORM overhead for dashboard queries
