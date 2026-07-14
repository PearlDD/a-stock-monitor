"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # PushPlus WeChat push notifications
    pushplus_token: str = ""

    # DeepSeek API (OpenAI-compatible)
    deepseek_api_key: str = ""

    # Redis for caching and dedup
    redis_url: str = "redis://localhost:6379/0"

    # SQLite database
    database_url: str = "sqlite+aiosqlite:///data/stock_monitor.db"

    # Logging
    log_level: str = "INFO"

    # Timezone (server in US, user in China)
    timezone: str = "Asia/Shanghai"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
