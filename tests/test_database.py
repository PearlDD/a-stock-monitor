"""Tests for database layer."""

import os
import tempfile

import pytest

from app.database import get_db, init_db


@pytest.fixture
async def db_path():
    """Create a temp DB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        await init_db(path)
        yield path


class TestDatabaseInit:
    @pytest.mark.asyncio
    async def test_init_creates_tables(self, db_path: str):
        async with get_db(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in await cursor.fetchall()}
            assert "stocks" in tables
            assert "alert_rules" in tables
            assert "price_snapshots" in tables
            assert "push_history" in tables
            assert "news_cache" in tables

    @pytest.mark.asyncio
    async def test_wal_mode(self, db_path: str):
        async with get_db(db_path) as db:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"


class TestStocksCRUD:
    @pytest.mark.asyncio
    async def test_insert_and_select(self, db_path: str):
        async with get_db(db_path) as db:
            await db.execute(
                "INSERT INTO stocks (code, name) VALUES (?, ?)",
                ("600519", "贵州茅台"),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM stocks WHERE code = ?", ("600519",)
            )
            row = await cursor.fetchone()
            assert row["code"] == "600519"
            assert row["name"] == "贵州茅台"

    @pytest.mark.asyncio
    async def test_delete(self, db_path: str):
        async with get_db(db_path) as db:
            await db.execute(
                "INSERT INTO stocks (code, name) VALUES (?, ?)",
                ("600519", "贵州茅台"),
            )
            await db.commit()
            await db.execute("DELETE FROM stocks WHERE code = ?", ("600519",))
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM stocks WHERE code = ?", ("600519",)
            )
            assert await cursor.fetchone() is None


class TestAlertRulesCRUD:
    @pytest.mark.asyncio
    async def test_insert_alert_rule(self, db_path: str):
        async with get_db(db_path) as db:
            await db.execute(
                "INSERT INTO stocks (code, name) VALUES (?, ?)",
                ("600519", "贵州茅台"),
            )
            sql = (
                "INSERT INTO alert_rules"
                " (stock_code, stock_name, alert_type, threshold)"
                " VALUES (?, ?, ?, ?)"
            )
            await db.execute(
                sql,
                ("600519", "贵州茅台", "price_pct_change", 5.0),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM alert_rules WHERE stock_code = ?", ("600519",)
            )
            row = await cursor.fetchone()
            assert row["alert_type"] == "price_pct_change"
            assert row["threshold"] == 5.0
            assert row["enabled"] == 1
