"""LangGraph-based A2A query generator for the research workflow."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TypedDict

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
from langgraph.graph import END, START, StateGraph

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from chapter9_support.config import settings
from chapter9_support.gemini_text import generate_text

try:
    from .query_parser import parse_queries
except ImportError:
    from query_parser import parse_queries


logger = logging.getLogger(__name__)


class QueryState(TypedDict, total=False):
    topic: str
    queries: list[str]


def generate_queries_for_topic(topic: str) -> list[str]:
    prompt = (
        "Generate exactly three concise web search queries for this research topic. "
        "Return one query per line with no commentary.\n\n"
        f"Topic: {topic}"
    )
    queries = parse_queries(generate_text(prompt, temperature=0.2))
    if len(queries) != 3:
        raise RuntimeError(f"Expected exactly three search queries, got {len(queries)}: {queries}")
    return queries


async def generate_queries_node(state: QueryState) -> QueryState:
    return {"queries": generate_queries_for_topic(state["topic"])}


workflow = StateGraph(QueryState)
workflow.add_node("generate_queries", generate_queries_node)
workflow.add_edge(START, "generate_queries")
workflow.add_edge("generate_queries", END)
query_graph = workflow.compile()


def build_agent_card(service_url: str | None = None) -> AgentCard:
    base_url = (service_url or settings.query_generator_url).rstrip("/")
    return AgentCard(
        name="LangGraph Query Generator",
        description="Breaks a research topic into three focused search queries.",
        provider=AgentProvider(organization="O'Reilly Chapter 9", url="https://example.com"),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="generate_queries",
                name="Generate search queries",
                description="Returns three focused search queries for a topic.",
                tags=["research", "planning", "langgraph"],
                examples=["Generate search queries for the A2A protocol"],
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


class QueryGeneratorExecutor(AgentExecutor):
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            new_text_message(
                "The query generator handles short requests only.",
                context_id=context.context_id,
            )
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        topic = context.get_user_input()
        if not topic:
            await event_queue.enqueue_event(
                new_text_message("Please provide a research topic.", context_id=context.context_id)
            )
            return

        logger.info("Generating research queries for: %s", topic)
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        try:
            state = await query_graph.ainvoke({"topic": topic})
            answer = "\n".join(state["queries"])
        except Exception as exc:  # noqa: BLE001 - surface model failures as A2A task status.
            logger.exception("Query generation failed")
            message = updater.new_agent_message([Part(text=f"Query generation failed: {exc}")])
            await updater.failed(message)
            return
        await updater.add_artifact([Part(text=answer)], name="search_queries")
        await updater.complete()


def create_app(agent_card: AgentCard | None = None) -> FastAPI:
    card = agent_card or build_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=QueryGeneratorExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    query_app = FastAPI(title="Chapter 9 Query Generator")
    query_app.routes.extend(create_agent_card_routes(agent_card=card))
    query_app.routes.extend(
        create_jsonrpc_routes(
            request_handler=request_handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )
    return query_app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Starting LangGraph Query Generator on {settings.query_generator_url}...")
    uvicorn.run(app, host=settings.query_generator_host, port=settings.query_generator_port)
