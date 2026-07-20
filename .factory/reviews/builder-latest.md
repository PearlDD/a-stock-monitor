# Builder Review — Netlify + Supabase Migration

## Summary

Major architecture refactor: converted from FastAPI + SQLite + APScheduler to Netlify Functions + Supabase (PostgreSQL) + Netlify Scheduled Functions.

## Changes Made

### Removed
- All Python backend code (src/app/, tests/, pyproject.toml, uv.lock)
- FastAPI, uvicorn, APScheduler, AKShare, aiosqlite dependencies
- SQLite database files and config

### Restructured
- Moved Vue frontend from `frontend/` to root level (`src/`, `index.html`, `vite.config.js`)
- Created root `package.json` with Vue + Supabase + Netlify dependencies

### Created — Netlify Functions (API)
- `watchlist.js` — CRUD for stock watchlist via Supabase
- `alerts.js` — CRUD for alert rules via Supabase
- `quotes.js` — Real-time quotes via Tencent Finance API (qt.gtimg.cn)
- `stock-info.js` — Stock info, financials, history, news, announcements
- `capital-flow.js` — Capital flow top stocks
- `settings.js` — Settings, test push, push quota
- `search.js` — Stock search via Tencent smartbox API

### Created — Netlify Scheduled Functions
- `poll-quotes.js` — Every 1 min during trading hours: evaluate alerts, send PushPlus
- `daily-digest.js` — 15:05 CST: daily watchlist summary
- `check-capital-flow.js` — Every 5 min during trading hours: alert on large moves
- `health-check.js` — 09:00 CST: verify Supabase connectivity, cleanup stale state

### Created — Shared Utilities
- `shared/supabase.js` — Supabase client singleton
- `shared/cors.js` — CORS headers and JSON response helpers
- `shared/tencent.js` — Tencent Finance API URL builder and response parser
- `shared/pushplus.js` — PushPlus notification sender with quota tracking
- `shared/trading-hours.js` — A-share trading hours checker

### Created — Infrastructure
- `netlify.toml` — Build config, function directory, API redirects, SPA fallback
- `supabase/migrations/001_init.sql` — Schema: watchlist, alert_rules, push_history, alert_state

### Updated
- `.env.example` — Supabase vars + PushPlus token
- `.gitignore` — Node.js patterns, .netlify/, legacy Python patterns
- `CLAUDE.md` — Updated for new architecture
- `vite.config.js` — Dev proxy targets Netlify CLI (port 8888)
- `src/views/Settings.vue` — Data source label changed to "腾讯财经"

## Verification
- Frontend builds successfully (`npm run build`)
- All functions use Netlify Functions v2 API with path-based routing
- Alert dedup via Supabase `alert_state` table
- Trading hours correctly converted to UTC cron expressions
