---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# AKShare THS Interface — Usage & Rate Limiting

## API Instability Alert (Feb 2026)

As of February 2026, **East Money `push2*` API endpoints are broken**:
- `stock_zh_a_hist()` — BROKEN (connection abort)
- `stock_individual_info_em()` — BROKEN (connection abort)

**Still working**:
- `stock_zh_a_spot()` — Real-time A-share market data (5,483+ stocks)
- `stock_info_a_code_name()` — A-share stock code/name listing
- `stock_zh_a_spot_em()` — Works but has **asyncio event loop conflict** in async environments

References: akfamily/akshare#7051

## Verified Working THS Interfaces

- `ak.stock_board_industry_name_ths()` — Industry sector names
- `ak.stock_financial_abstract_ths(symbol, indicator)` — Financial abstracts
- `ak.stock_news_em(stock)` — Stock news (East Money, not THS)

## Critical: asyncio Compatibility

AKShare uses `requests` (synchronous) internally. In FastAPI async context, must use:
```python
result = await asyncio.to_thread(ak.stock_zh_a_spot_em)
```
Direct calls will block the event loop or raise "cannot call asyncio.run() from running event loop".

## Critical: Rate Limiting

- **No built-in rate limiting** in AKShare
- No official published rate limit numbers — thresholds are opaque
- THS added 401 anti-crawling in early 2026 for some endpoints
- Users report mysterious blocking with no clear recovery (akfamily/akshare#6990)
- **2026 legal context**: China's modified Cybersecurity Law (effective 2026-01-01) tightens scraping rules

## Recommended Strategy

- Minimum 2-3 seconds between requests to same source
- Batch queries where API supports it
- Cache: financial data 24h, news 5min, quotes 60s, industry sectors 1 week
- For 20 stocks: ~1 request every 3 seconds (safe)
- For 50+ stocks: batch or longer intervals
- Exponential backoff on HTTP errors (401, 403, 429, 5xx)
- Log all request timestamps for debugging
