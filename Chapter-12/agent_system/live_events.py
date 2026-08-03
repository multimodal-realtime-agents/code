"""Defensive event parsing for Gemini 3.1 Live / ADK events."""

from __future__ import annotations

import base64
import json
from typing import Any


def event_to_browser_messages(event: Any) -> list[dict[str, Any]]:
    """Convert an ADK event into small browser messages.

    Gemini 3.1 Live events may contain multiple content parts, so this parser
    iterates every part instead of assuming one part per event.
    """
    data = _to_dict(event)
    messages: list[dict[str, Any]] = []

    if data.get("errorMessage") or data.get("error_message"):
        messages.append(
            {"type": "error", "message": data.get("errorMessage") or data.get("error_message")}
        )

    for key, msg_type in (
        ("inputTranscription", "input_transcript"),
        ("input_transcription", "input_transcript"),
        ("outputTranscription", "output_transcript"),
        ("output_transcription", "output_transcript"),
    ):
        transcription = data.get(key)
        if transcription and transcription.get("text"):
            messages.append(
                {
                    "type": msg_type,
                    "text": transcription["text"],
                    "partial": bool(data.get("partial")),
                }
            )

    content = data.get("content") or {}
    for part in content.get("parts") or []:
        if part.get("text"):
            messages.append(
                {
                    "type": "text",
                    "text": part["text"],
                    "partial": bool(data.get("partial")),
                    "role": content.get("role"),
                }
            )

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

        function_call = part.get("functionCall") or part.get("function_call")
        if function_call:
            messages.append({"type": "function_call", "function_call": function_call})

        function_response = part.get("functionResponse") or part.get("function_response")
        if function_response:
            messages.append({"type": "function_response", "function_response": function_response})
            provenance = _provenance_from_function_response(function_response)
            if provenance is not None:
                messages.append({"type": "provenance", **provenance})

    if data.get("turnComplete") or data.get("turn_complete"):
        messages.append({"type": "turn_complete"})
    if data.get("interrupted"):
        messages.append({"type": "interrupted"})

    return messages


def _provenance_from_function_response(function_response: dict[str, Any]) -> dict[str, Any] | None:
    result = _function_response_result(function_response)
    if not isinstance(result, dict):
        return None

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


def _function_response_result(function_response: dict[str, Any]) -> Any:
    response = function_response.get("response") or {}
    if not isinstance(response, dict):
        return None

    result = response.get("result", response)
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return result
        return parsed
    return result


def _to_dict(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump(exclude_none=True, by_alias=True)
    if hasattr(event, "dict"):
        return event.dict(exclude_none=True, by_alias=True)
    raise TypeError(f"Unsupported event type: {type(event)!r}")
