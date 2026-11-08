"""Local MCP for Chittorgarh IPO / NCD / buyback lists."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("chittorgarh")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "__dict__"):
        return {
            key: _jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)


def _dump(rows: Any) -> str:
    return json.dumps(_jsonable(rows), indent=2, default=str)


@mcp.tool()
def list_mainboard_ipos() -> str:
    """Current and recent mainboard IPOs from Chittorgarh."""
    from chittorgarh_client.client import ChittorgarhClient

    return _dump(ChittorgarhClient().get_mainboard_ipos())


@mcp.tool()
def list_sme_ipos() -> str:
    """Current and recent SME IPOs from Chittorgarh (BSE SME / NSE Emerge)."""
    from chittorgarh_client.client import ChittorgarhClient

    return _dump(ChittorgarhClient().get_sme_ipos())


@mcp.tool()
def list_ncds() -> str:
    """Latest NCD issues listed on Chittorgarh."""
    from chittorgarh_client.client import ChittorgarhClient

    return _dump(ChittorgarhClient().get_ncds())


@mcp.tool()
def list_buybacks() -> str:
    """Latest tender-offer buybacks listed on Chittorgarh."""
    from chittorgarh_client.client import ChittorgarhClient

    return _dump(ChittorgarhClient().get_buy_backs())


@mcp.tool()
def live_subscription(ipo_id: str) -> str:
    """Live IPO subscription multiples by category. ipo_id is the Chittorgarh numeric id."""
    from chittorgarh_client.client import ChittorgarhClient

    return _dump(ChittorgarhClient().get_live_subscription(ipo_id))


@mcp.tool()
def list_gmp() -> str:
    """Mainboard IPO grey-market premium (via the same unofficial client used for Chittorgarh)."""
    from chittorgarh_client.client import InvestorGainClient

    return _dump(InvestorGainClient().get_mainboard_ipos())


if __name__ == "__main__":
    mcp.run()
