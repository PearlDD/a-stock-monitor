"""Tests for TTL cache service."""

import time

import pytest

from app.services.cache import TTLCache


@pytest.fixture
def cache():
    return TTLCache()


class TestTTLCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: TTLCache):
        await cache.set("key1", "value1", ttl=60)
        assert await cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache: TTLCache):
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, cache: TTLCache):
        await cache.set("key1", "value1", ttl=1)
        assert await cache.get("key1") == "value1"
        # Simulate time passing by manipulating entry
        cache._store["key1"].expires_at = time.monotonic() - 1
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete(self, cache: TTLCache):
        await cache.set("key1", "value1", ttl=60)
        await cache.delete("key1")
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: TTLCache):
        await cache.delete("nonexistent")  # should not raise

    @pytest.mark.asyncio
    async def test_exists(self, cache: TTLCache):
        await cache.set("key1", "value1", ttl=60)
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_exists_expired(self, cache: TTLCache):
        await cache.set("key1", "value1", ttl=1)
        cache._store["key1"].expires_at = time.monotonic() - 1
        assert await cache.exists("key1") is False

    @pytest.mark.asyncio
    async def test_overwrite(self, cache: TTLCache):
        await cache.set("key1", "old", ttl=60)
        await cache.set("key1", "new", ttl=60)
        assert await cache.get("key1") == "new"

    @pytest.mark.asyncio
    async def test_different_types(self, cache: TTLCache):
        await cache.set("str", "hello", ttl=60)
        await cache.set("int", 42, ttl=60)
        await cache.set("list", [1, 2, 3], ttl=60)
        await cache.set("dict", {"a": 1}, ttl=60)
        assert await cache.get("str") == "hello"
        assert await cache.get("int") == 42
        assert await cache.get("list") == [1, 2, 3]
        assert await cache.get("dict") == {"a": 1}


class TestTTLCacheCounters:
    @pytest.mark.asyncio
    async def test_incr(self, cache: TTLCache):
        val = await cache.incr("counter1")
        assert val == 1
        val = await cache.incr("counter1")
        assert val == 2

    @pytest.mark.asyncio
    async def test_get_counter_default(self, cache: TTLCache):
        assert await cache.get_counter("nonexistent") == 0

    @pytest.mark.asyncio
    async def test_reset_counter(self, cache: TTLCache):
        await cache.incr("counter1")
        await cache.incr("counter1")
        await cache.reset_counter("counter1")
        assert await cache.get_counter("counter1") == 0

    @pytest.mark.asyncio
    async def test_set_with_daily_reset(self, cache: TTLCache):
        await cache.set_with_daily_reset("daily", 100)
        assert await cache.get_counter("daily") == 100


class TestTTLCacheCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache: TTLCache):
        await cache.set("live", "yes", ttl=3600)
        await cache.set("dead", "no", ttl=1)
        cache._store["dead"].expires_at = time.monotonic() - 1
        removed = await cache.cleanup_expired()
        assert removed == 1
        assert await cache.get("live") == "yes"
        assert await cache.get("dead") is None

    def test_clear(self, cache: TTLCache):
        cache._store["a"] = cache._store.get("a", None)  # type: ignore
        cache._counters["b"] = 1
        cache.clear()
        assert len(cache._store) == 0
        assert len(cache._counters) == 0
