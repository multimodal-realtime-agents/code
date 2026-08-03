"""ADK financial analyst that discovers tools from the Chapter 11 MCP server."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from config import require_google_credentials, settings


APP_NAME = "chapter_11_financial_analyst"
DEFAULT_QUERY = "What is the current price of Apple?"


def create_stock_toolset(
    server_path: Path | None = None,
    python_executable: str | None = None,
) -> McpToolset:
    """Create an ADK MCP toolset for the local stock server."""
    return McpToolset(
        connection_params=create_stock_connection_params(
            server_path=server_path,
            python_executable=python_executable,
        )
    )


def create_stock_connection_params(
    server_path: Path | None = None,
    python_executable: str | None = None,
) -> StdioConnectionParams:
    """Create stdio connection parameters for the local stock server."""
    resolved_server_path = server_path or Path(__file__).with_name("stock_server.py")
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=python_executable or sys.executable,
            args=[str(resolved_server_path)],
        ),
        timeout=10.0,
    )


def create_analyst_agent(
    model: str | None = None,
    mcp_toolset: McpToolset | None = None,
) -> Agent:
    """Create the financial analyst agent without embedding finance logic."""
    toolset = mcp_toolset or create_stock_toolset()
    return Agent(
        name="financial_analyst",
        model=model or settings.model,
        description="Financial analyst that uses an MCP stock server for sample quote data.",
        instruction=(
            "You are a financial analyst. Use the available MCP-discovered tools to "
            "answer questions about stock prices and sample chart data. Always state "
            "the ticker, price, and currency when a price is available. If the MCP "
            "server returns an unavailable result, say that the sample dataset does "
            "not include that ticker. When a tool returns an image, acknowledge the "
            "image in words but do not include raw base64 data or image markup in "
            "your text response. Do not provide investment advice."
        ),
        tools=[toolset],
    )


def event_text(event: object) -> str:
    """Return concatenated text parts from an ADK event."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    return "".join(part.text for part in parts if getattr(part, "text", None)).strip()


def function_call_names(event: object) -> list[str]:
    """Return tool/function names requested by an ADK event."""
    get_function_calls = getattr(event, "get_function_calls", None)
    if not callable(get_function_calls):
        return []
    return [call.name for call in get_function_calls() if getattr(call, "name", None)]


def function_response_images(event: object) -> list[dict[str, str]]:
    """Extract MCP image payloads from ADK function-response events."""
    images: list[dict[str, str]] = []
    for response in _function_responses(event):
        images.extend(_images_from_value(response.get("response")))
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for image in images:
        key = (image.get("mimeType", ""), image.get("data", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(image)
    return deduped


def _function_responses(event: object) -> list[dict[str, Any]]:
    data = _to_dict(event)
    content = data.get("content") or {}
    responses: list[dict[str, Any]] = []
    for part in content.get("parts") or []:
        response = part.get("functionResponse") or part.get("function_response")
        if isinstance(response, dict):
            responses.append(response)
    return responses


def _images_from_value(value: Any) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    if isinstance(value, dict):
        if value.get("type") == "image" and isinstance(value.get("data"), str):
            images.append(
                {
                    "mimeType": str(value.get("mimeType") or value.get("mime_type") or ""),
                    "data": value["data"],
                }
            )
        for nested in value.values():
            images.extend(_images_from_value(nested))
    elif isinstance(value, list):
        for item in value:
            images.extend(_images_from_value(item))
    return images


def _to_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(by_alias=True, exclude_none=True)
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return json.loads(to_json())
    return {}


async def run_query(query: str) -> list[str]:
    """Run the analyst once and return user-visible log lines."""
    session_service = InMemorySessionService()
    user_id = "chapter-11-user"
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    toolset = create_stock_toolset()
    runner = Runner(
        app_name=APP_NAME,
        agent=create_analyst_agent(mcp_toolset=toolset),
        session_service=session_service,
    )
    message = types.Content(role="user", parts=[types.Part(text=query)])
    lines = ["--- Starting Financial Analyst Agent ---", f"User: {query}"]

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            for name in function_call_names(event):
                lines.append(f"[Agent] Decided to call tool: {name}")
            for image in function_response_images(event):
                lines.append(
                    "[MCP] Received image payload: "
                    f"{image.get('mimeType') or 'unknown MIME type'}, "
                    f"{len(image.get('data', ''))} base64 characters"
                )
            if hasattr(event, "is_final_response") and event.is_final_response():
                text = event_text(event)
                if text:
                    lines.append(f"[Agent] Response: {text}")
    finally:
        await toolset.close()

    return lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="*", help="Question to ask the analyst agent.")
    return parser.parse_args(argv)


async def async_main(argv: list[str]) -> None:
    args = parse_args(argv)
    query = " ".join(args.query).strip() or DEFAULT_QUERY
    require_google_credentials()
    for line in await run_query(query):
        print(line)


def main() -> None:
    asyncio.run(async_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
