# Factory Configuration

## Goal

Build a reliable A-share stock monitoring system that auto-collects real-time quotes and news via AKShare (THS), triggers price/change/keyword alerts, pushes notifications to WeChat via PushPlus, and provides a web management UI.

## Scope

### Modifiable

- src/**/*.py
- tests/**/*.py
- templates/**/*.html
- static/**/*.css
- static/**/*.js
- pyproject.toml
- Dockerfile
- docker-compose.yml
- .env.example
- CLAUDE.md

### Read-only

- README.md
- factory.md
- eval/score.py

## Guards

- Do not delete or overwrite existing tests
- Do not modify files outside the declared scope
- Do not introduce secrets or credentials into the repository
- Do not hardcode PushPlus tokens or any API keys — use environment variables
- AKShare data calls must use THS (同花顺) interfaces, not East Money (东方财富) for quote data

## Eval

### Command

```bash
python3 eval/score.py
```

### Threshold

0.3

## Target Branch

main

## Smoke Test

```bash
cd /Users/pearl/factory-projects/spec && uv run python -c "from app.main import create_app; app = create_app(); print('OK')"
```

## Constraints

- Prefer small, incremental changes over large rewrites
- Each change should be accompanied by at least one test
- Follow the existing code style and conventions
- Use MockProvider for all tests — no network calls in CI
- Rate limit AKShare requests: minimum 2-3 seconds between calls
- PushPlus daily cap tracking: treat 180 as safe limit (not 200)
- SQLite with WAL mode for concurrent access
