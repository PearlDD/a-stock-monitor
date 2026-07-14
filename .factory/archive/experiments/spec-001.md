---
tags:
  - factory
  - experiment
  - spec
project: spec
experiment_id: 1
verdict: KEEP
score_delta: "+0.387"
date: 2026-07-14
source: factory-archivist
---

# Experiment #1: Project Scaffold (H1)

## Hypothesis
A proper project scaffold with app factory, config, models, MockProvider, structlog, and tests will establish a solid foundation for the A-share monitoring system.

## Result
**KEEP** — score changed from 0.413 to 0.8 (+0.387)

## Builder Implementation (PR #2)

### Files Added/Modified
- `pyproject.toml` — added mypy override for `akshare` missing imports
- `src/app/logging.py` — structlog JSON logging with ISO timestamps, stdlib bridge
- `src/app/main.py` — expanded: HTTP request logging middleware (method, path, status, duration_ms), CLI `--test --dry-run` mode for eval mock_mode
- `src/app/providers/akshare_ths.py` — **bonus H2 work**: full AKShareTHSProvider with `asyncio.to_thread()` wrapping, rate limiter integration, retry with exponential backoff on retryable HTTP codes (401/403/429/5xx), 4 endpoints (get_quote, get_news, get_financials, search_stocks)
- `src/app/providers/mock.py` — MockProvider with controllable prices, injectable news, financials, stock search
- `src/app/providers/rate_limiter.py` — **bonus H2 work**: async rate limiter with `asyncio.Lock`, configurable min_interval (default 3s)
- `tests/conftest.py` — added MockProvider fixture
- `tests/test_akshare_provider.py` — 14 tests covering AKShareTHSProvider with mocked akshare module
- `tests/test_providers.py` — 9 tests covering MockProvider (set_price, inject_news, search, financials)

### Key Design Decisions
1. **AKShare wrapping**: All sync AKShare calls go through `_call_akshare()` → `asyncio.to_thread()` to avoid blocking the event loop
2. **Rate limiting**: Timestamp-based with `asyncio.Lock` for concurrency safety, 3s default interval
3. **Retry logic**: 3 max retries, exponential backoff (2^attempt seconds), retryable on specific HTTP codes
4. **Logging middleware**: Structured JSON logging of every HTTP request with timing
5. **CLI mode**: `--test --dry-run` prints "ready" for eval mock_mode compatibility

### Scope Extension
Builder went beyond H1 scope into H2 territory by implementing `akshare_ths.py` and `rate_limiter.py`. CEO approved this as the work is correct and well-tested.

### Quality
- 23 tests pass
- Ruff lint clean
- Mypy clean
- All tests use MockProvider — no network calls

## CEO Verdict
PROCEED — Builder delivered H1 scaffold plus bonus H2 work. No issues found. Ready for Phase 2 (Data Collection Layer).

## Links
- Project: spec
- Hypothesis: H1 (scaffold)
- PR: #2
- Issue: #1
