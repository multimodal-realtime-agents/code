"""Configuration for the reference agent system."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_ROOT = Path(__file__).resolve().parent.parent


def _load_env_files() -> None:
    load_dotenv(APP_ROOT / ".env")
    load_dotenv(APP_ROOT / ".env.local", override=True)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    live_model: str
    fallback_live_model: str
    stock_agent_model: str
    weather_agent_model: str
    service_name: str
    mcp_host: str
    mcp_port: int
    mcp_url: str
    a2a_host: str
    a2a_port: int
    a2a_url: str
    weather_a2a_host: str
    weather_a2a_port: int
    weather_a2a_url: str
    specialist_agent_urls: tuple[str, ...]
    backend_host: str
    backend_port: int
    frontend_host: str
    frontend_port: int
    live_ws_url: str
    allowed_origins: tuple[str, ...]


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _service_port(
    name: str,
    default: int,
    service_names: str | tuple[str, ...],
    current_service: str,
) -> int:
    if os.getenv(name):
        return _int_env(name, default)
    names = {service_names} if isinstance(service_names, str) else set(service_names)
    if current_service in names:
        return _int_env("PORT", default)
    return default


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


def _default_host() -> str:
    if os.getenv("PORT"):
        return "0.0.0.0"
    return "127.0.0.1"


def load_settings() -> Settings:
    service_name = os.getenv("AGENT_SYSTEM_SERVICE", "").strip().casefold()
    default_host = _default_host()
    mcp_host = os.getenv("AGENT_SYSTEM_MCP_HOST", default_host)
    mcp_port = _service_port(
        "AGENT_SYSTEM_MCP_PORT",
        8010,
        ("mcp", "mcp-tool-server", "mcp_tool_server", "finance-mcp", "finance_mcp_server"),
        service_name,
    )
    a2a_host = os.getenv("AGENT_SYSTEM_A2A_HOST", default_host)
    a2a_port = _service_port(
        "AGENT_SYSTEM_A2A_PORT",
        8020,
        ("a2a", "stock-a2a", "stock_a2a_agent"),
        service_name,
    )
    weather_a2a_host = os.getenv("AGENT_SYSTEM_WEATHER_A2A_HOST", default_host)
    weather_a2a_port = _service_port(
        "AGENT_SYSTEM_WEATHER_A2A_PORT",
        8030,
        ("weather", "weather-a2a", "weather_a2a_agent"),
        service_name,
    )
    backend_host = os.getenv("AGENT_SYSTEM_BACKEND_HOST", default_host)
    backend_port = _service_port("AGENT_SYSTEM_BACKEND_PORT", 8000, "backend", service_name)
    frontend_host = os.getenv("AGENT_SYSTEM_FRONTEND_HOST", default_host)
    frontend_port = _service_port("AGENT_SYSTEM_FRONTEND_PORT", 8080, "frontend", service_name)
    a2a_url = os.getenv("AGENT_SYSTEM_A2A_URL", f"http://{a2a_host}:{a2a_port}")
    weather_a2a_url = os.getenv(
        "AGENT_SYSTEM_WEATHER_A2A_URL",
        f"http://{weather_a2a_host}:{weather_a2a_port}",
    )

    return Settings(
        live_model=os.getenv("AGENT_SYSTEM_LIVE_MODEL", "gemini-3.1-flash-live-preview"),
        fallback_live_model=os.getenv(
            "AGENT_SYSTEM_FALLBACK_LIVE_MODEL",
            "gemini-2.5-flash-native-audio-preview-12-2025",
        ),
        stock_agent_model=os.getenv("AGENT_SYSTEM_STOCK_AGENT_MODEL", "gemini-2.5-flash"),
        weather_agent_model=os.getenv("AGENT_SYSTEM_WEATHER_AGENT_MODEL", "gemini-2.5-flash"),
        service_name=service_name,
        mcp_host=mcp_host,
        mcp_port=mcp_port,
        mcp_url=os.getenv("AGENT_SYSTEM_MCP_URL", f"http://{mcp_host}:{mcp_port}/mcp"),
        a2a_host=a2a_host,
        a2a_port=a2a_port,
        a2a_url=a2a_url,
        weather_a2a_host=weather_a2a_host,
        weather_a2a_port=weather_a2a_port,
        weather_a2a_url=weather_a2a_url,
        specialist_agent_urls=tuple(
            url.strip()
            for url in os.getenv(
                "AGENT_SYSTEM_SPECIALIST_AGENT_URLS",
                f"{a2a_url},{weather_a2a_url}",
            ).split(",")
            if url.strip()
        ),
        backend_host=backend_host,
        backend_port=backend_port,
        frontend_host=frontend_host,
        frontend_port=frontend_port,
        live_ws_url=os.getenv("AGENT_SYSTEM_LIVE_WS_URL", f"ws://{backend_host}:{backend_port}/live"),
        allowed_origins=_csv_env(
            "AGENT_SYSTEM_ALLOWED_ORIGINS",
            "http://127.0.0.1:8080,http://localhost:8080",
        ),
    )


settings = load_settings()
