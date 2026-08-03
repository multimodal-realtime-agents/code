"""Browser event shaping for Chapter 3 direct Live API messages."""

from __future__ import annotations

import base64
import json
from typing import Any


def server_message_to_browser_messages(message: Any) -> list[dict[str, Any]]:
    """Convert Live API SDK messages into a small browser-facing vocabulary."""
    data = _to_dict(message)
    messages: list[dict[str, Any]] = []

    server_content = data.get("serverContent") or data.get("server_content") or {}
    if server_content:
        messages.extend(_server_content_messages(server_content))

    if "goAway" in data or "go_away" in data:
        messages.append({"type": "go_away"})

    return messages


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
            messages.append({"type": msg_type, "text": transcription["text"], "partial": True})

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
