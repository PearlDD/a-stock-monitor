"""Tests for trading calendar service."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.services.trading_calendar import (
    SHANGHAI_TZ,
    is_trade_date,
    is_trading_hours,
    should_poll,
)


class TestTradingHours:
    def test_morning_open(self):
        dt = datetime(2026, 7, 13, 9, 30, tzinfo=SHANGHAI_TZ)  # Monday
        assert is_trading_hours(dt) is True

    def test_morning_mid(self):
        dt = datetime(2026, 7, 13, 10, 15, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is True

    def test_morning_close(self):
        dt = datetime(2026, 7, 13, 11, 30, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is True

    def test_lunch_break(self):
        dt = datetime(2026, 7, 13, 12, 0, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is False

    def test_afternoon_open(self):
        dt = datetime(2026, 7, 13, 13, 0, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is True

    def test_afternoon_close(self):
        dt = datetime(2026, 7, 13, 15, 0, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is True

    def test_after_close(self):
        dt = datetime(2026, 7, 13, 15, 1, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is False

    def test_before_open(self):
        dt = datetime(2026, 7, 13, 9, 29, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is False

    def test_midnight(self):
        dt = datetime(2026, 7, 13, 0, 0, tzinfo=SHANGHAI_TZ)
        assert is_trading_hours(dt) is False

    def test_converts_utc_to_shanghai(self):
        # 2:30 UTC = 10:30 Shanghai (trading hours)
        dt = datetime(2026, 7, 13, 2, 30, tzinfo=ZoneInfo("UTC"))
        assert is_trading_hours(dt) is True


class TestTradeDate:
    @pytest.mark.asyncio
    async def test_weekend_not_trade_date(self):
        from datetime import date

        saturday = date(2026, 7, 11)  # Saturday
        assert saturday.weekday() == 5
        assert await is_trade_date(saturday) is False

    @pytest.mark.asyncio
    async def test_sunday_not_trade_date(self):
        from datetime import date

        sunday = date(2026, 7, 12)
        assert sunday.weekday() == 6
        assert await is_trade_date(sunday) is False

    @pytest.mark.asyncio
    async def test_weekday_with_empty_calendar_is_trade_date(self):
        """When calendar API fails, weekdays are assumed trading days."""
        with patch(
            "app.services.trading_calendar.load_trade_dates", return_value=set()
        ):
            from datetime import date

            monday = date(2026, 7, 13)
            assert await is_trade_date(monday) is True


class TestShouldPoll:
    @pytest.mark.asyncio
    async def test_should_poll_during_trading(self):
        dt = datetime(2026, 7, 13, 10, 0, tzinfo=SHANGHAI_TZ)  # Monday 10:00
        with patch(
            "app.services.trading_calendar.load_trade_dates", return_value=set()
        ):
            result = await should_poll(dt)
            assert result is True

    @pytest.mark.asyncio
    async def test_should_not_poll_weekend(self):
        dt = datetime(2026, 7, 11, 10, 0, tzinfo=SHANGHAI_TZ)  # Saturday 10:00
        result = await should_poll(dt)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_not_poll_outside_hours(self):
        dt = datetime(2026, 7, 13, 20, 0, tzinfo=SHANGHAI_TZ)  # Monday 20:00
        result = await should_poll(dt)
        assert result is False
