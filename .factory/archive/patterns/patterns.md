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

## Precheck Gate False Negatives
Discovered in spec experiment #001 (2026-07-14).
The finalize gate's score_direction precheck can produce false negatives, especially when scope_infra_issue is flagged. CEO keep decision was overridden despite +0.090 score improvement. Workaround: manual_pass override on retry. When a precheck fails but CEO confidence is high, re-submitting the same experiment with manual_pass is a valid recovery path.

## Hypothesis Combining for Efficiency
Discovered in spec experiments #001–#002 (2026-07-14).
When H1 is reverted due to infrastructure issues (not code quality), combining H1+H2 in the retry avoids duplicating scaffold work. This is valid when the hypotheses share infrastructure and the combined scope remains testable.
