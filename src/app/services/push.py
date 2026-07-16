"""PushPlus WeChat notification client.

Sends alerts via HTTP POST to http://www.pushplus.plus/send
Daily cap: warn at 150, hard-stop at 180.
Message batching: combines >3 alerts within 1 minute.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx

from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("push")

PUSHPLUS_URL = "http://www.pushplus.plus/send"
DAILY_CAP = 180
DAILY_WARN = 150
BATCH_WINDOW_SECONDS = 60
BATCH_THRESHOLD = 3

_DAILY_COUNTER_KEY = "pushplus:daily_count"
_DAILY_DATE_KEY = "pushplus:daily_date"


@dataclass
class PendingAlert:
    title: str
    content: str
    queued_at: float = field(default_factory=time.monotonic)


class PushPlusClient:
    """PushPlus notification sender with daily limits and batching."""

    def __init__(self, token: str) -> None:
        self.token = token
        self._batch_buffer: list[PendingAlert] = []
        self._batch_lock = asyncio.Lock()
        self._last_flush: float = 0.0

    async def _check_daily_reset(self) -> None:
        """Reset daily counter if date changed."""
        cache = get_cache()
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        stored_date = await cache.get(_DAILY_DATE_KEY)
        if stored_date != today:
            await cache.reset_counter(_DAILY_COUNTER_KEY)
            await cache.set(_DAILY_DATE_KEY, today, 86400)

    async def get_daily_count(self) -> int:
        await self._check_daily_reset()
        return await get_cache().get_counter(_DAILY_COUNTER_KEY)

    async def can_send(self) -> bool:
        count = await self.get_daily_count()
        return count < DAILY_CAP

    async def send_alert(self, title: str, content: str) -> bool:
        """Send a single alert. Returns True if sent successfully."""
        if not self.token:
            log.warning("pushplus_no_token")
            return False

        await self._check_daily_reset()
        cache = get_cache()
        count = await cache.get_counter(_DAILY_COUNTER_KEY)

        if count >= DAILY_CAP:
            log.error("pushplus_daily_cap_reached", count=count, cap=DAILY_CAP)
            return False

        if count >= DAILY_WARN:
            log.warning("pushplus_daily_warn", count=count, warn_at=DAILY_WARN)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    PUSHPLUS_URL,
                    json={
                        "token": self.token,
                        "title": title,
                        "content": content,
                        "template": "txt",
                    },
                )
                data = resp.json()
                if data.get("code") == 200:
                    await cache.incr(_DAILY_COUNTER_KEY)
                    log.info(
                        "pushplus_sent",
                        title=title,
                        daily_count=count + 1,
                    )
                    return True
                else:
                    log.error("pushplus_api_error", response=data)
                    return False
        except Exception:
            log.error("pushplus_send_failed", exc_info=True)
            return False

    async def queue_alert(self, title: str, content: str) -> None:
        """Queue an alert for potential batching."""
        async with self._batch_lock:
            self._batch_buffer.append(PendingAlert(title=title, content=content))
            if len(self._batch_buffer) >= BATCH_THRESHOLD:
                await self._flush_batch()
            elif not self._batch_buffer[0:1]:
                pass  # empty, shouldn't happen
            else:
                # Schedule flush after batch window
                now = time.monotonic()
                if now - self._last_flush > BATCH_WINDOW_SECONDS:
                    asyncio.get_running_loop().call_later(
                        BATCH_WINDOW_SECONDS,
                        lambda: asyncio.ensure_future(self.flush()),
                    )

    async def flush(self) -> None:
        async with self._batch_lock:
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Send all queued alerts as a single batched message."""
        if not self._batch_buffer:
            return

        alerts = self._batch_buffer[:]
        self._batch_buffer.clear()
        self._last_flush = time.monotonic()

        if len(alerts) == 1:
            await self.send_alert(alerts[0].title, alerts[0].content)
            return

        # Batch multiple alerts into one message
        title = f"📊 股票提醒 ({len(alerts)}条)"
        lines = []
        for a in alerts:
            lines.append(f"【{a.title}】\n{a.content}")
        content = "\n\n---\n\n".join(lines)
        content += "\n\n⚠️ 以上信息仅供参考，不构成投资建议"
        await self.send_alert(title, content)

    async def send_test(self) -> bool:
        """Send a test message to verify token works."""
        return await self.send_alert(
            "🔔 测试通知",
            "A股监控系统连接成功！\n\n⚠️ 此为测试消息，不构成投资建议",
        )


def format_alert_message(
    stock_name: str,
    stock_code: str,
    alert_type: str,
    current_value: float,
    threshold: float | None = None,
) -> tuple[str, str]:
    """Format an elderly-friendly alert message (3-4 lines + disclaimer).

    Returns (title, content) tuple.
    """
    type_labels = {
        "price_target": "目标价提醒",
        "limit_up": "涨停提醒",
        "limit_down": "跌停提醒",
        "volume_spike": "成交量异动",
    }
    label = type_labels.get(alert_type, "股票提醒")
    title = f"📊 {stock_name} {label}"

    if alert_type == "price_target":
        content = (
            f"{stock_name}({stock_code})\n"
            f"当前价格: ¥{current_value:.2f}\n"
            f"目标价格: ¥{threshold or 0:.2f}"
        )
    elif alert_type in ("limit_up", "limit_down"):
        status = "涨停" if alert_type == "limit_up" else "跌停"
        content = (
            f"{stock_name}({stock_code})\n已{status}! 当前价: ¥{current_value:.2f}"
        )
    elif alert_type == "volume_spike":
        content = f"{stock_name}({stock_code})\n成交量异动: {current_value:.0f}倍于均量"
    else:
        content = f"{stock_name}({stock_code})\n当前值: {current_value}"

    content += "\n\n⚠️ 以上信息仅供参考，不构成投资建议"
    return title, content
