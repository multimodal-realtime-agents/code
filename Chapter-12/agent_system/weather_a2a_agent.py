"""Official A2A weather specialist agent backed by a mock MCP weather tool."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import uvicorn
from a2a.helpers import new_data_part, new_message, new_text_message
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
)
from fastapi import FastAPI
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types

from .config import settings


logger = logging.getLogger(__name__)
APP_NAME = "agent_system_weather_specialist"


def create_weather_mcp_toolset() -> McpToolset:
    """Create an ADK MCP toolset that dynamically discovers the mock weather tool."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=settings.mcp_url,
            timeout=6.0,
            sse_read_timeout=30.0,
        ),
        tool_filter=["get_weather"],
    )


def create_weather_info_agent(
    model: str | None = None,
    mcp_toolset: McpToolset | None = None,
) -> Agent:
    toolset = mcp_toolset or create_weather_mcp_toolset()
    return Agent(
        name="weather_info_agent",
        model=model or settings.weather_agent_model,
        description="Specialist agent that converts natural-language weather requests into mock MCP weather calls.",
        instruction=(
            "You are the Weather Info Agent. The host will send natural-language weather "
            "requests such as 'What is the weather in London?' or 'Will it rain in San Francisco?' "
            "Identify the intended city or region. Use the MCP-discovered get_weather tool with "
            "only that location. The tool returns deterministic mock weather data for this demo. "
            "Use the MCP tool result to answer in one concise sentence with location, condition, "
            "temperature, and any short context or warning from the tool. Do not claim this is a "
            "live weather API result."
        ),
        tools=[toolset],
    )


async def run_weather_info_agent(request: str, context_id: str | None = None) -> dict[str, Any]:
    """Run the weather ADK specialist and return structured mock weather data."""
    session_service = InMemorySessionService()
    user_id = "a2a-host"
    session_id = context_id or str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={},
    )
    toolset = create_weather_mcp_toolset()
    runner = Runner(
        app_name=APP_NAME,
        agent=create_weather_info_agent(mcp_toolset=toolset),
        session_service=session_service,
    )
    message = types.Content(role="user", parts=[types.Part(text=request)])
    fallback_texts: list[str] = []
    latest_weather: dict[str, Any] | None = None
    saw_final_response = False

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            text = _event_text(event)
            if text:
                fallback_texts.append(text)
            weather = _event_weather(event)
            if weather is not None:
                latest_weather = weather
            if hasattr(event, "is_final_response") and event.is_final_response():
                saw_final_response = True
    finally:
        await toolset.close()

    if latest_weather is not None:
        return _structured_weather_result(request, latest_weather)

    text = " ".join(fallback_texts).strip()
    return {
        "kind": "weather_report",
        "title": "Weather unavailable",
        "source": "weather-specialist",
        "as_of": None,
        "status": "unavailable",
        "warning": (
            "The weather specialist finished without structured weather data."
            if saw_final_response and not text
            else "The weather specialist returned only text, not structured weather data."
        ),
        "fields": {"request": request},
        "weather_context": text or "No weather report was returned.",
    }


def _event_text(event: object) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    texts = [part.text for part in parts if getattr(part, "text", None)]
    return "".join(texts).strip()


def _event_weather(event: object) -> dict[str, Any] | None:
    data = _event_to_dict(event)
    content = data.get("content") or {}
    for part in content.get("parts") or []:
        function_response = part.get("functionResponse") or part.get("function_response")
        if not function_response:
            continue
        response = function_response.get("response") or {}
        weather = _weather_from_tool_response(response)
        if weather is not None:
            return weather
    return None


def _weather_from_tool_response(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None

    candidates = [
        response.get("structuredContent"),
        response.get("structured_content"),
        response.get("result"),
        response,
    ]
    for candidate in candidates:
        if _is_weather(candidate):
            return candidate

    content = response.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if _is_weather(parsed):
                return parsed
    return None


def _is_weather(value: Any) -> bool:
    return isinstance(value, dict) and "location" in value and "condition" in value and "source" in value


def _event_to_dict(event: object) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump(exclude_none=True, by_alias=True)
    if hasattr(event, "dict"):
        return event.dict(exclude_none=True, by_alias=True)
    return {}


def _structured_weather_result(request: str, weather: dict[str, Any]) -> dict[str, Any]:
    location = str(weather.get("location") or "Unknown")
    warning = weather.get("warning")
    status = "fallback" if warning else "mock"
    provenance = {
        "title": f"{location} weather",
        "kind": "weather_report",
        "source": weather.get("source") or "unknown",
        "as_of": weather.get("as_of"),
        "status": status,
        "warning": warning,
        "fields": {
            "location": location,
            "condition": weather.get("condition"),
            "temperature_c": weather.get("temperature_c"),
            "temperature_f": weather.get("temperature_f"),
        },
    }
    return {
        "kind": "weather_report_result",
        "request": request,
        "provenance": provenance,
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


class WeatherExecutor(AgentExecutor):
    """A2A executor that performs one bounded mock weather lookup."""

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            new_text_message(
                "This specialist handles fast requests only.",
                context_id=context.context_id,
            )
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        if not query:
            await event_queue.enqueue_event(
                new_text_message("Please provide a weather location.", context_id=context.context_id)
            )
            return

        logger.info("A2A weather specialist handling request: %s", query)
        try:
            answer = await run_weather_info_agent(query, context.context_id)
            await event_queue.enqueue_event(
                new_message(
                    [new_data_part(answer, media_type="application/json")],
                    context_id=context.context_id,
                )
            )
        except Exception as exc:  # noqa: BLE001 - convert tool failures into A2A text.
            logger.exception("Weather lookup failed")
            await event_queue.enqueue_event(
                new_text_message(
                    f"Weather lookup failed: {exc}",
                    context_id=context.context_id,
                )
            )


def build_agent_card() -> AgentCard:
    jsonrpc_url = f"{settings.weather_a2a_url.rstrip('/')}/a2a/jsonrpc"
    return AgentCard(
        name="Weather Specialist",
        description="Turns natural-language weather requests into MCP-backed mock weather lookups.",
        provider=AgentProvider(organization="Reference Agent System", url="https://example.com"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json", "text/plain"],
        skills=[
            AgentSkill(
                id="weather_report",
                name="Weather report",
                description=(
                    "Accepts natural-language city or region requests and returns deterministic "
                    "mock weather with concise context."
                ),
                tags=["weather", "forecast", "mock-data"],
                examples=[
                    "What is the weather in London?",
                    "Will it rain in San Francisco?",
                    "Give me the weather for Tokyo.",
                ],
                input_modes=["text/plain"],
                output_modes=["application/json", "text/plain"],
            )
        ],
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=jsonrpc_url,
            )
        ],
    )


def create_app() -> FastAPI:
    agent_card = build_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=WeatherExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI(title="Weather A2A Agent")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "weather-a2a",
            "weather_a2a_url": settings.weather_a2a_url,
            "mcp_url": settings.mcp_url,
        }

    app.routes.extend(create_agent_card_routes(agent_card=agent_card))
    app.routes.extend(
        create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )
    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=settings.weather_a2a_host, port=settings.weather_a2a_port)
