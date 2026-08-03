"""Configuration helpers for Chapter 9 examples."""

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
    model: str
    deterministic_smoke: bool
    greeter_host: str
    greeter_port: int
    greeter_url: str
    math_host: str
    math_port: int
    math_url: str
    query_generator_host: str
    query_generator_port: int
    query_generator_url: str
    researcher_host: str
    researcher_port: int
    researcher_url: str


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _url_env(name: str, host: str, port: int) -> str:
    return os.getenv(name, f"http://{host}:{port}").rstrip("/")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    greeter_host = os.getenv("CH9_GREETER_HOST", "127.0.0.1")
    greeter_port = _int_env("CH9_GREETER_PORT", 10000)
    math_host = os.getenv("CH9_MATH_HOST", "127.0.0.1")
    math_port = _int_env("CH9_MATH_PORT", 10001)
    query_generator_host = os.getenv("CH9_QUERY_GENERATOR_HOST", "127.0.0.1")
    query_generator_port = _int_env("CH9_QUERY_GENERATOR_PORT", 10002)
    researcher_host = os.getenv("CH9_RESEARCHER_HOST", "127.0.0.1")
    researcher_port = _int_env("CH9_RESEARCHER_PORT", 10003)

    return Settings(
        model=os.getenv("CH9_MODEL", "gemini-2.5-flash"),
        deterministic_smoke=_bool_env("CH9_DETERMINISTIC_SMOKE"),
        greeter_host=greeter_host,
        greeter_port=greeter_port,
        greeter_url=_url_env("CH9_GREETER_URL", greeter_host, greeter_port),
        math_host=math_host,
        math_port=math_port,
        math_url=_url_env("CH9_MATH_URL", math_host, math_port),
        query_generator_host=query_generator_host,
        query_generator_port=query_generator_port,
        query_generator_url=_url_env(
            "CH9_QUERY_GENERATOR_URL",
            query_generator_host,
            query_generator_port,
        ),
        researcher_host=researcher_host,
        researcher_port=researcher_port,
        researcher_url=_url_env("CH9_RESEARCHER_URL", researcher_host, researcher_port),
    )


def has_google_credentials() -> bool:
    if settings.deterministic_smoke:
        return True
    if os.getenv("GOOGLE_API_KEY"):
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
        "This Chapter 9 example requires GOOGLE_API_KEY or Vertex AI "
        "environment variables."
    )


settings = load_settings()
