"""Tests for volume_spike alert type (code review fix)."""

from __future__ import annotations

import pytest

from app.models.market import StockQuote
from app.services.alerting import AlertEngine, AlertRule
from app.services.cache import get_cache


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


def _make_quote(
    code: str = "600519",
    price: float = 100.0,
    volume: float = 10000.0,
    prev_close: float = 100.0,
) -> StockQuote:
    return StockQuote(
        code=code, name="Test", price=price,
        change_pct=0.0, volume=volume, amount=0,
        high=price, low=price, open=prev_close, prev_close=prev_close,
    )


def _make_volume_rule(
    code: str = "600519", threshold: float = 3.0
) -> AlertRule:
    return AlertRule(
        id=1, stock_code=code, stock_name="Test",
        alert_type="volume_spike", threshold=threshold,
    )


class TestVolumeSpikeAlert:
    @pytest.mark.asyncio
    async def test_no_history_no_trigger(self):
        """Without volume history, volume_spike should not trigger."""
        engine = AlertEngine()
        rule = _make_volume_rule(threshold=2.0)
        quotes = [_make_quote(volume=50000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        # First eval records volume but avg is based on current only, so
        # volume == avg, ratio is 1x, threshold 2x not met
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_spike_triggers(self):
        """Volume spike should trigger when volume > threshold * average."""
        engine = AlertEngine()
        rule = _make_volume_rule(threshold=3.0)

        # Build up volume history with normal volume
        for _ in range(5):
            quotes = [_make_quote(volume=10000.0)]
            await engine.evaluate(quotes, [rule])
            engine.reset_state()  # reset edge trigger for next eval

        # Now spike volume to 4x average
        quotes = [_make_quote(volume=40000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1
        assert triggered[0].current_value > 3.0  # ratio

    @pytest.mark.asyncio
    async def test_no_spike_normal_volume(self):
        """Normal volume should not trigger volume_spike."""
        engine = AlertEngine()
        rule = _make_volume_rule(threshold=3.0)

        # Build history
        for _ in range(5):
            quotes = [_make_quote(volume=10000.0)]
            await engine.evaluate(quotes, [rule])
            engine.reset_state()

        # Only slightly above average
        quotes = [_make_quote(volume=15000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_zero_volume_no_trigger(self):
        """Zero volume should never trigger."""
        engine = AlertEngine()
        rule = _make_volume_rule(threshold=2.0)
        quotes = [_make_quote(volume=0.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    def test_rolling_average_calculation(self):
        """Test rolling average tracks correctly."""
        engine = AlertEngine()
        for v in [100, 200, 300]:
            engine.record_volume("600519", v)
        assert engine.get_avg_volume("600519") == 200.0

    def test_rolling_window_limit(self):
        """History should be limited to window size."""
        engine = AlertEngine()
        engine._volume_window = 3
        for v in [10, 20, 30, 40, 50]:
            engine.record_volume("600519", v)
        assert engine.get_avg_volume("600519") == 40.0  # avg of [30, 40, 50]

    def test_avg_empty_history(self):
        engine = AlertEngine()
        assert engine.get_avg_volume("999999") == 0.0
