"""MCP stock-data server used by Chapter 11."""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent


logger = logging.getLogger(__name__)
mcp = FastMCP("Stock Data Server")

_SYMBOL_RE = re.compile(r"[^A-Z0-9.-]")


@dataclass(frozen=True)
class StockRecord:
    symbol: str
    name: str
    price: float
    currency: str
    sector: str
    market_cap: str
    context: str


STOCK_DATA: dict[str, StockRecord] = {
    "AAPL": StockRecord(
        symbol="AAPL",
        name="Apple Inc.",
        price=175.50,
        currency="USD",
        sector="Technology",
        market_cap="Large cap",
        context="Sample context: Apple is usually read through iPhone demand, services growth, and margin durability.",
    ),
    "GOOGL": StockRecord(
        symbol="GOOGL",
        name="Alphabet Inc.",
        price=140.20,
        currency="USD",
        sector="Communication Services",
        market_cap="Large cap",
        context="Sample context: Alphabet is often evaluated through advertising demand, cloud growth, and AI infrastructure spend.",
    ),
    "MSFT": StockRecord(
        symbol="MSFT",
        name="Microsoft Corp.",
        price=380.00,
        currency="USD",
        sector="Technology",
        market_cap="Large cap",
        context="Sample context: Microsoft is closely watched for cloud growth and enterprise AI monetization.",
    ),
    "NVDA": StockRecord(
        symbol="NVDA",
        name="NVIDIA Corp.",
        price=214.86,
        currency="USD",
        sector="Technology",
        market_cap="Large cap",
        context="Sample context: NVIDIA is treated as an AI infrastructure bellwether by many market observers.",
    ),
}

# A deterministic 1x1 red PNG. The image content is intentionally tiny so the
# example stays focused on MCP content transport rather than chart rendering.
MOCK_CHART_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


def normalize_ticker(ticker: str) -> str:
    """Return an uppercase stock ticker suitable for a bounded sample lookup."""
    clean = _SYMBOL_RE.sub("", ticker.upper().strip())
    if "." in clean:
        clean = clean.split(".", maxsplit=1)[0]
    if not clean:
        raise ValueError("A stock ticker is required.")
    return clean[:12]


def _record_to_quote(record: StockRecord) -> dict[str, Any]:
    return {
        "symbol": record.symbol,
        "name": record.name,
        "price": record.price,
        "currency": record.currency,
        "source": "deterministic-sample",
        "market_context": record.context,
    }


def _unknown_quote(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "name": None,
        "price": None,
        "currency": "USD",
        "source": "deterministic-sample-unavailable",
        "warning": (
            f"No deterministic sample quote is bundled for {symbol}; returning an "
            "explicit unavailable result rather than inventing a price."
        ),
    }


@mcp.tool()
def get_stock_price(ticker: str) -> dict[str, Any]:
    """Get the current sample price for a stock ticker."""
    symbol = normalize_ticker(ticker)
    record = STOCK_DATA.get(symbol)
    if record is None:
        logger.info("No deterministic sample quote for %s", symbol)
        return _unknown_quote(symbol)
    return _record_to_quote(record)


@mcp.resource("stock://{ticker}/info")
def get_company_info(ticker: str) -> str:
    """Get static sample metadata about a company."""
    symbol = normalize_ticker(ticker)
    record = STOCK_DATA.get(symbol)
    if record is None:
        return f"No company metadata is bundled for {symbol}."
    return (
        f"{record.name} ({record.symbol}) is a {record.market_cap} company in the "
        f"{record.sector} sector. {record.context}"
    )


@mcp.tool()
def get_stock_chart(ticker: str) -> ImageContent:
    """Return a deterministic sample PNG chart for a stock ticker."""
    symbol = normalize_ticker(ticker)
    if symbol not in STOCK_DATA:
        logger.info("Returning generic chart placeholder for unknown ticker %s", symbol)

    # Validate the bundled payload at call time so a corrupted literal fails loudly.
    base64.b64decode(MOCK_CHART_BASE64, validate=True)
    return ImageContent(type="image", data=MOCK_CHART_BASE64, mimeType="image/png")


def main() -> None:
    """Run the MCP server over stdio."""
    logging.basicConfig(level=logging.WARNING)
    mcp.run()


if __name__ == "__main__":
    main()
