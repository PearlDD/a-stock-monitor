"""Tests for PushPlus push service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache import get_cache
from app.services.push import (
    DAILY_CAP,
    PushPlusClient,
    format_alert_message,
)


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def push_client():
    return PushPlusClient(token="test_token_12345")


class TestPushPlusClient:
    @pytest.mark.asyncio
    async def test_send_alert_success(self, push_client: PushPlusClient):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 200, "msg": "ok"}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await push_client.send_alert("Test Title", "Test Content")
            assert result is True

    @pytest.mark.asyncio
    async def test_send_alert_no_token(self):
        client = PushPlusClient(token="")
        result = await client.send_alert("Title", "Content")
        assert result is False

    @pytest.mark.asyncio
    async def test_daily_count_starts_at_zero(self, push_client: PushPlusClient):
        count = await push_client.get_daily_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_can_send_when_below_cap(self, push_client: PushPlusClient):
        assert await push_client.can_send() is True

    @pytest.mark.asyncio
    async def test_cannot_send_at_cap(self, push_client: PushPlusClient):
        cache = get_cache()
        # Set today's date so daily reset doesn't clear our counter
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        await cache.set("pushplus:daily_date", today, 86400)
        await cache.set_with_daily_reset("pushplus:daily_count", DAILY_CAP)
        assert await push_client.can_send() is False

    @pytest.mark.asyncio
    async def test_send_blocked_at_cap(self, push_client: PushPlusClient):
        cache = get_cache()
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        await cache.set("pushplus:daily_date", today, 86400)
        await cache.set_with_daily_reset("pushplus:daily_count", DAILY_CAP)
        result = await push_client.send_alert("Title", "Content")
        assert result is False


class TestFormatAlertMessage:
    def test_price_target(self):
        title, content = format_alert_message(
            stock_name="五粮液",
            stock_code="000858",
            alert_type="price_target",
            current_value=180.50,
            threshold=180.0,
        )
        assert "目标价" in title
        assert "¥180.50" in content
        assert "¥180.00" in content

    def test_limit_up(self):
        title, content = format_alert_message(
            stock_name="茅台",
            stock_code="600519",
            alert_type="limit_up",
            current_value=1900.0,
        )
        assert "涨停" in title or "涨停" in content

    def test_limit_down(self):
        title, content = format_alert_message(
            stock_name="茅台",
            stock_code="600519",
            alert_type="limit_down",
            current_value=1600.0,
        )
        assert "跌停" in content

    def test_volume_spike(self):
        title, content = format_alert_message(
            stock_name="茅台",
            stock_code="600519",
            alert_type="volume_spike",
            current_value=5.0,
        )
        assert "异动" in title or "异动" in content

    def test_all_messages_have_disclaimer(self):
        for alert_type in [
            "price_target",
            "limit_up",
            "limit_down",
            "volume_spike",
        ]:
            _, content = format_alert_message(
                stock_name="测试",
                stock_code="000001",
                alert_type=alert_type,
                current_value=100.0,
                threshold=90.0,
            )
            assert "不构成投资建议" in content

    def test_message_is_short(self):
        """Elderly-friendly: messages should be concise (3-4 lines + disclaimer)."""
        _, content = format_alert_message(
            stock_name="茅台",
            stock_code="600519",
            alert_type="price_target",
            current_value=1900.0,
            threshold=1850.0,
        )
        lines = [x for x in content.strip().split("\n") if x.strip()]
        assert len(lines) <= 6  # 3-4 content lines + blank + disclaimer
