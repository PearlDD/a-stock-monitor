"""Alert evaluation engine.

Supports: price_target (one-shot), limit_up/down (daily), volume_spike (daily).
Uses edge triggering (alerts on threshold CROSSING, not while above).
Per-stock 30-minute cooldown with dedup.

Lifecycle:
  - price_target: ONE-SHOT. Auto-disable after trigger, record triggered_at.
  - limit_up / limit_down / volume_spike: DAILY. Fire at most once per day per stock.
    Reset at 09:30 CST each trading day.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.logging import get_logger
from app.models.market import StockQuote
from app.services.cache import get_cache

log = get_logger("alerting")

COOLDOWN_SECONDS = 1800  # 30 minutes

# Alert types that fire once per day (reset at 09:30 CST)
DAILY_ALERT_TYPES = {"limit_up", "limit_down", "volume_spike"}

# Alert types that are one-shot (auto-disable after trigger)
ONE_SHOT_ALERT_TYPES = {"price_target"}


@dataclass
class AlertRule:
    """An alert rule configuration."""

    id: int
    stock_code: str
    stock_name: str
    alert_type: str  # price_target, limit_up, limit_down, volume_spike
    threshold: float  # depends on type: price, or volume multiplier
    direction: str = "above"  # above or below (for price_target)
    enabled: bool = True
    triggered_at: str | None = None


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
        self._volume_history: dict[str, list[float]] = {}
        self._volume_window = 20  # rolling window size for average
        self._daily_fired: dict[int, str] = {}  # rule_id -> date string

    def record_volume(self, code: str, volume: float) -> None:
        """Record a volume observation for rolling average calculation."""
        history = self._volume_history.setdefault(code, [])
        history.append(volume)
        if len(history) > self._volume_window:
            self._volume_history[code] = history[-self._volume_window :]

    def get_avg_volume(self, code: str) -> float:
        """Get the rolling average volume for a stock."""
        history = self._volume_history.get(code, [])
        if not history:
            return 0.0
        return sum(history) / len(history)

    def reset_daily_fired(self) -> None:
        """Reset daily fired state (called at 09:30 CST each trading day)."""
        self._daily_fired.clear()
        log.info("daily_fired_state_reset")

    def _is_daily_fired(self, rule_id: int) -> bool:
        """Check if a daily alert has already fired today."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        return self._daily_fired.get(rule_id) == today

    def _mark_daily_fired(self, rule_id: int) -> None:
        """Mark a daily alert as fired for today."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        self._daily_fired[rule_id] = today

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

            # Daily alert types: check if already fired today
            if rule.alert_type in DAILY_ALERT_TYPES:
                if self._is_daily_fired(rule.id):
                    log.debug(
                        "daily_alert_already_fired",
                        rule_id=rule.id,
                        code=rule.stock_code,
                    )
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

            # Mark daily fired for daily types
            if rule.alert_type in DAILY_ALERT_TYPES:
                self._mark_daily_fired(rule.id)

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

        # Record volumes AFTER evaluation (so spike isn't counted in its own avg)
        for q in quotes:
            if q.volume > 0:
                self.record_volume(q.code, q.volume)

        return triggered

    def _check_condition(self, quote: StockQuote, rule: AlertRule) -> bool:
        """Check if a quote matches an alert condition."""
        if rule.alert_type == "price_target":
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
            avg_vol = self.get_avg_volume(quote.code)
            if avg_vol <= 0 or quote.volume <= 0:
                return False
            return quote.volume > rule.threshold * avg_vol

        return False

    def _get_current_value(self, quote: StockQuote, rule: AlertRule) -> float:
        """Get the relevant current value for the alert type."""
        if rule.alert_type in ("price_target", "limit_up", "limit_down"):
            return quote.price
        elif rule.alert_type == "volume_spike":
            avg_vol = self.get_avg_volume(quote.code)
            return quote.volume / avg_vol if avg_vol > 0 else 0.0
        return 0.0

    def reset_state(self, stock_code: str | None = None) -> None:
        """Reset edge-trigger state. If code is None, reset all."""
        if stock_code:
            self._previous_states.pop(stock_code, None)
        else:
            self._previous_states.clear()
