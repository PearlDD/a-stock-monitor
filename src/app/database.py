"""SQLite database with aiosqlite, WAL mode.

Tables: stocks (watchlist), alert_rules, price_snapshots, push_history, news_cache.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

from app.logging import get_logger

log = get_logger("database")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market TEXT DEFAULT '',
    sector TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL DEFAULT '',
    alert_type TEXT NOT NULL,
    threshold REAL NOT NULL,
    direction TEXT DEFAULT 'above',
    enabled INTEGER DEFAULT 1,
    triggered_at TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE TABLE IF NOT EXISTS capital_flow_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL DEFAULT '',
    net_inflow REAL NOT NULL,
    change_pct REAL DEFAULT 0,
    recorded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS capital_flow_alerts_seen (
    stock_code TEXT NOT NULL,
    alert_date TEXT NOT NULL,
    alerted_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (stock_code, alert_date)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    price REAL NOT NULL,
    change_pct REAL DEFAULT 0,
    volume REAL DEFAULT 0,
    recorded_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE TABLE IF NOT EXISTS push_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'sent',
    sent_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT DEFAULT '',
    url TEXT DEFAULT '',
    publish_time TEXT DEFAULT '',
    cached_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_stock ON alert_rules(stock_code);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_stock ON price_snapshots(stock_code);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_time ON price_snapshots(recorded_at);
CREATE INDEX IF NOT EXISTS idx_push_history_time ON push_history(sent_at);
CREATE INDEX IF NOT EXISTS idx_news_cache_stock ON news_cache(stock_code);

CREATE TABLE IF NOT EXISTS ai_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    request_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT DEFAULT '',
    tokens_used INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_alerts_seen (
    headline_hash TEXT PRIMARY KEY,
    stock_code TEXT NOT NULL,
    title TEXT NOT NULL,
    seen_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_log_stock ON ai_log(stock_code);
CREATE INDEX IF NOT EXISTS idx_ai_log_time ON ai_log(created_at);
CREATE INDEX IF NOT EXISTS idx_news_alerts_seen_time ON news_alerts_seen(seen_at);
CREATE INDEX IF NOT EXISTS idx_cf_snapshots_time
    ON capital_flow_snapshots(recorded_at);
CREATE INDEX IF NOT EXISTS idx_cf_snapshots_code
    ON capital_flow_snapshots(stock_code);
"""

_DB_PATH = "data/stock_monitor.db"


def _get_db_path() -> str:
    path = os.environ.get("DATABASE_PATH", _DB_PATH)
    # Strip SQLAlchemy prefix if present
    if path.startswith("sqlite"):
        path = path.split("///", 1)[-1] if "///" in path else _DB_PATH
    return path


async def init_db(db_path: str | None = None) -> None:
    """Initialize the database schema."""
    path = db_path or _get_db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA cache_size=10000")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.executescript(_SCHEMA)
        await db.commit()
    log.info("database_initialized", path=path)


@asynccontextmanager
async def get_db(
    db_path: str | None = None,
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get a database connection with WAL mode enabled."""
    path = db_path or _get_db_path()
    db = await aiosqlite.connect(path)
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()
