"""Data providers for the A-share stock monitor."""

from app.providers.base import DataProvider
from app.providers.demo import DemoProvider
from app.providers.mock import MockProvider

__all__ = ["DataProvider", "DemoProvider", "MockProvider"]


def get_provider() -> DataProvider:
    """Return the appropriate data provider based on DATA_MODE setting."""
    from app.config import get_settings

    settings = get_settings()
    if settings.data_mode == "mock":
        return DemoProvider()
    # For 'live' mode, callers use AKShare directly (existing behavior)
    # This function is primarily for mock/demo mode routing
    from app.providers.akshare_ths import AKShareTHSProvider

    return AKShareTHSProvider()
