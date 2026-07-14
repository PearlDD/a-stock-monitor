"""SQLite database setup with WAL mode and schema initialization."""

from __future__ import annotations

import aiosqlite
import structlog

logger = structlog.get_logger()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    rule_type TEXT NOT NULL,
    threshold REAL,
    keyword TEXT,
    cooldown_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    price REAL NOT NULL,
    change_pct REAL,
    volume REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_snapshots_stock_time
    ON price_snapshots(stock_id, timestamp);

CREATE TABLE IF NOT EXISTS push_history (
    id INTEGER PRIMARY KEY,
    alert_rule_id INTEGER REFERENCES alert_rules(id),
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    push_serial TEXT,
    status TEXT DEFAULT 'sent',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_push_stock_time
    ON push_history(stock_id, sent_at);

CREATE TABLE IF NOT EXISTS news_cache (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    title TEXT NOT NULL,
    url TEXT,
    source TEXT,
    content_hash TEXT UNIQUE,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_news_stock
    ON news_cache(stock_id, fetched_at);
"""


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Open a database connection with WAL mode and create schema."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA cache_size=10000")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.executescript(_SCHEMA_SQL)
    await db.commit()
    await logger.ainfo("database.initialized", path=db_path)
    return db
