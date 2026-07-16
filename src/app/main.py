"""FastAPI application factory."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import (
    bind_request_id,
    clear_request_context,
    configure_logging,
    generate_request_id,
    get_logger,
)


@asynccontextmanager
async def lifespan(application: FastAPI):  # type: ignore[no-untyped-def]
    """App lifespan: init DB and start scheduler."""
    log = get_logger("app")
    from app.database import init_db

    await init_db()
    log.info("database_ready")

    # Start scheduler
    from app.services.scheduler import create_scheduler, register_jobs

    scheduler = create_scheduler()

    # Shared alert engine instance (persists daily fired state)
    from app.services.alerting import AlertEngine

    _alert_engine = AlertEngine()

    async def poll_and_alert() -> None:
        """Poll quotes and evaluate alert rules."""
        from app.database import get_db
        from app.services.alerting import ONE_SHOT_ALERT_TYPES, AlertRule
        from app.services.market_data import get_realtime_quotes
        from app.services.push import PushPlusClient, format_alert_message
        from app.services.trading_calendar import should_poll

        if not await should_poll():
            return

        async with get_db() as db:
            cursor = await db.execute("SELECT code FROM stocks")
            rows = await cursor.fetchall()
            codes = [r["code"] for r in rows]
            if not codes:
                return

            quotes = await get_realtime_quotes(codes)
            if not quotes:
                return

            cursor = await db.execute("SELECT * FROM alert_rules WHERE enabled = 1")
            rule_rows = await cursor.fetchall()
            rules = [
                AlertRule(
                    id=r["id"],
                    stock_code=r["stock_code"],
                    stock_name=r["stock_name"],
                    alert_type=r["alert_type"],
                    threshold=r["threshold"],
                    direction=r["direction"],
                )
                for r in rule_rows
            ]

        if not rules:
            return

        triggered = await _alert_engine.evaluate(quotes, rules)
        if not triggered:
            return

        # Handle one-shot alerts: disable after triggering
        for alert in triggered:
            if alert.rule.alert_type in ONE_SHOT_ALERT_TYPES:
                from datetime import datetime
                from zoneinfo import ZoneInfo

                now_str = datetime.now(
                    tz=ZoneInfo("Asia/Shanghai")
                ).strftime("%m-%d %H:%M")
                async with get_db() as db:
                    await db.execute(
                        "UPDATE alert_rules SET enabled = 0, triggered_at = ?"
                        " WHERE id = ?",
                        (now_str, alert.rule.id),
                    )
                    await db.commit()
                log.info(
                    "one_shot_alert_disabled",
                    rule_id=alert.rule.id,
                    code=alert.rule.stock_code,
                )

        settings = get_settings()
        if not settings.pushplus_token:
            return

        push_client = PushPlusClient(settings.pushplus_token)
        for alert in triggered:
            title, content = format_alert_message(
                stock_name=alert.rule.stock_name,
                stock_code=alert.rule.stock_code,
                alert_type=alert.rule.alert_type,
                current_value=alert.current_value,
                threshold=alert.rule.threshold,
            )
            await push_client.queue_alert(title, content)
        await push_client.flush()

    async def daily_digest() -> None:
        """Send daily market summary at 15:05 CST."""
        from app.database import get_db
        from app.services.market_data import get_realtime_quotes
        from app.services.push import PushPlusClient

        settings = get_settings()
        if not settings.pushplus_token:
            return

        async with get_db() as db:
            cursor = await db.execute(
                "SELECT code, name FROM stocks ORDER BY sort_order"
            )
            rows = await cursor.fetchall()
            codes = [r["code"] for r in rows]

        if not codes:
            return

        quotes = await get_realtime_quotes(codes)
        lines = ["📊 今日行情汇总\n"]
        for q in quotes:
            direction = "🔴" if q.change_pct >= 0 else "🟢"
            lines.append(f"{direction} {q.name} ¥{q.price:.2f} ({q.change_pct:+.2f}%)")
        lines.append("\n⚠️ 以上信息仅供参考，不构成投资建议")

        client = PushPlusClient(settings.pushplus_token)
        await client.send_alert("📊 收盘行情汇总", "\n".join(lines))

    async def refresh_calendar() -> None:
        from app.services.trading_calendar import load_trade_dates

        await load_trade_dates()

    async def health_check() -> None:
        """Daily health check at 09:00 CST: test AKShare, PushPlus, data freshness.

        Pushes an alert if anything fails.
        """
        log.info("daily_health_check", status="running")
        from app.services.cache import get_cache

        cache = get_cache()
        await cache.cleanup_expired()
        failures: list[str] = []

        # Test AKShare connectivity
        try:
            import asyncio as _aio

            import akshare as ak

            df = await _aio.to_thread(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                failures.append("AKShare: 返回空数据")
            else:
                log.info("health_akshare_ok", rows=len(df))
        except Exception as exc:
            failures.append(f"AKShare: {exc}")
            log.error("health_akshare_failed", error=str(exc))

        # Test PushPlus token validity
        settings = get_settings()
        if not settings.pushplus_token:
            failures.append("PushPlus: Token未配置")
        else:
            log.info("health_pushplus_token_set")

        # Check data freshness — any quotes cached?
        cached_quotes = await cache.get("quotes:all")
        if cached_quotes is None:
            log.info("health_no_cached_quotes", note="expected before market open")
        else:
            log.info("health_quotes_cached", count=len(cached_quotes))

        # Push alert if any failures
        if failures and settings.pushplus_token:
            from app.services.push import PushPlusClient

            client = PushPlusClient(settings.pushplus_token)
            title = "⚠️ 系统健康检查异常"
            content = "以下组件异常:\n" + "\n".join(
                f"• {f}" for f in failures
            )
            content += "\n\n请及时检查系统状态"
            await client.send_alert(title, content)
            log.warning("health_check_failures_pushed", failures=failures)

        log.info("daily_health_check", status="complete", failures=len(failures))

    async def check_news() -> None:
        """Check for breaking news every 5 minutes, dedup by headline hash."""
        import hashlib

        from app.database import get_db
        from app.services.market_data import get_stock_news
        from app.services.push import PushPlusClient
        from app.services.trading_calendar import should_poll

        if not await should_poll():
            return

        settings = get_settings()
        if not settings.pushplus_token:
            return

        async with get_db() as db:
            cursor = await db.execute("SELECT code, name FROM stocks")
            stocks = await cursor.fetchall()

        if not stocks:
            return

        new_alerts: list[tuple[str, str]] = []
        for stock in stocks:
            code = stock["code"]
            name = stock["name"]
            news_items = await get_stock_news(code, limit=5)
            for item in news_items:
                h = hashlib.md5(item.title.encode()).hexdigest()  # noqa: S324
                async with get_db() as db:
                    cursor = await db.execute(
                        "SELECT 1 FROM news_alerts_seen WHERE headline_hash = ?",
                        (h,),
                    )
                    if await cursor.fetchone():
                        continue
                    await db.execute(
                        "INSERT OR IGNORE INTO news_alerts_seen"
                        " (headline_hash, stock_code, title) VALUES (?, ?, ?)",
                        (h, code, item.title),
                    )
                    await db.commit()
                new_alerts.append((name, item.title))

        if not new_alerts:
            return

        client = PushPlusClient(settings.pushplus_token)
        lines = ["📰 资讯快报\n"]
        for name, title in new_alerts[:10]:
            lines.append(f"• {name}: {title}")
        lines.append("\n⚠️ 以上信息仅供参考，不构成投资建议")
        await client.send_alert("📰 资讯快报", "\n".join(lines))
        log.info("news_alerts_sent", count=len(new_alerts))

    async def reset_daily_alerts() -> None:
        """Reset daily alert fired state at 09:30 CST."""
        _alert_engine.reset_daily_fired()

    async def refresh_sector_rotation() -> None:
        """Refresh sector rotation prediction at 09:00 CST."""
        from app.services.sector_rotation import predict_sector_rotation

        await predict_sector_rotation()
        log.info("sector_rotation_refreshed")

    async def check_capital_flow() -> None:
        """Check for large capital inflows every 5 min during trading hours."""
        from app.services.capital_flow import check_and_alert_capital_flow

        await check_and_alert_capital_flow()

    register_jobs(
        scheduler, poll_and_alert, daily_digest, refresh_calendar, health_check,
        check_news,
        reset_daily_alerts_func=reset_daily_alerts,
        refresh_sector_rotation_func=refresh_sector_rotation,
        check_capital_flow_func=check_capital_flow,
    )
    scheduler.start()
    log.info("scheduler_started")

    yield

    scheduler.shutdown(wait=False)
    log.info("scheduler_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("app")

    application = FastAPI(
        title="A股智能监控系统",
        description="A-share stock monitoring with real-time alerts",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local dev
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structlog request logging middleware with request_id tracing
    @application.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = generate_request_id()
        bind_request_id(request_id)
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        log.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        clear_request_context()
        return response

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    # Register API routers
    from app.routers.ai import router as ai_router
    from app.routers.capital_flow import router as capital_flow_router
    from app.routers.stocks import router as stocks_router
    from app.routers.watchlist import router as watchlist_router

    application.include_router(stocks_router)
    application.include_router(watchlist_router)
    application.include_router(ai_router)
    application.include_router(capital_flow_router)

    return application


# Module-level app instance for uvicorn and eval import_check
app = create_app()
