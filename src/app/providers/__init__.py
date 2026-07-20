"""Data providers for the A-share stock monitor."""

from app.providers.base import DataProvider
from app.providers.demo import DemoProvider
from app.providers.mock import MockProvider
from app.providers.tencent import TencentProvider

__all__ = ["DataProvider", "DemoProvider", "MockProvider", "TencentProvider"]


def get_provider() -> DataProvider:
    """Return the appropriate data provider based on settings."""
    from app.config import get_settings

    settings = get_settings()
    if settings.data_mode == "mock":
        return DemoProvider()
    if settings.data_source == "tencent":
        return TencentProvider()
    from app.providers.akshare_ths import AKShareTHSProvider

    return AKShareTHSProvider()
