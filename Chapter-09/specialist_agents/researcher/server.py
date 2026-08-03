"""ADK-based A2A researcher for the Chapter 9 workflow."""

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
from google.adk.agents import Agent
from google.adk.tools import google_search

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from chapter9_support.adk_runtime import run_agent_text
from chapter9_support.config import settings


logger = logging.getLogger(__name__)


def create_researcher_agent() -> Agent:
    return Agent(
        name="chapter_9_researcher",
        model=settings.model,
        description="Searches for concise search-assisted research notes.",
        instruction=(
            "You are a research worker. Use Google Search when useful. "
            "For the user's query, return concise research notes with the most "
            "relevant facts and source context. Do not synthesize the whole final report."
        ),
        tools=[google_search],
    )


def build_agent_card(service_url: str | None = None) -> AgentCard:
    base_url = (service_url or settings.researcher_url).rstrip("/")
    return AgentCard(
        name="ADK Researcher",
        description="Runs focused research queries and returns concise notes.",
        provider=AgentProvider(organization="O'Reilly Chapter 9", url="https://example.com"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="research_query",
                name="Research query",
                description="Researches one focused query using an ADK search-capable agent.",
                tags=["research", "search", "adk"],
                examples=["A2A protocol agent card"],
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


class ResearcherExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            new_text_message("The researcher handles bounded requests only.", context_id=context.context_id)
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        if not query:
            await event_queue.enqueue_event(
                new_text_message("Please provide a research query.", context_id=context.context_id)
            )
            return

        logger.info("Researcher handling query: %s", query)
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        try:
            answer = await run_agent_text(
                create_researcher_agent(),
                query,
                app_name="chapter_9_researcher",
            )
        except Exception as exc:  # noqa: BLE001 - surface ADK failures as A2A task status.
            logger.exception("Researcher failed")
            message = updater.new_agent_message([Part(text=f"Research failed: {exc}")])
            await updater.failed(message)
            return
        await updater.add_artifact([Part(text=answer)], name="research_notes")
        await updater.complete()


def create_app(agent_card: AgentCard | None = None) -> FastAPI:
    card = agent_card or build_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=ResearcherExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    researcher_app = FastAPI(title="Chapter 9 ADK Researcher")
    researcher_app.routes.extend(create_agent_card_routes(agent_card=card))
    researcher_app.routes.extend(
        create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )
    return researcher_app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Starting ADK Researcher on {settings.researcher_url}...")
    uvicorn.run(app, host=settings.researcher_host, port=settings.researcher_port)
