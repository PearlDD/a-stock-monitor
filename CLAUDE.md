# A股智能监控系统 (A-Share Stock Monitor)

## Project Overview

Personal A-share stock monitoring tool. Collects real-time quotes via Tencent Finance API, triggers alerts on price targets and volume spikes, pushes notifications to WeChat via PushPlus. Vue 3 mobile-first web UI deployed on Netlify with Supabase (PostgreSQL) backend.

## Tech Stack

- **Frontend:** Vue 3 + Vite + Vant 4 (mobile-first SPA)
- **Backend:** Netlify Functions (Node.js serverless)
- **Database:** Supabase (PostgreSQL)
- **Data:** Tencent Finance API (qt.gtimg.cn)
- **Push:** PushPlus API (180/day safe limit)
- **Hosting:** Netlify (static + functions)

## Project Structure

```
src/              — Vue 3 frontend source
src/api/          — API client (axios)
src/views/        — Vue page components
index.html        — SPA entry point
vite.config.js    — Vite config
netlify/functions/ — Netlify serverless functions
netlify/functions/shared/ — Shared utilities (Supabase client, Tencent parser, etc.)
supabase/migrations/ — Database migrations
public/           — Static assets
eval/             — Eval harness (do not modify)
.factory/         — Factory config (do not modify)
```

## Dev Commands

```bash
# Install dependencies
npm install

# Run frontend dev server
npm run dev

# Run Netlify dev (functions + frontend)
npx netlify dev

# Build for production
npm run build
```

## Conventions

- Netlify Functions use ES modules (type: module)
- All API functions handle CORS via shared helpers
- Tencent Finance API for real-time quotes (NOT AKShare)
- PushPlus daily cap: track in Supabase, hard stop at 180
- Trading hours: 9:30-11:30, 13:00-15:00 Asia/Shanghai
- Red=up, Green=down (Chinese market convention)
- System fonts only, no Google Fonts
- Alert messages: 3-4 lines, elderly-friendly, with disclaimer
- Edge trigger logic: price_target = one-shot, limit_up/down/volume_spike = daily reset
