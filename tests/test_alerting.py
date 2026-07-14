"""Tests for alert evaluation engine."""

import pytest

from app.models.market import StockQuote
from app.services.alerting import AlertEngine, AlertRule
from app.services.cache import get_cache


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def engine():
    return AlertEngine()


def _make_quote(
    code: str = "600519",
    name: str = "贵州茅台",
    price: float = 1800.0,
    change_pct: float = 0.0,
    prev_close: float = 1750.0,
    volume: float = 100000.0,
) -> StockQuote:
    return StockQuote(
        code=code,
        name=name,
        price=price,
        change_pct=change_pct,
        volume=volume,
        amount=0,
        high=price,
        low=price,
        open=prev_close,
        prev_close=prev_close,
    )


def _make_rule(
    rule_id: int = 1,
    code: str = "600519",
    alert_type: str = "price_pct_change",
    threshold: float = 5.0,
    direction: str = "above",
) -> AlertRule:
    return AlertRule(
        id=rule_id,
        stock_code=code,
        stock_name="贵州茅台",
        alert_type=alert_type,
        threshold=threshold,
        direction=direction,
    )


class TestAlertEngineEdgeTrigger:
    @pytest.mark.asyncio
    async def test_triggers_on_crossing(self, engine: AlertEngine):
        """Alert fires when condition transitions from False to True."""
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)

        # First eval: below threshold → no trigger
        quotes = [_make_quote(change_pct=3.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

        # Second eval: above threshold → trigger
        quotes = [_make_quote(change_pct=6.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1

    @pytest.mark.asyncio
    async def test_no_repeat_while_above(self, engine: AlertEngine):
        """Alert does NOT re-fire while still above threshold (edge trigger)."""
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)

        # Clear cooldown for this test
        quotes = [_make_quote(change_pct=6.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1

        # Still above threshold — should NOT trigger again (edge trigger)
        quotes = [_make_quote(change_pct=7.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_first_eval_above_threshold_triggers(self, engine: AlertEngine):
        """First evaluation with condition True should trigger."""
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)
        quotes = [_make_quote(change_pct=6.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1


class TestAlertCooldown:
    @pytest.mark.asyncio
    async def test_cooldown_prevents_retrigger(self, engine: AlertEngine):
        """After trigger, cooldown prevents same alert from firing."""
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)

        # Trigger
        quotes = [_make_quote(change_pct=6.0)]
        await engine.evaluate(quotes, [rule])

        # Reset edge state to simulate re-crossing
        engine.reset_state()

        # Try to trigger again — cooldown should block
        quotes = [_make_quote(change_pct=7.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0


class TestAlertTypes:
    @pytest.mark.asyncio
    async def test_price_target_above(self, engine: AlertEngine):
        rule = _make_rule(
            alert_type="price_target", threshold=1900.0, direction="above"
        )
        quotes = [_make_quote(price=1950.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1
        assert triggered[0].current_value == 1950.0

    @pytest.mark.asyncio
    async def test_price_target_below(self, engine: AlertEngine):
        rule = _make_rule(
            alert_type="price_target", threshold=1700.0, direction="below"
        )
        quotes = [_make_quote(price=1650.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1

    @pytest.mark.asyncio
    async def test_price_target_not_reached(self, engine: AlertEngine):
        rule = _make_rule(
            alert_type="price_target", threshold=2000.0, direction="above"
        )
        quotes = [_make_quote(price=1800.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_limit_up(self, engine: AlertEngine):
        rule = _make_rule(alert_type="limit_up")
        # 10% gain from prev_close=1000
        quotes = [_make_quote(price=1100.0, prev_close=1000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1

    @pytest.mark.asyncio
    async def test_limit_down(self, engine: AlertEngine):
        rule = _make_rule(alert_type="limit_down")
        # 10% drop from prev_close=1000
        quotes = [_make_quote(price=900.0, prev_close=1000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 1

    @pytest.mark.asyncio
    async def test_limit_up_not_reached(self, engine: AlertEngine):
        rule = _make_rule(alert_type="limit_up")
        quotes = [_make_quote(price=1050.0, prev_close=1000.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_disabled_rule_skipped(self, engine: AlertEngine):
        rule = _make_rule(alert_type="price_pct_change", threshold=1.0)
        rule.enabled = False
        quotes = [_make_quote(change_pct=5.0)]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0

    @pytest.mark.asyncio
    async def test_no_quote_for_rule(self, engine: AlertEngine):
        rule = _make_rule(code="999999", alert_type="price_pct_change", threshold=1.0)
        quotes = [_make_quote(code="600519")]
        triggered = await engine.evaluate(quotes, [rule])
        assert len(triggered) == 0


class TestAlertEngineReset:
    @pytest.mark.asyncio
    async def test_reset_specific_stock(self, engine: AlertEngine):
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)
        quotes = [_make_quote(change_pct=6.0)]
        await engine.evaluate(quotes, [rule])
        engine.reset_state("600519")
        assert "600519" not in engine._previous_states

    @pytest.mark.asyncio
    async def test_reset_all(self, engine: AlertEngine):
        rule = _make_rule(alert_type="price_pct_change", threshold=5.0)
        quotes = [_make_quote(change_pct=6.0)]
        await engine.evaluate(quotes, [rule])
        engine.reset_state()
        assert len(engine._previous_states) == 0
