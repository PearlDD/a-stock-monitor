"""Data providers for the A-share stock monitor."""

from app.providers.base import DataProvider
from app.providers.mock import MockProvider

__all__ = ["DataProvider", "MockProvider"]
