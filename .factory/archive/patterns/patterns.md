---
tags:
  - factory
  - patterns
source: factory-archivist
date: 2026-07-14
---

# Cross-Project Patterns

## DataProvider Abstraction Layer
Discovered in spec project research phase.
All successful A-share monitoring projects use a DataProvider abstraction with fallback sources. This pattern enables: (1) testing without network via MockProvider, (2) swapping data sources when APIs break, (3) gradual migration between data providers.
