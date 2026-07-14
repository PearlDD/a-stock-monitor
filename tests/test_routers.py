"""Tests for API router endpoints (watchlist, stocks, AI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import create_app


@pytest.fixture
async def test_db(tmp_path):
    """Initialize a test database."""
    db_path = str(tmp_path / "test.db")
    import os
    os.environ["DATABASE_PATH"] = db_path
    await init_db(db_path)
    yield db_path
    os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def client(test_db):
    """Test client with initialized DB, no network calls."""
    app = create_app()
    return TestClient(app)


class TestWatchlistRouter:
    def test_list_empty_watchlist(self, client: TestClient):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        assert resp.json()["stocks"] == []

    def test_add_and_list_stock(self, client: TestClient):
        resp = client.post(
            "/api/watchlist",
            json={"code": "600519", "name": "贵州茅台", "market": "SH"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = client.get("/api/watchlist")
        stocks = resp.json()["stocks"]
        assert len(stocks) == 1
        assert stocks[0]["code"] == "600519"
        assert stocks[0]["name"] == "贵州茅台"

    def test_remove_stock(self, client: TestClient):
        client.post(
            "/api/watchlist",
            json={"code": "000858", "name": "五粮液"},
        )
        resp = client.delete("/api/watchlist/000858")
        assert resp.status_code == 200

        resp = client.get("/api/watchlist")
        assert len(resp.json()["stocks"]) == 0

    def test_search_stocks(self, client: TestClient):
        client.post("/api/watchlist", json={"code": "600519", "name": "贵州茅台"})
        client.post("/api/watchlist", json={"code": "000858", "name": "五粮液"})

        resp = client.get("/api/search", params={"q": "茅台"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["code"] == "600519"


class TestAlertRouter:
    def test_create_and_list_alert(self, client: TestClient):
        # Add stock first
        client.post("/api/watchlist", json={"code": "600519", "name": "贵州茅台"})

        resp = client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "price_pct_change",
                "threshold": 5.0,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["id"] is not None

        resp = client.get("/api/alerts")
        alerts = resp.json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["stock_code"] == "600519"
        assert alerts[0]["threshold"] == 5.0

    def test_invalid_alert_type(self, client: TestClient):
        resp = client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "invalid_type",
                "threshold": 5.0,
            },
        )
        assert resp.status_code == 400

    def test_update_alert(self, client: TestClient):
        client.post("/api/watchlist", json={"code": "600519", "name": "贵州茅台"})
        resp = client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "price_target",
                "threshold": 1800.0,
            },
        )
        alert_id = resp.json()["id"]

        resp = client.put(
            f"/api/alerts/{alert_id}",
            json={"threshold": 2000.0, "enabled": False},
        )
        assert resp.status_code == 200

        resp = client.get("/api/alerts")
        alert = resp.json()["alerts"][0]
        assert alert["threshold"] == 2000.0
        assert alert["enabled"] is False

    def test_delete_alert(self, client: TestClient):
        client.post("/api/watchlist", json={"code": "600519", "name": "贵州茅台"})
        resp = client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "limit_up",
                "threshold": 0,
            },
        )
        alert_id = resp.json()["id"]

        resp = client.delete(f"/api/alerts/{alert_id}")
        assert resp.status_code == 200

        resp = client.get("/api/alerts")
        assert len(resp.json()["alerts"]) == 0


_MKT = "app.services.market_data"


def _mock_mkt(fn_name, retval):
    return patch(f"{_MKT}.{fn_name}", new_callable=AsyncMock, return_value=retval)


class TestStockRouter:
    def test_get_financials_empty(self, client: TestClient):
        with _mock_mkt("get_financial_summary", None):
            resp = client.get("/api/stocks/600519/financials")
            assert resp.status_code == 200
            assert resp.json()["financials"] is None

    def test_get_history_empty(self, client: TestClient):
        with _mock_mkt("get_price_history", []):
            resp = client.get("/api/stocks/600519/history")
            assert resp.status_code == 200
            assert resp.json()["history"] == []

    def test_get_announcements_empty(self, client: TestClient):
        with _mock_mkt("get_announcements", []):
            resp = client.get("/api/stocks/600519/announcements")
            assert resp.status_code == 200
            assert resp.json()["announcements"] == []

    def test_get_news_empty(self, client: TestClient):
        with _mock_mkt("get_stock_news", []):
            resp = client.get("/api/stocks/600519/news")
            assert resp.status_code == 200
            assert resp.json()["news"] == []

    def test_get_quotes_empty(self, client: TestClient):
        with _mock_mkt("get_realtime_quotes", []):
            resp = client.get(
                "/api/stocks/quotes", params={"codes": "600519"}
            )
            assert resp.status_code == 200
            assert resp.json()["quotes"] == []


class TestSettingsRouter:
    def test_get_settings(self, client: TestClient):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "pushplus_token_masked" in data
        assert "pushplus_token_set" in data

    def test_get_push_quota(self, client: TestClient):
        resp = client.get("/api/push-quota")
        assert resp.status_code == 200
        data = resp.json()
        assert "used" in data
        assert "limit" in data
        assert data["limit"] == 180

    def test_get_setup_guide(self, client: TestClient):
        resp = client.get("/api/setup")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["steps"]) == 5
        assert len(data["notes"]) == 3

    def test_health_endpoint(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_request_id_header(self, client: TestClient):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) == 12


class TestAIRouter:
    def test_get_presets(self, client: TestClient):
        resp = client.get("/api/ai/presets")
        assert resp.status_code == 200
        presets = resp.json()["presets"]
        assert len(presets) == 3
        names = [p["name"] for p in presets]
        assert "低估值蓝筹" in names
        assert "近期强势" in names
        assert "高股息" in names

    def test_screen_no_criteria(self, client: TestClient):
        resp = client.post("/api/ai/screen", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
