"""Sector rotation prediction service (板块轮动预测).

Uses AKShare to fetch sector/industry data and capital flow,
then sends to AI for rotation prediction.
Results cached for 4 hours.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.logging import get_logger
from app.services.cache import get_cache

log = get_logger("sector_rotation")

SECTOR_CACHE_TTL = 14400  # 4 hours
SECTOR_CACHE_KEY = "sector_rotation:prediction"

AI_DISCLAIMER = "以上由AI预测，仅供参考，不构成投资建议"

SECTOR_PROMPT = (
    "根据以下板块近期表现和资金流向数据，预测下一轮可能轮动的板块，"
    "并推荐每个板块的龙头股。输出格式：板块名称、轮动理由、龙头股（代码+名称）。"
    "限3-5个板块。"
)


async def fetch_sector_data() -> dict[str, Any]:
    """Fetch sector performance and capital flow data from AKShare."""
    import akshare as ak

    sectors: list[dict] = []
    capital_flow: list[dict] = []

    try:
        df = await asyncio.to_thread(ak.stock_board_industry_name_ths)
        if df is not None and not df.empty:
            for _, row in df.head(30).iterrows():
                sectors.append({
                    "name": str(row.get("板块名称", row.get("name", ""))),
                    "change_pct": float(row.get("涨跌幅", row.get("change", 0)) or 0),
                    "turnover": float(row.get("换手率", 0) or 0),
                })
        log.info("sector_list_fetched", count=len(sectors))
    except Exception:
        log.error("sector_list_fetch_failed", exc_info=True)

    try:
        df = await asyncio.to_thread(
            ak.stock_sector_fund_flow_rank, indicator="今日"
        )
        if df is not None and not df.empty:
            for _, row in df.head(30).iterrows():
                capital_flow.append({
                    "sector": str(row.get("名称", "")),
                    "net_inflow": float(row.get("今日主力净流入-净额", 0) or 0),
                    "change_pct": float(row.get("今日涨跌幅", 0) or 0),
                })
        log.info("sector_capital_flow_fetched", count=len(capital_flow))
    except Exception:
        log.error("sector_capital_flow_fetch_failed", exc_info=True)

    return {"sectors": sectors, "capital_flow": capital_flow}


async def predict_sector_rotation() -> dict[str, Any]:
    """Predict sector rotation using AI analysis.

    Returns cached result if available (4-hour TTL).
    """
    cache = get_cache()
    cached = await cache.get(SECTOR_CACHE_KEY)
    if cached is not None:
        return {"predictions": cached, "cached": True, "disclaimer": AI_DISCLAIMER}

    data = await fetch_sector_data()

    if not data["sectors"] and not data["capital_flow"]:
        return {
            "predictions": [],
            "cached": False,
            "error": "无法获取板块数据",
            "disclaimer": AI_DISCLAIMER,
        }

    context_parts: list[str] = []
    if data["sectors"]:
        lines = [
            f"  {s['name']}: 涨跌幅{s['change_pct']:+.2f}%"
            for s in data["sectors"][:15]
        ]
        context_parts.append("板块表现:\n" + "\n".join(lines))

    if data["capital_flow"]:
        lines = []
        for cf in data["capital_flow"][:15]:
            inflow = cf["net_inflow"] / 1e8
            pct = cf["change_pct"]
            lines.append(
                f"  {cf['sector']}: "
                f"主力净流入{inflow:.2f}亿, "
                f"涨跌幅{pct:+.2f}%"
            )
        context_parts.append("资金流向:\n" + "\n".join(lines))

    context = "\n\n".join(context_parts)
    prompt = f"{SECTOR_PROMPT}\n\n{context}"

    try:
        from app.services.ai import _call_ai

        response = await _call_ai(prompt, task_type="analysis", max_chars=1000)
        predictions = _parse_predictions(response)
        await cache.set(SECTOR_CACHE_KEY, predictions, SECTOR_CACHE_TTL)
        log.info("sector_rotation_predicted", count=len(predictions))
        return {
            "predictions": predictions,
            "cached": False,
            "disclaimer": AI_DISCLAIMER,
        }
    except Exception:
        log.error("sector_rotation_prediction_failed", exc_info=True)
        return {
            "predictions": [],
            "cached": False,
            "error": "AI预测暂时不可用",
            "disclaimer": AI_DISCLAIMER,
        }


def _parse_predictions(text: str) -> list[dict[str, Any]]:
    """Parse AI response into structured predictions.

    Best-effort parsing: each prediction has sector, reason, leaders.
    Falls back to returning raw text as single prediction if parsing fails.
    """
    predictions: list[dict[str, Any]] = []
    if not text:
        return predictions

    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]

    current: dict[str, Any] | None = None
    for line in lines:
        # Lines starting with numbers or bullets likely start a new sector
        stripped = line.lstrip("0123456789.、）) -·*#")
        if not stripped:
            continue

        if any(line.startswith(prefix) for prefix in ("1", "2", "3", "4", "5")) or (
            line.startswith("**") and "板块" in line
        ):
            if current:
                predictions.append(current)
            sector = stripped.split("：")[0].split(":")[0].strip("*")
            current = {"sector": sector, "reason": "", "leaders": []}
            if "：" in stripped or ":" in stripped:
                sep = "：" if "：" in stripped else ":"
                current["reason"] = stripped.split(sep, 1)[1].strip()
        elif current is not None:
            has_code = any(
                c.isdigit() and len(c) == 6 for c in line.split()
            )
            if "龙头" in line or "代码" in line or has_code:
                import re

                codes = re.findall(r"(\d{6})", line)
                for code in codes:
                    pat = rf"{code}[^\w]*([^\d,，、\s]+)"
                    m = re.search(pat, line)
                    name = m.group(1).strip("()（）") if m else ""
                    current["leaders"].append(
                        {"code": code, "name": name}
                    )
            elif current["reason"]:
                current["reason"] += " " + stripped
            else:
                current["reason"] = stripped

    if current:
        predictions.append(current)

    # Fallback: return raw text if no structured parsing worked
    if not predictions and text.strip():
        predictions.append({
            "sector": "AI分析结果",
            "reason": text.strip(),
            "leaders": [],
        })

    return predictions[:5]
