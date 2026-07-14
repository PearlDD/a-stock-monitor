# Builder Review — Test Reliability Fixes

## Status: COMPLETE

## Changes Made

### Test Fixes (Code Review Follow-up)

1. **`test_akshare_provider.py`**: Rewrote all mocks from `unittest.mock.patch` to `monkeypatch.setattr` for reliable async mocking. Previous approach was flaky with `asyncio.to_thread` — mocks sometimes didn't intercept the real akshare calls, causing network-dependent test failures.

2. **`test_routers.py`**: Rewrote `TestStockRouter` tests using `monkeypatch.setattr` on the `market_data` module directly (instead of `AsyncMock` with `patch`). Added 4 new endpoint tests:
   - `test_get_stock_info` — stock info endpoint with mocked data
   - `test_get_quotes_empty` — quotes endpoint
   - `test_analyze_no_key` — AI analyze endpoint (no API key)
   - `test_summarize_no_news` — AI summarize endpoint (no news)

3. **`test_volume_spike.py`**: Updated comment to match the fixed logic (volumes now recorded AFTER evaluation, so first eval has no history → avg is 0 → no trigger).

4. **Cache isolation**: Added `cache.clear()` in the `client` fixture to prevent cross-test cache pollution.

## Test Results
- **176 tests passed, 0 failed** (up from 173 with 3 failures)
- **Lint: All checks passed**
- **No network calls in any test**
