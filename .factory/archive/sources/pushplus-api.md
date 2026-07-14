---
tags:
  - factory
  - source
  - spec
source: factory-archivist
date: 2026-07-14
---

# PushPlus API Integration

## API Endpoint

POST http://www.pushplus.plus/send with JSON body (token, title, content, template, channel).

## Rate Limits — Critical

- **200 messages/day** free tier
- Exceeding 200: messages silently dropped
- **Exceeding 400 attempts: account blocked for 2 days**
- Must track daily send count to avoid the 400-attempt ban

## Recommended Implementation

- Set safety threshold at **180** (not 200) to leave room for test pushes
- Store daily count in DB, reset at midnight Beijing time
- Log all push attempts with serial numbers
- `code: 200` means "server received it", NOT "delivered to WeChat" — query delivery status separately if needed

## Sources

- PushPlus API Docs: pushplus.plus/doc/guide/api.html
- PushPlus Rate Limits: pushplus.plus/doc/help/limit.html
