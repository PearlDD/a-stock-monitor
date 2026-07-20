"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # PushPlus WeChat push notifications
    pushplus_token: str = ""

    # SQLite database
    database_url: str = "sqlite+aiosqlite:///data/stock_monitor.db"

    # Data mode: 'mock' for demo data (no AKShare), 'live' for real data
    data_mode: str = "live"

    # Data source for real-time quotes: 'tencent' or 'akshare' (default: tencent)
    data_source: str = "tencent"

    # Logging
    log_level: str = "INFO"

    # Timezone (server in US, user in China)
    timezone: str = "Asia/Shanghai"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
