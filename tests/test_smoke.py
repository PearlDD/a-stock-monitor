"""Smoke tests for basic application functionality."""

from fastapi import FastAPI

from app.main import create_app


def test_create_app_returns_fastapi():
    """App factory returns a FastAPI instance."""
    app = create_app()
    assert isinstance(app, FastAPI)


def test_app_has_title():
    """App has the expected title."""
    app = create_app()
    assert "监控" in app.title


def test_health_endpoint(client):
    """Health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_import_app_module():
    """Core app modules are importable."""
    from app import config, database, main  # noqa: F401
