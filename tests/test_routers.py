"""Tests for API router endpoints (watchlist, stocks, AI)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.services.market_data as market_data
from app.database import init_db
from app.main import create_app
from app.services.cache import get_cache


@pytest.fixture
async def test_db(tmp_path):
    """Initialize a test database."""
    import os

    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path
    await init_db(db_path)
    yield db_path
    os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def client(test_db):
    """Test client with initialized DB."""
    cache = get_cache()
    cache.clear()
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
        assert resp.status_code == 200
        assert resp.json()["id"] is not None

        resp = client.get("/api/alerts")
        alerts = resp.json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["stock_code"] == "600519"
        assert alerts[0]["threshold"] == 1800.0

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

    def test_price_pct_change_rejected(self, client: TestClient):
        """price_pct_change alert type should be rejected."""
        resp = client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "price_pct_change",
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


class TestStockRouter:
    def test_get_financials_empty(self, client: TestClient, monkeypatch):
        async def _no_financials(*a, **kw):
            return None

        monkeypatch.setattr(market_data, "get_financial_summary", _no_financials)
        resp = client.get("/api/stocks/600519/financials")
        assert resp.status_code == 200
        assert resp.json()["financials"] is None

    def test_get_history_empty(self, client: TestClient, monkeypatch):
        async def _no_history(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_price_history", _no_history)
        resp = client.get("/api/stocks/600519/history")
        assert resp.status_code == 200
        assert resp.json()["history"] == []

    def test_get_announcements_empty(self, client: TestClient, monkeypatch):
        async def _no_ann(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_announcements", _no_ann)
        resp = client.get("/api/stocks/600519/announcements")
        assert resp.status_code == 200
        assert resp.json()["announcements"] == []

    def test_get_news_empty(self, client: TestClient, monkeypatch):
        async def _no_news(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_stock_news", _no_news)
        resp = client.get("/api/stocks/600519/news")
        assert resp.status_code == 200
        assert resp.json()["news"] == []

    def test_get_quotes_empty(self, client: TestClient, monkeypatch):
        async def _no_quotes(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_realtime_quotes", _no_quotes)
        resp = client.get("/api/stocks/quotes", params={"codes": "600519"})
        assert resp.status_code == 200
        assert resp.json()["quotes"] == []

    def test_get_stock_info(self, client: TestClient, monkeypatch):
        from app.models.market import StockInfo

        async def _mock_info(*a, **kw):
            return StockInfo(
                code="600519", name="贵州茅台", sector="白酒", market="SH"
            )

        monkeypatch.setattr(market_data, "get_stock_info", _mock_info)
        resp = client.get("/api/stocks/600519/info")
        assert resp.status_code == 200
        info = resp.json()["info"]
        assert info["code"] == "600519"
        assert info["name"] == "贵州茅台"


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

    def test_setup_guide_removed(self, client: TestClient):
        resp = client.get("/api/setup")
        assert resp.status_code in (404, 405)

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

    def test_analyze_no_key(self, client: TestClient, monkeypatch):
        async def _no_quotes(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_realtime_quotes", _no_quotes)
        resp = client.post("/api/ai/analyze/600519")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data

    def test_summarize_no_news(self, client: TestClient, monkeypatch):
        async def _no_news(*a, **kw):
            return []

        monkeypatch.setattr(market_data, "get_stock_news", _no_news)
        resp = client.post("/api/ai/summarize-news/600519")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_sector_rotation_endpoint(self, client: TestClient, monkeypatch):
        import app.services.sector_rotation as sector_mod

        async def _mock_predict(*a, **kw):
            return {
                "predictions": [{"sector": "新能源", "reason": "test", "leaders": []}],
                "cached": False,
                "disclaimer": "以上由AI预测，仅供参考，不构成投资建议",
            }

        monkeypatch.setattr(sector_mod, "predict_sector_rotation", _mock_predict)
        resp = client.get("/api/ai/sector-rotation")
        assert resp.status_code == 200
        data = resp.json()
        assert "predictions" in data
        assert "disclaimer" in data

    def test_capital_flow_top_endpoint(self, client: TestClient, monkeypatch):
        import app.services.capital_flow as flow_mod

        async def _mock_top(*a, **kw):
            return {
                "stocks": [{
                    "code": "600519", "name": "贵州茅台",
                    "net_inflow": 1e8, "change_pct": 3.5,
                }],
                "cached": False,
            }

        monkeypatch.setattr(flow_mod, "get_top_capital_flow", _mock_top)
        resp = client.get("/api/ai/capital-flow/top")
        assert resp.status_code == 200
        data = resp.json()
        assert "stocks" in data
        assert len(data["stocks"]) == 1

    def test_alert_triggered_at_field(self, client: TestClient):
        """Alert list should include triggered_at field."""
        client.post("/api/watchlist", json={"code": "600519", "name": "贵州茅台"})
        client.post(
            "/api/alerts",
            json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "alert_type": "price_target",
                "threshold": 1900.0,
            },
        )
        resp = client.get("/api/alerts")
        alert = resp.json()["alerts"][0]
        assert "triggered_at" in alert
        assert alert["triggered_at"] is None
