"""Application configuration via environment variables."""

from __future__ import annotations

from functools import cached_property

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # PushPlus WeChat push notifications
    pushplus_token: str = ""

    # DeepSeek API (OpenAI-compatible)
    deepseek_api_key: str = ""

    # Claude / Anthropic API
    claude_api_key: str = ""
    anthropic_api_key: str = ""  # alias for claude_api_key

    # AI provider routing
    ai_provider_analysis: str = "claude"  # provider for deep stock analysis
    ai_provider_screening: str = "deepseek"  # provider for screening/summarization

    # SQLite database
    database_url: str = "sqlite+aiosqlite:///data/stock_monitor.db"

    # Logging
    log_level: str = "INFO"

    # Timezone (server in US, user in China)
    timezone: str = "Asia/Shanghai"

    @cached_property
    def effective_claude_api_key(self) -> str:
        """Resolve Claude API key with ANTHROPIC_API_KEY fallback."""
        return self.claude_api_key or self.anthropic_api_key

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
