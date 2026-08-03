"""Direct Live API tool registry for Chapter 4.

Chapter 4 keeps tools local to the live proxy so readers can learn function
calling before the same capabilities move behind A2A and MCP in Chapter 12.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"[^A-Z0-9.-]")
_LOCATION_RE = re.compile(r"[^A-Za-z0-9 .,'-]")
_PROVENANCE_FIELD_EXCLUDES = {
    "provenance",
    "answer_context",
    "kind",
    "request",
    "source",
    "as_of",
    "status",
    "warning",
}
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
            "Sample context: AAPL is usually interpreted through the lens of iPhone "
            "demand, services growth, and margin durability."
        ),
    },
    "MSFT": {
        "symbol": "MSFT",
        "price": 430.0,
        "currency": "USD",
        "as_of": "sample",
        "source": "offline-sample",
        "market_context": (
            "Sample context: MSFT is closely watched for cloud growth and enterprise AI "
            "monetization."
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


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]]


def normalize_symbol(symbol: str) -> str:
    clean = _SYMBOL_RE.sub("", symbol.upper().strip())
    if "." in clean:
        clean = clean.split(".", maxsplit=1)[0]
    if not clean:
        raise ValueError("A stock symbol is required.")
    return clean[:12]


def normalize_location(location: str) -> str:
    clean = _LOCATION_RE.sub("", location).strip()
    clean = " ".join(clean.split())
    if not clean:
        raise ValueError("A weather location is required.")
    return clean[:80]


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


async def get_stock_price(symbol: str) -> dict[str, Any]:
    ticker = normalize_symbol(symbol)
    try:
        quote = await fetch_stooq_quote(ticker)
    except Exception as exc:  # noqa: BLE001 - deterministic fallback is intentional.
        logger.warning("Falling back to sample quote for %s: %s", ticker, exc)
        quote = _fallback_quote(ticker, str(exc))
    return _structured_stock_result(quote)


async def get_weather(location: str) -> dict[str, Any]:
    weather = _mock_weather_for(normalize_location(location))
    return _structured_weather_result(weather)


TOOLS: dict[str, ToolSpec] = {
    "get_stock_price": ToolSpec(
        name="get_stock_price",
        description=(
            "Get the latest available stock quote and short market context for a ticker symbol. "
            "Use this for current price, quote, or market-context questions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "A public stock ticker symbol, such as NVDA, AAPL, MSFT, GOOG, or TSLA.",
                }
            },
            "required": ["symbol"],
        },
        handler=get_stock_price,
    ),
    "get_weather": ToolSpec(
        name="get_weather",
        description=(
            "Get deterministic demo weather for a city or region. The result is mock data "
            "and must be described as such."
        ),
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city or region to get demo weather for.",
                }
            },
            "required": ["location"],
        },
        handler=get_weather,
    ),
}


def function_declarations() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for tool in TOOLS.values()
    ]


async def execute_tool(name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        return {
            "kind": "tool_error",
            "status": "error",
            "warning": f"Unknown tool: {name}",
        }
    try:
        result = await tool.handler(**(args or {}))
        return ensure_tool_result_contract(name, args or {}, result)
    except TypeError as exc:
        return {
            "kind": "tool_error",
            "status": "error",
            "warning": f"Invalid arguments for {name}: {exc}",
        }
    except Exception as exc:  # noqa: BLE001 - function responses should be structured.
        logger.exception("Tool execution failed: %s", name)
        return {
            "kind": "tool_error",
            "status": "error",
            "warning": f"Tool execution failed for {name}: {exc}",
        }


def ensure_tool_result_contract(name: str, args: dict[str, Any], result: Any) -> dict[str, Any]:
    """Keep swapped-in tools compatible with the Chapter 12-style UI contract."""
    if not isinstance(result, dict):
        result = {"value": result}

    normalized = dict(result)
    normalized.setdefault("kind", "tool_result")
    normalized.setdefault("request", _request_summary(args))

    if not _has_valid_provenance(normalized):
        normalized["provenance"] = _generic_provenance(name, args, normalized)

    normalized.setdefault("answer_context", _answer_context_from(normalized))
    return normalized


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
                f"No deterministic sample quote is bundled for {symbol}; live quote retrieval "
                "failed, so the system is returning an explicit unavailable result."
            ),
        }
    quote["symbol"] = symbol
    quote["warning"] = f"Using deterministic fallback data: {reason}"
    return quote


def _mock_weather_for(location: str) -> dict[str, Any]:
    weather = _MOCK_WEATHER.get(location.upper())
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


def _structured_stock_result(quote: dict[str, Any]) -> dict[str, Any]:
    symbol = str(quote.get("symbol") or "Unknown")
    warning = quote.get("warning")
    price = quote.get("price")
    status = "unavailable" if price is None else "fallback" if warning else "live"
    return {
        "kind": "stock_quote_result",
        "request": symbol,
        "provenance": {
            "title": f"{symbol} quote",
            "kind": "stock_quote",
            "source": quote.get("source") or "unknown",
            "as_of": quote.get("as_of"),
            "status": status,
            "warning": warning,
            "fields": {
                "symbol": symbol,
                "price": price,
                "currency": quote.get("currency"),
            },
        },
        "quote": quote,
        "answer_context": {
            "symbol": symbol,
            "price": price,
            "currency": quote.get("currency"),
            "market_context": quote.get("market_context"),
            "warning": warning,
            "source": quote.get("source"),
            "as_of": quote.get("as_of"),
        },
    }


def _structured_weather_result(weather: dict[str, Any]) -> dict[str, Any]:
    location = str(weather.get("location") or "Unknown")
    warning = weather.get("warning")
    return {
        "kind": "weather_report_result",
        "request": location,
        "provenance": {
            "title": f"{location} weather",
            "kind": "weather_report",
            "source": weather.get("source") or "unknown",
            "as_of": weather.get("as_of"),
            "status": "fallback" if warning else "mock",
            "warning": warning,
            "fields": {
                "location": location,
                "condition": weather.get("condition"),
                "temperature_c": weather.get("temperature_c"),
                "temperature_f": weather.get("temperature_f"),
            },
        },
        "weather": weather,
        "answer_context": {
            "location": location,
            "condition": weather.get("condition"),
            "temperature_c": weather.get("temperature_c"),
            "temperature_f": weather.get("temperature_f"),
            "humidity_percent": weather.get("humidity_percent"),
            "wind_kph": weather.get("wind_kph"),
            "weather_context": weather.get("weather_context"),
            "warning": warning,
            "source": weather.get("source"),
            "as_of": weather.get("as_of"),
        },
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
        f"{symbol}'s latest available price is a point-in-time quote; compare it with broader "
        "index and sector moves before drawing conclusions."
    )


def _optional_float(value: str | None) -> float | None:
    if value in {None, "", "N/D"}:
        return None
    return float(value)


def _optional_int(value: str | None) -> int | None:
    if value in {None, "", "N/D"}:
        return None
    return int(float(value))


def _has_valid_provenance(result: dict[str, Any]) -> bool:
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        return False
    if any(not provenance.get(key) for key in ("title", "kind", "source", "status")):
        return False
    return isinstance(provenance.get("fields"), dict)


def _generic_provenance(name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    fields = _scalar_fields(result)
    if not fields:
        fields = {f"arg_{key}": value for key, value in _scalar_fields(args).items()}
    if not fields:
        fields = {"tool": name}
    return {
        "title": f"{name.replace('_', ' ')} result",
        "kind": result.get("kind") or "tool_result",
        "source": result.get("source") or "chapter4-local-tool",
        "as_of": result.get("as_of"),
        "status": result.get("status") or "ok",
        "warning": result.get("warning"),
        "fields": fields,
    }


def _answer_context_from(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key not in {"provenance", "answer_context"} and _is_scalar(value)
    }


def _request_summary(args: dict[str, Any]) -> str:
    if not args:
        return ""
    return ", ".join(f"{key}={value}" for key, value in args.items())


def _scalar_fields(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if key not in _PROVENANCE_FIELD_EXCLUDES and _is_scalar(value)
    }


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))
