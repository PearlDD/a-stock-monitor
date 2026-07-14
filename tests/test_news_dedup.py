"""Tests for news alert deduplication and structured logging."""

from __future__ import annotations

import hashlib

import pytest

from app.database import get_db, init_db
from app.logging import (
    clear_request_context,
    configure_logging,
    generate_request_id,
    get_logger,
)


@pytest.fixture
async def test_db(tmp_path):
    import os
    db_path = str(tmp_path / "test_dedup.db")
    os.environ["DATABASE_PATH"] = db_path
    await init_db(db_path)
    yield db_path
    os.environ.pop("DATABASE_PATH", None)


class TestNewsDedup:
    @pytest.mark.asyncio
    async def test_insert_and_detect_duplicate(self, test_db):
        """Same headline hash should only be inserted once."""
        title = "茅台发布最新年报"
        h = hashlib.md5(title.encode()).hexdigest()

        async with get_db() as db:
            await db.execute(
                "INSERT INTO news_alerts_seen (headline_hash, stock_code, title)"
                " VALUES (?, ?, ?)",
                (h, "600519", title),
            )
            await db.commit()

        # Check it exists
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT 1 FROM news_alerts_seen WHERE headline_hash = ?", (h,)
            )
            assert await cursor.fetchone() is not None

        # Try inserting same hash — should be ignored by UNIQUE constraint
        async with get_db() as db:
            await db.execute(
                "INSERT OR IGNORE INTO news_alerts_seen"
                " (headline_hash, stock_code, title) VALUES (?, ?, ?)",
                (h, "600519", title),
            )
            await db.commit()

            cursor = await db.execute("SELECT COUNT(*) as cnt FROM news_alerts_seen")
            row = await cursor.fetchone()
            assert row["cnt"] == 1

    @pytest.mark.asyncio
    async def test_different_headlines_both_stored(self, test_db):
        titles = ["新闻A", "新闻B"]
        for title in titles:
            h = hashlib.md5(title.encode()).hexdigest()
            async with get_db() as db:
                await db.execute(
                    "INSERT OR IGNORE INTO news_alerts_seen"
                    " (headline_hash, stock_code, title) VALUES (?, ?, ?)",
                    (h, "600519", title),
                )
                await db.commit()

        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM news_alerts_seen")
            row = await cursor.fetchone()
            assert row["cnt"] == 2


class TestStructuredLogging:
    def test_request_id_generation(self):
        rid = generate_request_id()
        assert len(rid) == 12
        assert isinstance(rid, str)

    def test_unique_request_ids(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_configure_logging_no_error(self):
        configure_logging("INFO")
        configure_logging("DEBUG")

    def test_get_logger(self):
        log = get_logger("test")
        assert log is not None

    def test_clear_context(self):
        from app.logging import bind_request_id
        bind_request_id("test123")
        clear_request_context()


class TestPWAManifest:
    def test_manifest_exists(self):
        import json
        from pathlib import Path

        base = Path(__file__).parent.parent
        manifest_path = base / "frontend" / "public" / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            data = json.load(f)

        assert data["name"] == "A股智能监控"
        assert data["display"] == "standalone"
        assert len(data["icons"]) >= 1
