"""Official A2A client helper used by the ADK host agent and smoke checks."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState
from google.protobuf.json_format import MessageToDict


async def ask_specialist(query: str, agent_url: str) -> dict[str, Any]:
    """Send a request to an A2A specialist and collect its structured response."""
    base_url = agent_url
    async with httpx.AsyncClient(timeout=20.0) as httpx_client:
        client = await create_client(
            base_url,
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
            return await _collect_specialist_result(client.send_message(request))
        finally:
            await client.close()


async def _collect_specialist_result(stream: Any) -> dict[str, Any]:
    """Collect structured A2A data parts, with text as an explicit fallback."""
    data_results: list[dict[str, Any]] = []
    texts: list[str] = []
    async for event in stream:
        if event.HasField("message"):
            data_results.extend(_data_parts(event.message.parts))
            text = get_message_text(event.message, delimiter=" ").strip()
            if text:
                texts.append(text)
            continue

        if event.HasField("task") and event.task.artifacts:
            for artifact in event.task.artifacts:
                data_results.extend(_data_parts(artifact.parts))
                text = get_artifact_text(artifact, delimiter=" ").strip()
                if text:
                    texts.append(text)
            continue

        if event.HasField("artifact_update"):
            data_results.extend(_data_parts(event.artifact_update.artifact.parts))
            text = get_artifact_text(event.artifact_update.artifact, delimiter=" ").strip()
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
                raise RuntimeError(f"A2A task failed with state {TaskState.Name(state)}")

    if data_results:
        return data_results[-1]
    if texts:
        text = " ".join(texts)
        return {
            "kind": "specialist_text",
            "status": "text_only",
            "text": text,
            "warning": (
                "The A2A specialist returned text only, so the browser cannot show "
                "structured tool-result provenance for this turn."
            ),
        }
    raise RuntimeError("A2A specialist returned no structured data or text.")


def _data_parts(parts: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for part in parts:
        if part.HasField("data"):
            results.append(MessageToDict(part.data))
            continue
        if part.HasField("text") and part.media_type == "application/json":
            try:
                parsed = json.loads(part.text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                results.append(parsed)
    return results
