"""AI analysis and screening API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.logging import get_logger

log = get_logger("api.ai")

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ScreenRequest(BaseModel):
    query: str | None = None
    preset: str | None = None


@router.post("/analyze/{code}")
async def analyze_stock(code: str):
    """Run AI analysis on a stock via DeepSeek."""
    from app.services.ai import analyze_stock as _analyze

    result = await _analyze(code)
    return result


@router.post("/summarize-news/{code}")
async def summarize_news(code: str):
    """Summarize recent news for a stock via DeepSeek."""
    from app.services.ai import summarize_news as _summarize

    result = await _summarize(code)
    return result


@router.post("/push-analysis/{code}")
async def push_analysis(code: str):
    """Push AI analysis to WeChat via PushPlus."""
    from app.config import get_settings
    from app.services.ai import analyze_stock as _analyze
    from app.services.push import PushPlusClient

    result = await _analyze(code)
    analysis = result.get("analysis", "")
    if not analysis:
        return {"status": "error", "message": "分析结果为空"}

    settings = get_settings()
    if not settings.pushplus_token:
        return {"status": "error", "message": "PushPlus Token未配置"}

    client = PushPlusClient(settings.pushplus_token)
    title = f"📊 AI分析 - {code}"
    ok = await client.send_alert(title, analysis)
    return {"status": "ok" if ok else "error"}


@router.post("/screen")
async def screen_stocks(req: ScreenRequest):
    """Screen stocks by AI-parsed criteria or predefined filter."""
    from app.services.screener import screen_stocks as _screen

    result = await _screen(query=req.query, preset=req.preset)
    return result


@router.get("/presets")
async def get_presets():
    """Get predefined screening filters."""
    from app.services.screener import PREDEFINED_FILTERS

    return {
        "presets": [
            {"name": k, "description": v["description"]}
            for k, v in PREDEFINED_FILTERS.items()
        ]
    }


@router.get("/sector-rotation")
async def get_sector_rotation():
    """Get sector rotation prediction from AI."""
    from app.services.sector_rotation import predict_sector_rotation

    result = await predict_sector_rotation()
    return result


@router.get("/capital-flow/top")
async def get_capital_flow_top():
    """Get today's top capital inflow stocks."""
    from app.services.capital_flow import get_top_capital_flow

    result = await get_top_capital_flow()
    return result
