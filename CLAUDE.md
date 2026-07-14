# A股智能监控系统 (A-Share Stock Monitor)

## Project Overview

Personal A-share stock monitoring tool. Collects real-time quotes/news via AKShare (THS interfaces), triggers alerts on price targets and news keywords, pushes to WeChat via PushPlus. AI-powered analysis via DeepSeek. Vue 3 mobile-first web UI.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, APScheduler, aiosqlite (SQLite with WAL mode)
- **Data:** AKShare (THS interfaces only — not East Money)
- **AI:** DeepSeek API (OpenAI-compatible SDK, base_url=https://api.deepseek.com)
- **Push:** PushPlus API (180/day safe limit)
- **Frontend:** Vue 3 + Vite + Vant 4 (mobile-first SPA in `frontend/`)
- **Deployment:** Docker (single uvicorn worker — APScheduler constraint)

## Project Structure

```
src/app/          — Application source code
src/app/services/ — Business logic (alerting, AI, screening, push)
src/app/routers/  — FastAPI API endpoints
src/app/providers/— Data providers (AKShare, mock)
tests/            — Test suite
frontend/         — Vue 3 + Vant 4 SPA
eval/             — Eval harness (do not modify)
.factory/         — Factory config (do not modify)
```

## Dev Commands

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/

# Smoke test
uv run python -c "from app.main import create_app; print('OK')"

# Run eval
python3 eval/score.py
```

## Conventions

- Use `src/` layout with `app` package
- All tests use MockProvider — no network calls in CI
- AKShare calls must use `asyncio.to_thread()` (AKShare is synchronous internally)
- Rate limit AKShare: minimum 2-3s between requests
- PushPlus daily cap: track in DB, hard stop at 180
- SQLite: WAL mode, busy_timeout=5000
- Single uvicorn worker only (APScheduler runs per-worker)
