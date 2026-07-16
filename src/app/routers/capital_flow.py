"""Capital flow API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/capital-flow", tags=["capital-flow"])


@router.get("/top")
async def get_capital_flow_top():
    """Get today's top capital inflow stocks."""
    from app.services.capital_flow import get_top_capital_flow

    result = await get_top_capital_flow()
    return result
