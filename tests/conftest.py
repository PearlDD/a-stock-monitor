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
    """Create a MockProvider instance for testing."""
    return MockProvider()
