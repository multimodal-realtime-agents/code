"""Shared MCP tool server for the Chapter 12 specialist tools."""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings


logger = logging.getLogger(__name__)

mcp = FastMCP(
    "MCP Tool Server",
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path="/mcp",
    json_response=True,
)

_SYMBOL_RE = re.compile(r"[^A-Z0-9.-]")
_LOCATION_RE = re.compile(r"[^A-Za-z0-9 .,'-]")
_FALLBACK_QUOTES = {
    "NVDA": {
        "symbol": "NVDA",
        "price": 890.0,
        "currency": "USD",
        "as_of": "sample",
        "source": "offline-sample",
        "market_context": (
            "Sample context: NVDA is treated as an AI infrastructure bellwether, "
            "so investors often read its moves as a signal for accelerated computing demand."
        ),
    },
    "AAPL": {
        "symbol": "AAPL",
        "price": 190.0,
        "currency": "USD",
        "as_of": "sample",
        "source": "offline-sample",
        "market_context": (
            "Sample context: AAPL is usually interpreted through the lens of "
            "iPhone demand, services growth, and margin durability."
        ),
    },
    "MSFT": {
        "symbol": "MSFT",
        "price": 430.0,
        "currency": "USD",
        "as_of": "sample",
        "source": "offline-sample",
        "market_context": (
            "Sample context: MSFT is closely watched for cloud growth and "
            "enterprise AI monetization."
        ),
    },
}
_MOCK_WEATHER = {
    "LONDON": {
        "location": "London",
        "condition": "light rain",
        "temperature_c": 12,
        "temperature_f": 54,
        "humidity_percent": 78,
        "wind_kph": 16,
        "as_of": "sample",
        "source": "mock-weather",
        "weather_context": (
            "Mock context: light rain and a cool breeze make this a jacket-and-umbrella day."
        ),
    },
    "NEW YORK": {
        "location": "New York",
        "condition": "partly cloudy",
        "temperature_c": 18,
        "temperature_f": 64,
        "humidity_percent": 61,
        "wind_kph": 12,
        "as_of": "sample",
        "source": "mock-weather",
        "weather_context": "Mock context: mild conditions with some cloud cover.",
    },
    "SAN FRANCISCO": {
        "location": "San Francisco",
        "condition": "foggy",
        "temperature_c": 14,
        "temperature_f": 57,
        "humidity_percent": 84,
        "wind_kph": 18,
        "as_of": "sample",
        "source": "mock-weather",
        "weather_context": "Mock context: cool fog is keeping visibility and temperatures low.",
    },
    "TOKYO": {
        "location": "Tokyo",
        "condition": "clear",
        "temperature_c": 21,
        "temperature_f": 70,
        "humidity_percent": 55,
        "wind_kph": 9,
        "as_of": "sample",
        "source": "mock-weather",
        "weather_context": "Mock context: clear and comfortable conditions.",
    },
}


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "mcp-tool-server",
            "mcp_url": settings.mcp_url,
        }
    )


def normalize_symbol(symbol: str) -> str:
    """Return an uppercase stock ticker suitable for a bounded lookup."""
    clean = _SYMBOL_RE.sub("", symbol.upper().strip())
    if "." in clean:
        clean = clean.split(".", maxsplit=1)[0]
    if not clean:
        raise ValueError("A stock symbol is required.")
    return clean[:12]


def normalize_location(location: str) -> str:
    """Return a compact location string suitable for a bounded mock lookup."""
    clean = _LOCATION_RE.sub("", location).strip()
    clean = " ".join(clean.split())
    if not clean:
        raise ValueError("A weather location is required.")
    return clean[:80]


def _fallback_quote(symbol: str, reason: str) -> dict[str, Any]:
    quote = _FALLBACK_QUOTES.get(symbol)
    if quote is not None:
        quote = dict(quote)
    else:
        quote = {
            "symbol": symbol,
            "price": None,
            "currency": "USD",
            "as_of": "unavailable",
            "source": "offline-unavailable",
            "market_context": (
                f"No deterministic sample quote is bundled for {symbol}; live quote "
                "retrieval failed, so the system is returning an explicit unavailable "
                "result rather than copying another symbol's sample price."
            ),
        }
    quote["symbol"] = symbol
    quote["warning"] = f"Using deterministic fallback data: {reason}"
    return quote


def _mock_weather_for(location: str) -> dict[str, Any]:
    key = location.upper()
    weather = _MOCK_WEATHER.get(key)
    if weather is not None:
        return dict(weather)
    return {
        "location": location.title(),
        "condition": "partly cloudy",
        "temperature_c": 17,
        "temperature_f": 63,
        "humidity_percent": 65,
        "wind_kph": 10,
        "as_of": "sample",
        "source": "mock-weather",
        "weather_context": (
            f"Mock context: no city-specific sample is bundled for {location.title()}, "
            "so this is generic deterministic weather data."
        ),
        "warning": "Using generic mock weather data for an unlisted location.",
    }


def _context_for(symbol: str, price: float, open_price: float | None, high: float | None, low: float | None) -> str:
    if open_price and open_price > 0:
        direction = "above" if price >= open_price else "below"
        pct = ((price - open_price) / open_price) * 100
        return (
            f"{symbol} is trading {direction} its open by {abs(pct):.2f}%, "
            "which frames the move as a short-term session read rather than a full investment view."
        )
    if high and low:
        return (
            f"{symbol}'s latest price sits within a {low:.2f}-{high:.2f} session range, "
            "so the context is a quick market snapshot rather than a forecast."
        )
    return (
        f"{symbol}'s latest available price is a point-in-time quote; compare it with "
        "broader index and sector moves before drawing conclusions."
    )


async def fetch_stooq_quote(symbol: str) -> dict[str, Any]:
    stooq_symbol = f"{symbol.lower()}.us"
    url = "https://stooq.com/q/l/"
    params = {"s": stooq_symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}
    async with httpx.AsyncClient(timeout=6.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

    rows = list(csv.DictReader(io.StringIO(response.text)))
    if not rows:
        raise ValueError("quote response was empty")

    row = rows[0]
    close_value = row.get("Close", "N/D")
    if close_value in {"N/D", "", None}:
        raise ValueError(f"no quote available for {symbol}")

    price = float(close_value)
    open_price = _optional_float(row.get("Open"))
    high = _optional_float(row.get("High"))
    low = _optional_float(row.get("Low"))
    date = row.get("Date") or datetime.now(timezone.utc).date().isoformat()
    time = row.get("Time") or "market close"

    return {
        "symbol": symbol,
        "price": price,
        "currency": "USD",
        "as_of": f"{date} {time}",
        "source": "stooq",
        "open": open_price,
        "high": high,
        "low": low,
        "volume": _optional_int(row.get("Volume")),
        "market_context": _context_for(symbol, price, open_price, high, low),
    }


def _optional_float(value: str | None) -> float | None:
    if value in {None, "", "N/D"}:
        return None
    return float(value)


def _optional_int(value: str | None) -> int | None:
    if value in {None, "", "N/D"}:
        return None
    return int(float(value))


@mcp.tool()
async def get_stock_price(symbol: str) -> dict[str, Any]:
    """Return the latest available stock quote and one-sentence market context."""
    ticker = normalize_symbol(symbol)
    try:
        return await fetch_stooq_quote(ticker)
    except Exception as exc:  # noqa: BLE001 - fallback is intentional for the book demo.
        logger.warning("Falling back to sample quote for %s: %s", ticker, exc)
        return _fallback_quote(ticker, str(exc))


@mcp.tool()
async def get_weather(location: str) -> dict[str, Any]:
    """Return deterministic mock weather for a city or region."""
    return _mock_weather_for(normalize_location(location))


def main() -> None:
    """Run the MCP streamable HTTP server."""
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
