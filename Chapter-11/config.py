"""Configuration helpers for the Chapter 11 MCP examples."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_ROOT = Path(__file__).resolve().parent


def _load_env_files() -> None:
    load_dotenv(APP_ROOT / ".env")
    load_dotenv(APP_ROOT / ".env.local", override=True)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    model: str


def load_settings() -> Settings:
    return Settings(model=os.getenv("CH11_MODEL", "gemini-3.5-flash"))


def has_google_credentials() -> bool:
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return True
    return (
        os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "1"
        and bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
        and bool(os.getenv("GOOGLE_CLOUD_LOCATION"))
    )


def require_google_credentials() -> None:
    if has_google_credentials():
        return
    raise RuntimeError(
        "analyst_agent.py requires GOOGLE_API_KEY, GEMINI_API_KEY, or "
        "Vertex AI environment variables. The deterministic tests do not."
    )


settings = load_settings()
