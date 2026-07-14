"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.mock import MockProvider


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_provider():
    """Create a MockProvider with some default data."""
    provider = MockProvider()
    provider.set_price(
        "600519", 1823.50, name="贵州茅台", change_pct=3.84, prev_close=1756.0,
    )
    provider.set_price(
        "000858", 168.20, name="五粮液", change_pct=-1.2, prev_close=170.24,
    )
    return provider
