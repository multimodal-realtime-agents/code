"""CLI client for the Chapter 9 A2A Math Agent."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chapter9_support.config import settings


async def ask_math_agent(query: str, agent_url: str = settings.math_url) -> str:
    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
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
            request = SendMessageRequest(
                message=Message(
                    role=Role.ROLE_USER,
                    message_id=str(uuid.uuid4()),
                    context_id=str(uuid.uuid4()),
                    parts=[Part(text=query)],
                )
            )
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


async def main() -> None:
    query = " ".join(sys.argv[1:]) or "What is 5 times 12?"
    answer = await ask_math_agent(query)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
