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

## Design Decisions

- **WAL mode**: `PRAGMA journal_mode=WAL` for concurrent read/write (scheduler writes while web UI reads)
- **Price snapshot retention**: 30 days. 20 stocks × 240 min/day ≈ 4800 rows/day — negligible for SQLite
- **News dedup**: content_hash (MD5 of title+url)
- **No ORM overhead for reads**: raw SQL for dashboard queries, SQLAlchemy for schema management only
