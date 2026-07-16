"""Watchlist and alert CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.logging import get_logger

log = get_logger("api.watchlist")

router = APIRouter(prefix="/api", tags=["watchlist"])


class StockAdd(BaseModel):
    code: str
    name: str
    market: str = ""
    sector: str = ""


class AlertRuleCreate(BaseModel):
    stock_code: str
    stock_name: str = ""
    alert_type: str
    threshold: float
    direction: str = "above"


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None
    direction: str | None = None


class SettingsUpdate(BaseModel):
    pushplus_token: str = ""


# --- Watchlist CRUD ---


@router.get("/watchlist")
async def list_watchlist():
    """List all stocks in watchlist."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM stocks ORDER BY sort_order, created_at"
        )
        rows = await cursor.fetchall()
        return {
            "stocks": [
                {
                    "code": r["code"],
                    "name": r["name"],
                    "market": r["market"],
                    "sector": r["sector"],
                }
                for r in rows
            ]
        }


@router.post("/watchlist")
async def add_to_watchlist(stock: StockAdd):
    """Add a stock to watchlist."""
    async with get_db() as db:
        try:
            sql = (
                "INSERT OR REPLACE INTO stocks"
                " (code, name, market, sector)"
                " VALUES (?, ?, ?, ?)"
            )
            await db.execute(
                sql,
                (stock.code, stock.name, stock.market, stock.sector),
            )
            await db.commit()
            return {"status": "ok", "code": stock.code}
        except Exception as e:
            log.error("watchlist_add_failed", code=stock.code, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{code}")
async def remove_from_watchlist(code: str):
    """Remove a stock from watchlist."""
    async with get_db() as db:
        await db.execute("DELETE FROM alert_rules WHERE stock_code = ?", (code,))
        await db.execute("DELETE FROM stocks WHERE code = ?", (code,))
        await db.commit()
        return {"status": "ok"}


# --- Alert Rules CRUD ---


@router.get("/alerts")
async def list_alerts():
    """List all alert rules."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM alert_rules ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return {
            "alerts": [
                {
                    "id": r["id"],
                    "stock_code": r["stock_code"],
                    "stock_name": r["stock_name"],
                    "alert_type": r["alert_type"],
                    "threshold": r["threshold"],
                    "direction": r["direction"],
                    "enabled": bool(r["enabled"]),
                    "triggered_at": r["triggered_at"],
                }
                for r in rows
            ]
        }


@router.post("/alerts")
async def create_alert(rule: AlertRuleCreate):
    """Create a new alert rule."""
    valid_types = {
        "price_target",
        "limit_up",
        "limit_down",
        "volume_spike",
    }
    if rule.alert_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Invalid alert_type. Must be one of: {valid_types}"
        )

    async with get_db() as db:
        sql = (
            "INSERT INTO alert_rules"
            " (stock_code, stock_name, alert_type, threshold, direction)"
            " VALUES (?, ?, ?, ?, ?)"
        )
        cursor = await db.execute(
            sql,
            (
                rule.stock_code,
                rule.stock_name,
                rule.alert_type,
                rule.threshold,
                rule.direction,
            ),
        )
        await db.commit()
        return {"status": "ok", "id": cursor.lastrowid}


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: int, update: AlertRuleUpdate):
    """Update an alert rule."""
    async with get_db() as db:
        sets: list[str] = []
        params: list[Any] = []
        if update.enabled is not None:
            sets.append("enabled = ?")
            params.append(int(update.enabled))
        if update.threshold is not None:
            sets.append("threshold = ?")
            params.append(update.threshold)
        if update.direction is not None:
            sets.append("direction = ?")
            params.append(update.direction)
        if not sets:
            return {"status": "ok"}
        params.append(alert_id)
        await db.execute(
            f"UPDATE alert_rules SET {', '.join(sets)} WHERE id = ?", params
        )
        await db.commit()
        return {"status": "ok"}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    """Delete an alert rule."""
    async with get_db() as db:
        await db.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
        await db.commit()
        return {"status": "ok"}


# --- Search ---


@router.get("/search")
async def search_stocks(q: str):
    """Search stocks by code or name (uses watchlist for now)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM stocks WHERE code LIKE ? OR name LIKE ? LIMIT 20",
            (f"%{q}%", f"%{q}%"),
        )
        rows = await cursor.fetchall()
        return {
            "results": [
                {"code": r["code"], "name": r["name"], "market": r["market"]}
                for r in rows
            ]
        }


# --- Settings ---


@router.get("/settings")
async def get_settings():
    """Get current settings."""
    from app.config import get_settings as _get_settings

    s = _get_settings()
    # Mask token for security
    token = s.pushplus_token
    masked = (
        f"{token[:4]}****{token[-4:]}" if len(token) > 8 else ("****" if token else "")
    )
    return {
        "pushplus_token_masked": masked,
        "pushplus_token_set": bool(token),
        "timezone": s.timezone,
        "ai_provider_analysis": s.ai_provider_analysis,
        "ai_provider_screening": s.ai_provider_screening,
        "ai_providers_configured": {
            "deepseek": bool(s.deepseek_api_key),
            "claude": bool(s.effective_claude_api_key),
        },
    }


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings (token stored in env, not DB for security)."""
    import os

    if settings.pushplus_token:
        os.environ["PUSHPLUS_TOKEN"] = settings.pushplus_token
    return {"status": "ok"}


@router.post("/test-push")
@router.post("/settings/test-push")
async def test_push():
    """Send a test push notification."""
    from app.config import get_settings as _get_settings
    from app.services.push import PushPlusClient

    s = _get_settings()
    if not s.pushplus_token:
        raise HTTPException(status_code=400, detail="PushPlus token not configured")

    client = PushPlusClient(s.pushplus_token)
    ok = await client.send_alert(
        "🔔 测试通知",
        "盯盘助手测试消息 - 推送配置成功！",
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Push test failed")
    return {"status": "ok", "message": "Test notification sent"}


@router.get("/push-quota")
@router.get("/push/quota")
async def get_push_quota():
    """Get current daily push usage."""
    from app.config import get_settings as _get_settings
    from app.services.push import DAILY_CAP, PushPlusClient

    client = PushPlusClient(_get_settings().pushplus_token)
    count = await client.get_daily_count()
    return {"used": count, "limit": DAILY_CAP, "remaining": DAILY_CAP - count}
