"""ADK agent that can greet a remote A2A service."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState
from google.adk.agents import Agent

from chapter9_support.config import settings


async def greet_remote_agent(agent_url: str = settings.greeter_url) -> str:
    """Connect to a remote A2A agent, send a greeting, and return its response."""
    print(f"Attempting to greet remote agent at {agent_url}...")

    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
        print("Step 1: Discovering agent and creating A2A client...")
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
            print("Step 2: Sending message...")
            request = SendMessageRequest(
                message=Message(
                    role=Role.ROLE_USER,
                    message_id=str(uuid.uuid4()),
                    context_id=str(uuid.uuid4()),
                    parts=[Part(text="Hi from your ADK friend!")],
                )
            )
            response = await collect_text_response(client.send_message(request), agent_url)
        finally:
            await client.close()

    print(f"--> Received response: {response!r}")
    return f"Success. The remote agent said: {response}"


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


root_agent = Agent(
    name="chapter_9_initiator",
    model=settings.model,
    description="A small ADK agent that greets a remote A2A service.",
    instruction=(
        "Use greet_remote_agent to greet the remote A2A agent. "
        "Return the remote agent's answer without adding unrelated detail."
    ),
    tools=[greet_remote_agent],
)
