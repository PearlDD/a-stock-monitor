# Researcher Agent Output

- **timestamp:** 2026-07-14T16:06:07Z
- **exit_code:** 0

---

Discovery complete. Here's what was produced:

### Outputs

1. **`.factory/strategy/research.md`** — Comprehensive research report covering:
   - 6 similar open-source projects analyzed (daily_stock_analysis, stock-scanner, etc.)
   - AKShare THS API usage patterns with specific function calls verified
   - Rate limiting strategy (no official limits published; recommend 2-3s between requests, cache aggressively)
   - FastAPI + HTMX + SSE real-time dashboard pattern with code examples
   - APScheduler integration (AsyncIOScheduler + lifespan, single-worker constraint)
   - PushPlus API spec (200/day limit, **hard stop at 180** to avoid 2-day ban at 400 attempts)
   - SQLite schema design (5 tables: stocks, alert_rules, price_snapshots, push_history, news_cache)
   - Trading calendar approach (`chinese-calendar` package, handles 补班 correctly)
   - Mock/test provider pattern (ABC + controllable MockProvider)
   - 8 pitfalls with mitigations
   - MVP scope recommendation aligned with Phases 2-3

2. **`.factory/eval_profile.json`** — 6 eval dimensions:
   - Tests (0.40) — pytest
   - Type check (0.15) — mypy
   - Lint (0.15) — ruff
   - Import check (0.10) — app imports cleanly
   - Mock mode (0.15) — `--test` mode starts
   - Docker build (0.05) — container builds

3. **`eval/score.py`** — Standalone scoring script outputting JSON with weighted overall score

### Key Findings

- **AKShare risk**: No published rate limits, anti-crawling tightened in 2026. Must build defensive rate limiting from day 1.
- **PushPlus trap**: Going over 400 attempts (not just 200) triggers a 2-day account ban — critical to track daily count in DB.
- **Architecture validated**: The DataProvider abstraction + MockProvider pattern is used by every successful similar project.
- **HTMX+SSE proven**: Sub-50ms partial updates, ~14KB JS footprint, well-documented pattern with `sse-starlette`.
