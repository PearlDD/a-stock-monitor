"""Tests for TencentProvider — mock HTTP responses, no network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.providers.tencent import (
    TencentProvider,
    _market_prefix,
    _parse_tencent_response,
)

# Sample Tencent Finance API response (GBK-encoded text, already decoded)
# Field layout: 0=market, 1=name, 2=code, 3=price, 4=prev_close, 5=open,
# 6=volume, 7-8=buy/sell vol, 9-28=bid/ask, 29=unused, 30=timestamp,
# 31=change_amount, 32=change_pct, 33=high, 34=low,
# 35=price/vol/amt, 36=vol, 37=amount
SAMPLE_RESPONSE = (
    'v_sh600519="1~贵州茅台~600519~1800.00~1785.00~1790.00~50000~25000~25000'
    "~1800.00~100~1799.00~200~1798.00~300~1797.00~400~1796.00~500"
    "~1801.00~100~1802.00~200~1803.00~300~1804.00~400~1805.00~500"
    "~~20260718150003~15.00~0.84~1810.00~1780.00~1800.00/50000/900000000"
    '~50000~90000.00~1.50~60.00~~1810.00~1780.00~1.68~3600.00~4500.00~2.50~1963.50~1606.50~0.84~-1~~90000.00~0";\n'
    'v_sz000858="1~五粮液~000858~150.00~148.00~149.00~30000~15000~15000'
    "~150.00~100~149.50~200~149.00~300~148.50~400~148.00~500"
    "~150.50~100~151.00~200~151.50~300~152.00~400~152.50~500"
    "~~20260718150003~2.00~1.35~152.00~147.00~150.00/30000/450000000"
    '~30000~45000.00~0.80~25.00~~152.00~147.00~3.38~1200.00~1500.00~1.35~163.80~133.20~0.50~-1~~45000.00~0";\n'
)


class TestMarketPrefix:
    def test_shanghai_prefix(self):
        assert _market_prefix("600519") == "sh"
        assert _market_prefix("601318") == "sh"
        assert _market_prefix("688001") == "sh"

    def test_shenzhen_prefix(self):
        assert _market_prefix("000858") == "sz"
        assert _market_prefix("300750") == "sz"
        assert _market_prefix("002594") == "sz"


class TestParseTencentResponse:
    def test_parse_valid_response(self):
        quotes = _parse_tencent_response(SAMPLE_RESPONSE)
        assert len(quotes) == 2

        q1 = quotes[0]
        assert q1.code == "600519"
        assert q1.name == "贵州茅台"
        assert q1.price == 1800.00
        assert q1.prev_close == 1785.00
        assert q1.open == 1790.00
        assert q1.volume == 50000.0
        assert q1.high == 1810.00
        assert q1.low == 1780.00
        assert q1.change_pct == 0.84
        assert q1.amount == 90000.00

    def test_parse_second_stock(self):
        quotes = _parse_tencent_response(SAMPLE_RESPONSE)
        q2 = quotes[1]
        assert q2.code == "000858"
        assert q2.name == "五粮液"
        assert q2.price == 150.00

    def test_parse_empty_response(self):
        quotes = _parse_tencent_response("")
        assert quotes == []

    def test_parse_blank_quote(self):
        text = 'v_sh000001="";\n'
        quotes = _parse_tencent_response(text)
        assert quotes == []

    def test_parse_short_fields_skipped(self):
        text = 'v_sh600519="1~贵州茅台~600519";\n'
        quotes = _parse_tencent_response(text)
        assert quotes == []


class TestTencentProvider:
    @pytest.mark.asyncio
    async def test_get_realtime_quotes_success(self):
        provider = TencentProvider()
        mock_response = AsyncMock()
        mock_response.content = SAMPLE_RESPONSE.encode("gbk")
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        provider._client = mock_client

        quotes = await provider.get_realtime_quotes(["600519", "000858"])
        assert len(quotes) == 2
        assert quotes[0].code == "600519"
        assert quotes[1].code == "000858"

        # Verify the URL contains correct market prefixes
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "sh600519" in url
        assert "sz000858" in url

    @pytest.mark.asyncio
    async def test_get_realtime_quotes_empty_codes(self):
        provider = TencentProvider()
        quotes = await provider.get_realtime_quotes([])
        assert quotes == []

    @pytest.mark.asyncio
    async def test_get_realtime_quotes_http_error(self):
        provider = TencentProvider()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.is_closed = False
        provider._client = mock_client

        quotes = await provider.get_realtime_quotes(["600519"])
        assert quotes == []
