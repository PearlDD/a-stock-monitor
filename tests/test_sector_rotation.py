"""Tests for sector rotation prediction service."""

from __future__ import annotations

import pytest

from app.services.cache import get_cache
from app.services.sector_rotation import (
    AI_DISCLAIMER,
    SECTOR_CACHE_KEY,
    _parse_predictions,
    predict_sector_rotation,
)


@pytest.fixture(autouse=True)
def fresh_cache():
    cache = get_cache()
    cache.clear()
    yield
    cache.clear()


class TestParsePredictions:
    def test_empty_text(self):
        assert _parse_predictions("") == []

    def test_numbered_sectors(self):
        text = (
            "1. 新能源：政策支持，资金流入明显\n"
            "龙头股: 300750 宁德时代, 601012 隆基绿能\n"
            "2. 半导体：国产替代加速\n"
            "龙头股: 002371 北方华创"
        )
        result = _parse_predictions(text)
        assert len(result) == 2
        assert result[0]["sector"] == "新能源"
        assert "政策" in result[0]["reason"]
        assert len(result[0]["leaders"]) == 2
        assert result[0]["leaders"][0]["code"] == "300750"

    def test_fallback_raw_text(self):
        text = "这是一段没有结构化格式的分析文本"
        result = _parse_predictions(text)
        assert len(result) == 1
        assert result[0]["sector"] == "AI分析结果"

    def test_max_five_predictions(self):
        lines = []
        for i in range(8):
            lines.append(f"{i + 1}. 板块{i}：理由{i}")
        result = _parse_predictions("\n".join(lines))
        assert len(result) <= 5


class TestPredictSectorRotation:
    @pytest.mark.asyncio
    async def test_returns_cached_result(self):
        """Should return cached predictions without calling AI."""
        cache = get_cache()
        cached_data = [{"sector": "缓存板块", "reason": "test", "leaders": []}]
        await cache.set(SECTOR_CACHE_KEY, cached_data, 3600)

        result = await predict_sector_rotation()
        assert result["cached"] is True
        assert result["predictions"] == cached_data
        assert result["disclaimer"] == AI_DISCLAIMER

    @pytest.mark.asyncio
    async def test_no_data_returns_empty(self, monkeypatch):
        """Should return empty if AKShare returns nothing."""
        import app.services.sector_rotation as mod

        async def _empty_data():
            return {"sectors": [], "capital_flow": []}

        monkeypatch.setattr(mod, "fetch_sector_data", _empty_data)

        result = await predict_sector_rotation()
        assert result["predictions"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ai_call_with_data(self, monkeypatch):
        """Should call AI when data is available."""
        import app.services.sector_rotation as mod

        async def _mock_data():
            return {
                "sectors": [
                    {"name": "新能源", "change_pct": 3.5, "turnover": 5.2},
                ],
                "capital_flow": [
                    {"sector": "新能源", "net_inflow": 1e9, "change_pct": 3.5},
                ],
            }

        async def _mock_ai(prompt, task_type, max_chars=500):
            return "1. 新能源：资金持续流入\n龙头股: 300750 宁德时代"

        monkeypatch.setattr(mod, "fetch_sector_data", _mock_data)
        monkeypatch.setattr("app.services.ai._call_ai", _mock_ai)

        result = await predict_sector_rotation()
        assert result["cached"] is False
        assert len(result["predictions"]) >= 1
        assert result["disclaimer"] == AI_DISCLAIMER

    @pytest.mark.asyncio
    async def test_ai_failure_returns_error(self, monkeypatch):
        """Should handle AI failure gracefully."""
        import app.services.sector_rotation as mod

        async def _mock_data():
            return {
                "sectors": [{"name": "Test", "change_pct": 1.0, "turnover": 2.0}],
                "capital_flow": [],
            }

        async def _mock_ai_fail(prompt, task_type, max_chars=500):
            raise RuntimeError("AI down")

        monkeypatch.setattr(mod, "fetch_sector_data", _mock_data)
        monkeypatch.setattr("app.services.ai._call_ai", _mock_ai_fail)

        result = await predict_sector_rotation()
        assert result["predictions"] == []
        assert "error" in result
