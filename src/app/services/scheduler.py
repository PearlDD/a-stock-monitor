"""APScheduler job configuration.

Jobs:
  - poll_and_alert: every minute during trading hours (CronTrigger)
  - daily_digest: 15:05 CST
  - refresh_calendar: 06:00 CST
  - health_check: 09:00 CST

Single uvicorn worker constraint: APScheduler runs per-worker.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.logging import get_logger

log = get_logger("scheduler")

SHANGHAI_TZ_STR = "Asia/Shanghai"


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler(
        timezone=SHANGHAI_TZ_STR,
        job_defaults={
            "max_instances": 1,
            "misfire_grace_time": 30,
        },
    )
    return scheduler


def register_jobs(
    scheduler: AsyncIOScheduler,
    poll_func,  # type: ignore[no-untyped-def]
    digest_func,  # type: ignore[no-untyped-def]
    refresh_calendar_func,  # type: ignore[no-untyped-def]
    health_check_func,  # type: ignore[no-untyped-def]
) -> None:
    """Register all scheduled jobs.

    All use CronTrigger (not IntervalTrigger) per project constraints.
    """
    # Poll and alert every minute during trading hours
    # Morning: 9:30-11:30, Afternoon: 13:00-15:00
    scheduler.add_job(
        poll_func,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-11,13-14",
            minute="*",
            timezone=SHANGHAI_TZ_STR,
        ),
        id="poll_and_alert",
        name="Poll quotes and evaluate alerts",
        replace_existing=True,
    )

    # Also cover 15:00 specifically (market close)
    scheduler.add_job(
        poll_func,
        CronTrigger(
            day_of_week="mon-fri",
            hour="15",
            minute="0",
            timezone=SHANGHAI_TZ_STR,
        ),
        id="poll_and_alert_close",
        name="Poll at market close",
        replace_existing=True,
    )

    # Daily digest at 15:05 CST
    scheduler.add_job(
        digest_func,
        CronTrigger(
            day_of_week="mon-fri",
            hour=15,
            minute=5,
            timezone=SHANGHAI_TZ_STR,
        ),
        id="daily_digest",
        name="Send daily market digest",
        replace_existing=True,
    )

    # Refresh trading calendar at 06:00 CST
    scheduler.add_job(
        refresh_calendar_func,
        CronTrigger(
            hour=6,
            minute=0,
            timezone=SHANGHAI_TZ_STR,
        ),
        id="refresh_calendar",
        name="Refresh trading calendar",
        replace_existing=True,
    )

    # Daily health check at 09:00 CST
    scheduler.add_job(
        health_check_func,
        CronTrigger(
            day_of_week="mon-fri",
            hour=9,
            minute=0,
            timezone=SHANGHAI_TZ_STR,
        ),
        id="health_check",
        name="Daily system health check",
        replace_existing=True,
    )

    log.info("scheduler_jobs_registered", job_count=len(scheduler.get_jobs()))
