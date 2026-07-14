---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# A-Share Trading Calendar & Hours

## Recommended Package

`chinese-calendar` (or `cn-stock-holidays`) — handles irregular Chinese holidays and "补班" (make-up workdays that are NOT trading days).

## Trading Hours

- Morning: 9:30–11:30 Beijing time
- Afternoon: 13:00–15:00 Beijing time
- Call auction: 9:15–9:25 (decide if monitoring this for MVP)

## Pitfalls

- Chinese holidays are irregular (Spring Festival, National Day dates change yearly)
- `chinese-calendar` package updates annually (supports through 2026) — pin version, check for updates
- Saturday/Sunday "补班" are NOT trading days despite being workdays
- Half-day sessions (e.g., typhoon warnings) are rare — not worth coding for MVP

## Sources

- chinesecalendar PyPI
- cn-stock-holidays PyPI
