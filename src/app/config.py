"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    pushplus_token: str = ""
    database_url: str = "sqlite+aiosqlite:///data/stock_monitor.db"
    database_path: str = "data/stock_monitor.db"
    log_level: str = "INFO"
    pushplus_daily_limit: int = 180

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
