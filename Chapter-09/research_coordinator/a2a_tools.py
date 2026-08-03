"""A2A tool functions used by the research coordinator."""

from __future__ import annotations

import re
import uuid
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState

from chapter9_support.config import settings
from chapter9_support.gemini_text import generate_text


async def delegate_research(research_topic: str) -> str:
    """Research a topic by delegating work to remote A2A specialists."""
    search_queries_text = await call_remote_agent(
        settings.query_generator_url,
        research_topic,
    )
    search_queries = parse_queries(search_queries_text)
    if not search_queries:
        raise RuntimeError(f"Query generator returned no usable queries: {search_queries_text!r}")

    research_notes: list[str] = []
    for query in search_queries:
        note = await call_remote_agent(settings.researcher_url, query)
        research_notes.append(f"Query: {query}\n{note}")

    prompt = (
        "Write a concise three-paragraph executive summary based only on these "
        "research notes. Mention uncertainty when the notes are thin.\n\n"
        f"Original topic: {research_topic}\n\n"
        "Research notes:\n"
        + "\n\n---\n\n".join(research_notes)
    )
    summary = generate_text(prompt, temperature=0.2)
    return f"Research complete.\n\n{summary}"


async def call_remote_agent(agent_url: str, prompt: str) -> str:
    """Run one discover/connect/communicate A2A request cycle."""
    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        client = await create_client(
            agent_url,
            client_config=ClientConfig(
                streaming=True,
                polling=False,
                httpx_client=httpx_client,
                supported_protocol_bindings=["JSONRPC"],
            ),
        )
        try:
            request_message = Message(
                role=Role.ROLE_USER,
                message_id=str(uuid.uuid4()),
                context_id=str(uuid.uuid4()),
                parts=[Part(text=prompt)],
            )
            request = SendMessageRequest(message=request_message)
            return await collect_text_response(client.send_message(request), agent_url)
        finally:
            await client.close()


async def collect_text_response(stream: Any, agent_url: str) -> str:
    texts: list[str] = []
    delimiter = " "

    async for event in stream:
        if event.HasField("message"):
            text = get_message_text(
                event.message,
                delimiter=delimiter,
            ).strip()
            if text:
                texts.append(text)
            continue

        if event.HasField("task") and event.task.artifacts:
            for artifact in event.task.artifacts:
                text = get_artifact_text(
                    artifact,
                    delimiter=delimiter,
                ).strip()
                if text:
                    texts.append(text)
            continue

        if event.HasField("artifact_update"):
            text = get_artifact_text(event.artifact_update.artifact, delimiter=delimiter).strip()
            if text:
                texts.append(text)
            continue

        if event.HasField("status_update"):
            state = event.status_update.status.state
            if state in {
                TaskState.TASK_STATE_FAILED,
                TaskState.TASK_STATE_CANCELED,
                TaskState.TASK_STATE_REJECTED,
            }:
                state_name = TaskState.Name(state)
                message = f"A2A task failed with state {state_name}"
                raise RuntimeError(message)

    if not texts:
        message = f"A2A agent at {agent_url} returned no text."
        raise RuntimeError(message)
    return delimiter.join(texts).strip()


def parse_queries(text: str, limit: int = 3) -> list[str]:
    queries: list[str] = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        cleaned = cleaned.strip("\"'")
        if cleaned:
            queries.append(cleaned)
        if len(queries) == limit:
            break
    return queries
