# Stock Monitor

A full-stack stock watchlist and price-alert web application for A-shares and selected U.S. equities. Users can sign up with email, search symbols such as `600519` or `AAPL`, create alert rules, and receive notifications when a rule is met. Market data may be delayed and is provided for informational purposes only; this project does not provide investment advice.

**Live demo:** [stockmonitor01.netlify.app](https://stockmonitor01.netlify.app/)

## Highlights

- Email/password authentication with Supabase Auth and session restoration.
- Per-user watchlists, alert rules, notification preferences, and delivery quotas protected by Row Level Security (RLS).
- A-share and U.S. stock search, quotes, and currency-aware price display.
- Target-price, limit-up, limit-down, and turnover alert types.
- One-time target-price alerts; daily de-duplication for the other alert types.
- Scheduled quote polling during the relevant market session, with request timeouts, retries, and malformed-price filtering.
- Browser alerts when PushPlus is not configured; optional PushPlus notifications for WeChat delivery.
- PushPlus tokens encrypted at rest with AES-256-GCM; server-only secrets never reach the browser.

## Architecture

```text
Vue 3 / Vant SPA ── Bearer JWT ──> Netlify Functions ── service role ──> Supabase PostgreSQL
       │                                      │
       └──────────── Supabase Auth ───────────┤
                                              ├── Tencent Finance quote endpoint
                                              └── PushPlus (per-user encrypted token)

Netlify Cron ──> poll-quotes ──> validate rules ──> atomic delivery claim ──> notify user
```

The `alert_deliveries` table has a unique constraint for each rule and trading day, preventing concurrent scheduled invocations from sending duplicate alerts. Delivery is at-least-once: an external provider failure after accepting a message but before the database update can still cause a rare duplicate notification.

## Tech Stack

| Area | Technology |
| --- | --- |
| Front end | Vue 3, Vite, Vant, Axios, Supabase JS |
| Serverless API | Node.js 22, Netlify Functions |
| Authentication and database | Supabase Auth, PostgreSQL, Row Level Security |
| Scheduler | Netlify Cron |
| Market data | Tencent Finance public quote endpoint (GBK responses) |
| Notifications | Browser banner and PushPlus |
| Tests | Node.js built-in test runner |

## Local Development

Prerequisites: Node.js 22+, a Supabase project, and the Netlify CLI.

```bash
git clone https://github.com/PearlDD/a-stock-monitor.git
cd a-stock-monitor
npm ci
cp .env.example .env

# Apply the SQL migrations using the Supabase CLI or SQL Editor.
npx supabase db push

# Run the SPA and Netlify Functions together.
npx netlify dev
```

Use the URL printed by `netlify dev`. Running `npm run dev` starts Vite only, so serverless `/api` endpoints will not be available.

## Configuration

Configure the following values in local `.env` files and in Netlify environment variables. Never commit `.env` files, service-role keys, encryption keys, or notification tokens.

| Variable | Purpose | Exposure |
| --- | --- | --- |
| `SUPABASE_URL` | Supabase URL used by Functions | Server only |
| `SUPABASE_SERVICE_ROLE_KEY` | Auth verification and scheduled server operations | Secret |
| `VITE_SUPABASE_URL` | Browser connection to Supabase Auth | Public |
| `VITE_SUPABASE_ANON_KEY` | Browser anonymous key; protected by RLS | Public |
| `APP_ENCRYPTION_KEY` | Base64-encoded 32-byte key for PushPlus token encryption | Secret |
| `ALLOWED_ORIGIN` | Production web origin, e.g. `https://example.netlify.app` | Server configuration |

Each user stores their own PushPlus token in the Settings screen. A shared `PUSHPLUS_TOKEN` must not be used because it would mix notifications between accounts.

## Deployment

1. Create a Supabase project and enable Email/Password sign-in.
2. Run `supabase/migrations/001_init.sql` and `supabase/migrations/002_multi_tenant_security.sql` in order. The migration does not delete existing records. Legacy global records with a `NULL` `user_id` are intentionally hidden until they are safely assigned to an owner.
3. Import the repository into Netlify. The repository config uses Node.js 22 and `npm run build`.
4. Add every required environment variable in Netlify. Keep service keys and `APP_ENCRYPTION_KEY` private.
5. Add the deployed site URL to Supabase Auth's Site URL and Redirect URL allow list. Set `ALLOWED_ORIGIN` to the identical origin.
6. Create a test account, add an alert, and test both browser and PushPlus delivery before release.

## Testing

```bash
npm ci
npm test
npm run build
```

The current test suite verifies bounded symbol validation, U.S. quote normalization, unsafe threshold rejection, and malformed-price filtering. Production verification should also cover unauthenticated API rejection, cross-user RLS isolation, retry behaviour, one delivery per rule/day, and failed-notification recovery.

## Production Considerations

- The Tencent public endpoint has no guaranteed SLA, rate-limit contract, or complete exchange holiday calendar. This project batches at most 50 symbols per quote request and uses timeouts plus exponential backoff; a licensed market-data provider and a proper trading calendar are recommended for production use.
- Netlify Cron is not a real-time scheduler and missed executions are not backfilled with historical quotes.
- A public health endpoint and an error-tracking service such as Sentry are still recommended before a broader release.
- The capital-flow feature is display-only; user-level capital-flow rules and de-duplication are not implemented.

## Security Notes

Supabase service-role keys are used only inside Netlify Functions and must never be exposed through `VITE_*` variables, client-side code, screenshots, or commits. RLS enforces data isolation and Functions additionally verify the Supabase Bearer JWT. Keep `.env` excluded by `.gitignore`, revoke and rotate any exposed secret immediately, and plan token re-encryption before rotating `APP_ENCRYPTION_KEY`.

## License

This project is intended for learning and portfolio demonstration. Market data is for informational use only.
