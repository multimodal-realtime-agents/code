"""A2A server that wraps the Chapter 6 Math Agent."""

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
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chapter9_support.adk_runtime import run_agent_text
from chapter9_support.config import settings

try:
    from .math_agent_ch6.agent import root_agent
except ImportError:
    from math_agent_ch6.agent import root_agent


logger = logging.getLogger(__name__)


def build_agent_card(service_url: str | None = None) -> AgentCard:
    base_url = (service_url or settings.math_url).rstrip("/")
    return AgentCard(
        name="ADK Math Agent",
        description="The Chapter 6 Math Agent exposed as an A2A service.",
        provider=AgentProvider(organization="O'Reilly Chapter 9", url="https://example.com"),
        version="2.0-a2a",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="add",
                name="Addition",
                description="Adds numbers.",
                tags=["math", "adk", "addition"],
                examples=["Add 4 and 9"],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="subtract",
                name="Subtraction",
                description="Subtracts numbers.",
                tags=["math", "adk", "subtraction"],
                examples=["Subtract 7 from 20"],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="multiply",
                name="Multiplication",
                description="Multiplies numbers.",
                tags=["math", "adk", "multiplication"],
                examples=["What is 5 times 12?"],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="divide",
                name="Division",
                description="Divides numbers.",
                tags=["math", "adk", "division"],
                examples=["Divide 144 by 12"],
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


class MathAgentExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            new_text_message("The math agent handles short requests only.", context_id=context.context_id)
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        if not query:
            await event_queue.enqueue_event(
                new_text_message("Please provide a math question.", context_id=context.context_id)
            )
            return

        logger.info("Math Agent received request: %s", query)
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        try:
            answer = await run_agent_text(root_agent, query, app_name="chapter_9_math_agent")
        except Exception as exc:  # noqa: BLE001 - surface ADK failures as A2A task status.
            logger.exception("Math Agent failed")
            message = updater.new_agent_message([Part(text=f"Math Agent failed: {exc}")])
            await updater.failed(message)
            return
        await updater.add_artifact([Part(text=answer)], name="math_result")
        await updater.complete()


def create_app(agent_card: AgentCard | None = None) -> FastAPI:
    card = agent_card or build_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=MathAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    math_app = FastAPI(title="Chapter 9 A2A Math Agent")
    math_app.routes.extend(create_agent_card_routes(agent_card=card))
    math_app.routes.extend(
        create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )
    return math_app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Starting A2A Math Agent on {settings.math_url}...")
    uvicorn.run(app, host=settings.math_host, port=settings.math_port)
