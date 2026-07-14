---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# Similar A-Share Monitoring Projects

## Key Projects Analyzed

| Project | Relevance | Key Takeaway |
|---------|-----------|--------------|
| daily_stock_analysis (ZhuLinsen) | High | LLM-driven multi-market analysis with AKShare fallback, multi-channel push (WeChat Work/Telegram/Slack), GitHub Actions scheduling. Modular data providers with fallback chain. |
| stock-scanner (DR-lin-eng) | Medium | AI-enhanced A-share analysis, 25 financial indicators, news sentiment. Good indicator calculation structure. |
| aiagents-stock (oficcejo) | Medium | Multi-agent monitoring with real-time alerts. Shows alert engine patterns. |
| pythonstock/stock | Medium | Full-stack Python stock system with Docker + MySQL. Good Docker packaging reference. |
| adata (1nchaos) | Low-Med | Multi-source data fusion with dynamic proxy. Resilient data fetching patterns. |
| Ashare (mpquant) | Low | Minimal real-time data wrapper. Simplest possible quote fetching. |

## Cross-Project Pattern

All successful projects use a **DataProvider abstraction layer with fallback sources**. This validates the spec's MockProvider + AKShare provider design.
