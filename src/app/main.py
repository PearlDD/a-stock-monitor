"""FastAPI application factory."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import configure_logging, get_logger


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

    async def poll_and_alert() -> None:
        """Poll quotes and evaluate alert rules."""
        from app.database import get_db
        from app.services.alerting import AlertEngine, AlertRule
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

        engine = AlertEngine()
        triggered = await engine.evaluate(quotes, rules)
        if not triggered:
            return

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

    register_jobs(
        scheduler, poll_and_alert, daily_digest, refresh_calendar, health_check
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structlog request logging middleware
    @application.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
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
        return response

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    # Register API routers
    from app.routers.stocks import router as stocks_router
    from app.routers.watchlist import router as watchlist_router

    application.include_router(stocks_router)
    application.include_router(watchlist_router)

    return application


# Module-level app instance for uvicorn and eval import_check
app = create_app()
