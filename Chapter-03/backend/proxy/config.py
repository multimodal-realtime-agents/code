"""Configuration for the Chapter 3 audio-only Live API app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_ROOT = Path(__file__).resolve().parents[2]


def _load_env_files() -> None:
    load_dotenv(APP_ROOT / ".env")
    load_dotenv(APP_ROOT / ".env.local", override=True)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    live_model: str
    fallback_live_model: str
    api_key: str | None
    proxy_host: str
    proxy_port: int
    proxy_max_size: int
    frontend_host: str
    frontend_port: int
    live_ws_url: str
    allowed_origins: tuple[str, ...]


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in (os.getenv(name) or default).split(",") if value.strip())


def _str_env(name: str, default: str) -> str:
    return os.getenv(name) or default


def load_settings() -> Settings:
    proxy_host = _str_env("CHAPTER3_PROXY_HOST", "127.0.0.1")
    proxy_port = _int_env("CHAPTER3_PROXY_PORT", 8081)
    frontend_host = _str_env("CHAPTER3_FRONTEND_HOST", "127.0.0.1")
    frontend_port = _int_env("CHAPTER3_FRONTEND_PORT", 8000)
    return Settings(
        live_model=_str_env("CHAPTER3_LIVE_MODEL", "gemini-3.1-flash-live-preview"),
        fallback_live_model=_str_env(
            "CHAPTER3_FALLBACK_LIVE_MODEL",
            "gemini-2.5-flash-native-audio-preview-12-2025",
        ),
        api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_max_size=_int_env("CHAPTER3_PROXY_MAX_SIZE", 2 * 1024 * 1024),
        frontend_host=frontend_host,
        frontend_port=frontend_port,
        live_ws_url=_str_env("CHAPTER3_LIVE_WS_URL", f"ws://{proxy_host}:{proxy_port}/live"),
        allowed_origins=_csv_env(
            "CHAPTER3_ALLOWED_ORIGINS",
            f"http://{frontend_host}:{frontend_port},http://localhost:{frontend_port}",
        ),
    )


settings = load_settings()
