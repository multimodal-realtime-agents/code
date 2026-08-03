"""Official A2A stock specialist agent."""

from __future__ import annotations

import logging
import json
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
APP_NAME = "agent_system_stock_info_specialist"


def create_stock_mcp_toolset() -> McpToolset:
    """Create an ADK MCP toolset that dynamically discovers the stock-price tool."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=settings.mcp_url,
            timeout=6.0,
            sse_read_timeout=30.0,
        ),
        tool_filter=["get_stock_price"],
    )


def create_stock_info_agent(
    model: str | None = None,
    mcp_toolset: McpToolset | None = None,
) -> Agent:
    toolset = mcp_toolset or create_stock_mcp_toolset()
    return Agent(
        name="stock_info_agent",
        model=model or settings.stock_agent_model,
        description="Specialist agent that converts natural-language stock requests into MCP quote calls.",
        instruction=(
            "You are the Stock Info Agent. The host will send natural-language stock "
            "requests such as 'What is Google's stock price today?' or 'Please get Microsoft's "
            "current stock price.' Identify the intended publicly traded company or ticker, map "
            "common company names to ticker symbols such as Google/Alphabet -> GOOG, Microsoft -> "
            "MSFT, Apple -> AAPL, Nvidia -> NVDA, Amazon -> AMZN, Meta/Facebook -> META, and Tesla "
            "-> TSLA. Use the MCP-discovered get_stock_price tool with only the ticker symbol. "
            "Use the MCP tool result to answer in one concise sentence with symbol, price, currency, "
            "and any short context or warning from the tool. Do not provide investment advice."
        ),
        tools=[toolset],
    )


async def run_stock_info_agent(request: str, context_id: str | None = None) -> dict[str, Any]:
    """Run the specialist ADK agent and return structured quote data."""
    session_service = InMemorySessionService()
    user_id = "a2a-host"
    session_id = context_id or str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={},
    )
    toolset = create_stock_mcp_toolset()
    runner = Runner(
        app_name=APP_NAME,
        agent=create_stock_info_agent(mcp_toolset=toolset),
        session_service=session_service,
    )
    message = types.Content(role="user", parts=[types.Part(text=request)])
    fallback_texts: list[str] = []
    latest_quote: dict[str, Any] | None = None
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
            quote = _event_stock_quote(event)
            if quote is not None:
                latest_quote = quote
            if hasattr(event, "is_final_response") and event.is_final_response():
                saw_final_response = True
    finally:
        await toolset.close()

    if latest_quote is not None:
        return _structured_stock_result(request, latest_quote)

    text = " ".join(fallback_texts).strip()
    return {
        "kind": "stock_quote",
        "title": "Stock quote unavailable",
        "source": "stock-specialist",
        "as_of": None,
        "status": "unavailable",
        "warning": (
            "The stock specialist finished without structured quote data."
            if saw_final_response and not text
            else "The stock specialist returned only text, not structured quote data."
        ),
        "fields": {"request": request},
        "market_context": text or "No stock quote was returned.",
    }


def _event_text(event: object) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    texts = [part.text for part in parts if getattr(part, "text", None)]
    return "".join(texts).strip()


def _event_stock_quote(event: object) -> dict[str, Any] | None:
    data = _event_to_dict(event)
    content = data.get("content") or {}
    for part in content.get("parts") or []:
        function_response = part.get("functionResponse") or part.get("function_response")
        if not function_response:
            continue
        response = function_response.get("response") or {}
        quote = _quote_from_tool_response(response)
        if quote is not None:
            return quote
    return None


def _quote_from_tool_response(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None

    candidates = [
        response.get("structuredContent"),
        response.get("structured_content"),
        response.get("result"),
        response,
    ]
    for candidate in candidates:
        if _is_quote(candidate):
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
            if _is_quote(parsed):
                return parsed
    return None


def _is_quote(value: Any) -> bool:
    return isinstance(value, dict) and "symbol" in value and "source" in value


def _event_to_dict(event: object) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump(exclude_none=True, by_alias=True)
    if hasattr(event, "dict"):
        return event.dict(exclude_none=True, by_alias=True)
    return {}


def _structured_stock_result(request: str, quote: dict[str, Any]) -> dict[str, Any]:
    symbol = str(quote.get("symbol") or "Unknown")
    warning = quote.get("warning")
    price = quote.get("price")
    status = "unavailable" if price is None else "fallback" if warning else "live"
    provenance = {
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
    }
    return {
        "kind": "stock_quote_result",
        "request": request,
        "provenance": provenance,
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


class StockQuoteExecutor(AgentExecutor):
    """A2A executor that performs one bounded MCP quote lookup."""

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
                new_text_message("Please provide a stock symbol.", context_id=context.context_id)
            )
            return

        logger.info("A2A stock specialist handling request: %s", query)
        try:
            answer = await run_stock_info_agent(query, context.context_id)
            await event_queue.enqueue_event(
                new_message(
                    [new_data_part(answer, media_type="application/json")],
                    context_id=context.context_id,
                )
            )
        except Exception as exc:  # noqa: BLE001 - convert tool failures into A2A text.
            logger.exception("Stock lookup failed")
            await event_queue.enqueue_event(
                new_text_message(
                    f"Stock lookup failed: {exc}",
                    context_id=context.context_id,
                )
            )


def build_agent_card() -> AgentCard:
    jsonrpc_url = f"{settings.a2a_url.rstrip('/')}/a2a/jsonrpc"
    return AgentCard(
        name="Stock Specialist",
        description=(
            "Turns natural-language stock price requests into MCP-backed quote lookups."
        ),
        provider=AgentProvider(organization="Reference Agent System", url="https://example.com"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json", "text/plain"],
        skills=[
            AgentSkill(
                id="stock_quote",
                name="Stock quote",
                description=(
                    "Accepts natural-language company or ticker requests and returns the latest "
                    "available quote with one-sentence market context."
                ),
                tags=["stocks", "finance", "quotes"],
                examples=[
                    "NVDA",
                    "What is the latest price for NVDA?",
                    "What is Google's stock price today?",
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
        agent_executor=StockQuoteExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI(title="Stock A2A Agent")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "stock-a2a",
            "a2a_url": settings.a2a_url,
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
    uvicorn.run(app, host=settings.a2a_host, port=settings.a2a_port)
