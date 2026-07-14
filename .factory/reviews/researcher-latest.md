# Researcher Agent Output

- **timestamp:** 2026-07-14T16:14:09Z
- **exit_code:** 0

---

Research report written to `.factory/strategy/research.md`. Key new findings from web research:

1. **AKShare API instability** — East Money `push2*` endpoints (including `stock_zh_a_hist`, `stock_individual_info_em`) are broken since Feb 2026. THS interfaces still work but the DataProvider abstraction is critical insurance.

2. **asyncio conflict** — AKShare uses synchronous `requests` internally. Must wrap all calls in `asyncio.to_thread()` to avoid blocking FastAPI's event loop.

3. **aiosqlite required** — Standard `sqlite3` blocks the event loop. Must use `aiosqlite` with WAL mode, busy_timeout, and FastAPI dependency injection.

4. **HTMX template patterns** — Underscore-prefixed partials (`_stock_card.html`), route duality (full page vs fragment based on `HX-Request` header), OOB swaps for multi-element updates.

5. **APScheduler lifespan** — Confirmed pattern using `AsyncIOScheduler` with FastAPI's `asynccontextmanager` lifespan. Single-worker constraint documented.
