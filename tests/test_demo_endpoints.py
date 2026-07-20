"""Tests for demo mode (DATA_MODE=mock) endpoint fixes."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.services.cache import get_cache


@pytest.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path
    await init_db(db_path)
    yield db_path
    os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def mock_client(test_db, monkeypatch):
    """Test client with DATA_MODE=mock."""
    monkeypatch.setenv("DATA_MODE", "mock")
    cache = get_cache()
    cache.clear()
    from app.main import create_app

    app = create_app()
    return TestClient(app)


class TestCapitalFlowDemo:
    def test_returns_stocks_in_mock_mode(self, mock_client):
        resp = mock_client.get("/api/capital-flow/top")
        assert resp.status_code == 200
        data = resp.json()
        assert "stocks" in data
        stocks = data["stocks"]
        assert len(stocks) == 10
        for s in stocks:
            assert "code" in s
            assert "name" in s
            assert "net_inflow" in s
            assert s["net_inflow"] > 0


class TestPushQuotaRoute:
    def test_push_quota_at_new_path(self, mock_client):
        resp = mock_client.get("/api/push/quota")
        assert resp.status_code == 200
        data = resp.json()
        assert "used" in data
        assert "limit" in data
        assert "remaining" in data
        assert data["limit"] == 180

    def test_push_quota_at_old_path(self, mock_client):
        resp = mock_client.get("/api/push-quota")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 180


class TestTestPushRoute:
    def test_test_push_at_new_path(self, mock_client, monkeypatch):
        from app.services import push

        async def _fake_send(self, title, content):
            return True

        monkeypatch.setattr(push.PushPlusClient, "send_alert", _fake_send)
        resp = mock_client.post("/api/settings/test-push")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_test_push_at_old_path(self, mock_client, monkeypatch):
        from app.services import push

        async def _fake_send(self, title, content):
            return True

        monkeypatch.setattr(push.PushPlusClient, "send_alert", _fake_send)
        resp = mock_client.post("/api/test-push")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_test_push_sends_correct_message(self, mock_client, monkeypatch):
        from app.services import push

        sent_messages = []

        async def _capture_send(self, title, content):
            sent_messages.append((title, content))
            return True

        monkeypatch.setattr(push.PushPlusClient, "send_alert", _capture_send)
        mock_client.post("/api/settings/test-push")
        assert len(sent_messages) == 1
        assert "盯盘助手测试消息" in sent_messages[0][1]
        assert "推送配置成功" in sent_messages[0][1]


