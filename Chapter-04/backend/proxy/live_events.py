"""Browser event shaping for direct Gemini Live API messages."""

from __future__ import annotations

import base64
import json
from typing import Any


def server_message_to_browser_messages(message: Any) -> list[dict[str, Any]]:
    data = _to_dict(message)
    messages: list[dict[str, Any]] = []

    server_content = data.get("serverContent") or data.get("server_content") or {}
    if server_content:
        messages.extend(_server_content_messages(server_content))

    tool_call = data.get("toolCall") or data.get("tool_call")
    if tool_call:
        for function_call in tool_call.get("functionCalls") or tool_call.get("function_calls") or []:
            messages.append({"type": "function_call", "function_call": function_call})

    if data.get("goAway") or data.get("go_away"):
        messages.append({"type": "go_away"})

    return messages


def function_response_to_browser_messages(name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    response = {"name": name, "response": {"result": result}}
    messages = [{"type": "function_response", "function_response": response}]
    provenance = provenance_from_tool_result(result)
    if provenance is not None:
        messages.append({"type": "provenance", **provenance})
    return messages


def provenance_from_tool_result(result: dict[str, Any]) -> dict[str, Any] | None:
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        provenance = result if result.get("kind") and result.get("fields") else None
    if not isinstance(provenance, dict):
        return None

    fields = provenance.get("fields")
    if not isinstance(fields, dict):
        return None

    required = ("title", "kind", "source", "status")
    if any(not provenance.get(key) for key in required):
        return None

    return {
        "title": str(provenance["title"]),
        "kind": str(provenance["kind"]),
        "source": str(provenance["source"]),
        "as_of": provenance.get("as_of"),
        "status": str(provenance["status"]),
        "warning": provenance.get("warning"),
        "fields": fields,
    }


def _server_content_messages(server_content: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    for key, msg_type in (
        ("inputTranscription", "input_transcript"),
        ("input_transcription", "input_transcript"),
        ("outputTranscription", "output_transcript"),
        ("output_transcription", "output_transcript"),
    ):
        transcription = server_content.get(key)
        if transcription and transcription.get("text"):
            messages.append({"type": msg_type, "text": transcription["text"], "partial": False})

    model_turn = server_content.get("modelTurn") or server_content.get("model_turn") or {}
    for part in model_turn.get("parts") or []:
        if part.get("text"):
            messages.append({"type": "text", "text": part["text"], "partial": False})

        inline_data = part.get("inlineData") or part.get("inline_data")
        if inline_data and inline_data.get("data"):
            audio_data = inline_data["data"]
            if isinstance(audio_data, bytes):
                audio_data = base64.b64encode(audio_data).decode("ascii")
            messages.append(
                {
                    "type": "audio",
                    "data": audio_data,
                    "mime_type": inline_data.get("mimeType")
                    or inline_data.get("mime_type")
                    or "audio/pcm;rate=24000",
                }
            )

    if server_content.get("interrupted"):
        messages.append({"type": "interrupted"})
    if server_content.get("turnComplete") or server_content.get("turn_complete"):
        messages.append({"type": "turn_complete"})
    return messages


def _to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True, by_alias=True)
    if hasattr(message, "dict"):
        return message.dict(exclude_none=True, by_alias=True)
    if isinstance(message, str):
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
