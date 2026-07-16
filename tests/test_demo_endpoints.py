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


class TestSectorRotationDemo:
    def test_returns_predictions_in_mock_mode(self, mock_client):
        resp = mock_client.get("/api/ai/sector-rotation")
        assert resp.status_code == 200
        data = resp.json()
        assert "sectors" in data
        sectors = data["sectors"]
        assert 3 <= len(sectors) <= 5
        for p in sectors:
            assert "sector" in p
            assert "reason" in p
            assert "leaders" in p
            assert len(p["leaders"]) > 0


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


class TestAIAnalyzeDemo:
    def test_returns_analysis_in_mock_mode(self, mock_client):
        resp = mock_client.post("/api/ai/analyze/600519")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data
        analysis = data["analysis"]
        assert "近期走势" in analysis
        assert "基本面" in analysis
        assert "风险提示" in analysis
        assert "仅供参考" in analysis

    def test_works_for_any_stock_code(self, mock_client):
        resp = mock_client.post("/api/ai/analyze/000001")
        assert resp.status_code == 200
        assert "近期走势" in resp.json()["analysis"]


class TestAIScreenDemo:
    def test_returns_stocks_for_query(self, mock_client):
        resp = mock_client.post("/api/ai/screen", json={"query": "低估值"})
        assert resp.status_code == 200
        data = resp.json()
        stocks = data["stocks"]
        assert 5 <= len(stocks) <= 8
        for s in stocks:
            assert "code" in s
            assert "name" in s
            assert "price" in s

    def test_returns_filtered_for_preset(self, mock_client):
        resp = mock_client.post("/api/ai/screen", json={"preset": "低估值蓝筹"})
        assert resp.status_code == 200
        data = resp.json()
        stocks = data["stocks"]
        assert len(stocks) > 0
        for s in stocks:
            assert s["pe_ratio"] <= 15
            assert s["pb_ratio"] <= 2

    def test_no_criteria_returns_error(self, mock_client):
        resp = mock_client.post("/api/ai/screen", json={})
        assert resp.status_code == 200
        assert "error" in resp.json()
