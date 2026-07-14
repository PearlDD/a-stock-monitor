---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# FastAPI + Jinja2 + HTMX/SSE Architecture

## SSE Real-Time Updates Pattern

- Use `sse-starlette` package for SSE support
- Stream rendered HTML fragments, not JSON (server-side rendering)
- Include `Vary: HX-Request` header for CDN/proxy compatibility
- Dual-response pattern: same route returns full page or fragment based on `HX-Request` header
- Self-host htmx.min.js (~14KB gzipped) — no CDN dependency
- Performance: expect sub-50ms partial updates
- HTMX auto-reconnects SSE on connection drops; add visual "disconnected" indicator

## Key Dependencies

- fastapi, uvicorn[standard], jinja2, sse-starlette, python-multipart

## Key Patterns

1. **Route duality** — Same route returns full page OR fragment based on `HX-Request` header
2. **Underscore prefix convention** — Components use `_` prefix (`_stock_card.html`) to distinguish fragments from pages
3. **OOB swaps** — Single response updates multiple DOM elements (quote table + alert badge)
4. **Jinja2 globals** — Register translation, CSRF, asset URL functions as globals

## Project Structure

Recommended layout: `src/app/` with subdirectories for providers/, engine/, push/, routes/, templates/ (components/ + pages/).

## Sources

- Blake Crosley FastAPI + HTMX Guide
- Medium/CodeX: Real-Time Dashboards with FastAPI + HTMX
- TestDriven.io: FastAPI + HTMX
