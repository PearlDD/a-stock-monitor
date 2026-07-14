---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# AKShare THS Interface — Usage & Rate Limiting

## Verified Working Interfaces

- `ak.stock_board_industry_name_ths()` — Industry sector names
- `ak.stock_financial_abstract_ths(symbol, indicator)` — Financial abstracts
- `ak.stock_news_em(stock)` — Stock news (East Money, not THS)

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
