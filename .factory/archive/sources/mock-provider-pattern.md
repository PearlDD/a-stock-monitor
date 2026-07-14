---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# Mock/Test Provider Pattern

## Design

Abstract `DataProvider` ABC with methods: `get_quote()`, `get_news()`, `get_financials()`, `search_stocks()`.

## MockProvider Features

- `set_price(symbol, price)` — manually set price for trigger testing
- `inject_news(symbol, title, keywords)` — inject fake news items
- `simulate_day(symbol)` — replay a full trading day

## Purpose

Enables `--test` CLI mode to run the complete pipeline (monitoring → alert evaluation → push notification) without any network calls. Essential for development and CI testing.

## Validation

The DataProvider abstraction pattern is validated across all 6 similar projects analyzed — all successful ones use a similar abstraction layer with fallback sources.
