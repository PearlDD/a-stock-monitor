"""Alert evaluation engine.

Supports: price_pct_change, price_target, limit_up/down, volume_spike.
Uses edge triggering (alerts on threshold CROSSING, not while above).
Per-stock 30-minute cooldown with dedup.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.logging import get_logger
from app.models.market import StockQuote
from app.services.cache import get_cache

log = get_logger("alerting")

COOLDOWN_SECONDS = 1800  # 30 minutes


@dataclass
class AlertRule:
    """An alert rule configuration."""

    id: int
    stock_code: str
    stock_name: str
    alert_type: (
        str  # price_pct_change, price_target, limit_up, limit_down, volume_spike
    )
    threshold: float  # depends on type: pct, price, or volume multiplier
    direction: str = "above"  # above or below (for price_target)
    enabled: bool = True


@dataclass
class TriggeredAlert:
    """An alert that has been triggered."""

    rule: AlertRule
    current_value: float
    triggered_at: float


class AlertEngine:
    """Evaluate quotes against alert rules with edge-trigger and cooldown."""

    def __init__(self) -> None:
        self._previous_states: dict[str, dict[int, bool]] = {}

    async def evaluate(
        self,
        quotes: list[StockQuote],
        rules: list[AlertRule],
    ) -> list[TriggeredAlert]:
        """Evaluate quotes against rules. Returns newly triggered alerts."""
        triggered: list[TriggeredAlert] = []
        cache = get_cache()
        quote_map = {q.code: q for q in quotes}

        for rule in rules:
            if not rule.enabled:
                continue

            quote = quote_map.get(rule.stock_code)
            if quote is None:
                continue

            is_triggered = self._check_condition(quote, rule)

            # Edge trigger: only fire when transitioning from False → True
            prev_state = self._previous_states.get(rule.stock_code, {}).get(
                rule.id, False
            )
            self._previous_states.setdefault(rule.stock_code, {})[rule.id] = (
                is_triggered
            )

            if not is_triggered or prev_state:
                continue

            # Check cooldown
            cooldown_key = f"alert_cooldown:{rule.stock_code}:{rule.id}"
            if await cache.exists(cooldown_key):
                log.debug(
                    "alert_cooldown_active", rule_id=rule.id, code=rule.stock_code
                )
                continue

            # Set cooldown
            await cache.set(cooldown_key, True, COOLDOWN_SECONDS)

            current_value = self._get_current_value(quote, rule)
            alert = TriggeredAlert(
                rule=rule,
                current_value=current_value,
                triggered_at=time.time(),
            )
            triggered.append(alert)
            log.info(
                "alert_triggered",
                rule_id=rule.id,
                code=rule.stock_code,
                type=rule.alert_type,
                value=current_value,
                threshold=rule.threshold,
            )

        return triggered

    def _check_condition(self, quote: StockQuote, rule: AlertRule) -> bool:
        """Check if a quote matches an alert condition."""
        if rule.alert_type == "price_pct_change":
            return abs(quote.change_pct) >= abs(rule.threshold)

        elif rule.alert_type == "price_target":
            if rule.direction == "above":
                return quote.price >= rule.threshold
            else:
                return quote.price <= rule.threshold

        elif rule.alert_type == "limit_up":
            # A-share limit up is ~10% (20% for 创业板/科创板)
            if quote.prev_close <= 0:
                return False
            change = (quote.price - quote.prev_close) / quote.prev_close * 100
            return change >= 9.9

        elif rule.alert_type == "limit_down":
            if quote.prev_close <= 0:
                return False
            change = (quote.price - quote.prev_close) / quote.prev_close * 100
            return change <= -9.9

        elif rule.alert_type == "volume_spike":
            # threshold is the multiplier (e.g., 3 = 3x average volume)
            return rule.threshold > 0 and quote.volume > 0

        return False

    def _get_current_value(self, quote: StockQuote, rule: AlertRule) -> float:
        """Get the relevant current value for the alert type."""
        if rule.alert_type == "price_pct_change":
            return quote.change_pct
        elif rule.alert_type in ("price_target", "limit_up", "limit_down"):
            return quote.price
        elif rule.alert_type == "volume_spike":
            return quote.volume
        return 0.0

    def reset_state(self, stock_code: str | None = None) -> None:
        """Reset edge-trigger state. If code is None, reset all."""
        if stock_code:
            self._previous_states.pop(stock_code, None)
        else:
            self._previous_states.clear()
