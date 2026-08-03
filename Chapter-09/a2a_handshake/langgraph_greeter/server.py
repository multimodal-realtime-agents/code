"""A2A server that exposes the LangGraph Greeter."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from a2a.helpers import new_text_message
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import TaskUpdater
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    Part,
)
from fastapi import FastAPI

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from chapter9_support.config import settings

try:
    from .greeter_agent_logic import langgraph_app
except ImportError:
    from greeter_agent_logic import langgraph_app


logger = logging.getLogger(__name__)


def build_agent_card(service_url: str | None = None) -> AgentCard:
    base_url = (service_url or settings.greeter_url).rstrip("/")
    return AgentCard(
        name="LangGraph Greeter",
        description="A friendly LangGraph agent exposed through A2A.",
        provider=AgentProvider(organization="O'Reilly Chapter 9", url="https://example.com"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="greet",
                name="Simple Greeting",
                description="Returns a friendly greeting for the request.",
                tags=["greeting", "langgraph"],
                examples=["Hello", "Hi from ADK"],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            )
        ],
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=f"{base_url}/a2a/jsonrpc",
            )
        ],
    )


class GreeterExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            new_text_message("The Greeter does not support cancellation.", context_id=context.context_id)
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        request = context.get_user_input() or "Hello"
        logger.info("Greeter received request: %s", request)
        final_state = await langgraph_app.ainvoke(
            {},
            {"configurable": {"thread_id": context.context_id}},
        )
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.add_artifact([Part(text=final_state["message"])], name="greeting_response")
        await updater.complete()


def create_app(agent_card: AgentCard | None = None) -> FastAPI:
    card = agent_card or build_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=GreeterExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    greeter_app = FastAPI(title="Chapter 9 LangGraph Greeter")
    greeter_app.routes.extend(create_agent_card_routes(agent_card=card))
    greeter_app.routes.extend(
        create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )
    return greeter_app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Starting LangGraph Greeter on {settings.greeter_url}...")
    uvicorn.run(app, host=settings.greeter_host, port=settings.greeter_port)
