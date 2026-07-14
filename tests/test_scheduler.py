"""Tests for APScheduler configuration."""

from unittest.mock import AsyncMock

from app.services.scheduler import create_scheduler, register_jobs


class TestSchedulerConfig:
    def test_create_scheduler(self):
        scheduler = create_scheduler()
        assert scheduler is not None
        assert scheduler.timezone.key == "Asia/Shanghai"  # type: ignore[union-attr]

    def test_register_jobs(self):
        scheduler = create_scheduler()
        poll = AsyncMock()
        digest = AsyncMock()
        refresh = AsyncMock()
        health = AsyncMock()

        register_jobs(scheduler, poll, digest, refresh, health)

        jobs = scheduler.get_jobs()
        job_ids = {j.id for j in jobs}
        assert "poll_and_alert" in job_ids
        assert "poll_and_alert_close" in job_ids
        assert "daily_digest" in job_ids
        assert "refresh_calendar" in job_ids
        assert "health_check" in job_ids

    def test_jobs_use_cron_trigger(self):
        """All jobs must use CronTrigger, not IntervalTrigger."""
        from apscheduler.triggers.cron import CronTrigger

        scheduler = create_scheduler()
        register_jobs(scheduler, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())

        for job in scheduler.get_jobs():
            assert isinstance(job.trigger, CronTrigger), (
                f"Job {job.id} must use CronTrigger, got {type(job.trigger).__name__}"
            )

    def test_job_defaults(self):
        """Verify scheduler job defaults are set correctly."""
        scheduler = create_scheduler()
        defaults = scheduler._job_defaults
        assert defaults.get("max_instances") == 1
        assert defaults.get("misfire_grace_time") == 30
