"""Direct Gemini Live API proxy for the Chapter 4 app.

This backend intentionally keeps tools inside the live proxy. Chapter 12 rebuilds
the same reader-facing app with ADK, A2A, and MCP boundaries.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import websockets
from google import genai
from google.genai import types

from config import settings
from live_events import function_response_to_browser_messages, server_message_to_browser_messages
from tool_handler import execute_tool, function_declarations


logger = logging.getLogger(__name__)
POLICY_VIOLATION = 1008

SYSTEM_INSTRUCTIONS = """
You are the user-facing live assistant for the Chapter 4 direct Live API app.
Keep answers brief, spoken-friendly, and grounded in the user's live audio, text,
and optional visual context.

For current stock price, quote, ticker, company-name lookup, or short market
context requests, call get_stock_price. Common mappings include
Google/Alphabet -> GOOG, Microsoft -> MSFT, Apple -> AAPL, Nvidia -> NVDA,
Amazon -> AMZN, Meta/Facebook -> META, and Tesla -> TSLA. Preserve source,
as_of, status, and warning information from the tool result. Do not provide
investment advice.

For weather requests, call get_weather and clearly treat its result as
deterministic demo data when the source is mock-weather.

If the user asks about a visible chart, describe what can be inferred from the
visual context. If they ask for latest/current market data, use the stock tool.
"""


def create_live_client() -> genai.Client:
    if not settings.api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY must be set before starting Chapter 4.")
    return genai.Client(api_key=settings.api_key)


def create_live_config() -> types.LiveConnectConfig:
    declarations = [
        types.FunctionDeclaration(
            name=declaration["name"],
            description=declaration["description"],
            parameters=declaration["parameters"],
        )
        for declaration in function_declarations()
    ]
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            language_code="en-US",
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
            ),
        ),
        system_instruction=SYSTEM_INSTRUCTIONS,
        tools=[types.Tool(function_declarations=declarations)],
    )


async def handle_connection(client_ws: Any) -> None:
    origin = getattr(getattr(client_ws, "request", None), "headers", {}).get("origin")
    if not _origin_allowed(origin):
        logger.warning("Rejected WebSocket from disallowed origin: %s", origin)
        await client_ws.close(code=POLICY_VIOLATION)
        return

    logger.info("Browser connected from %s", getattr(client_ws, "remote_address", "unknown"))
    client = create_live_client()
    live_config = create_live_config()

    try:
        async with client.aio.live.connect(model=settings.live_model, config=live_config) as live_session:
            tasks = [
                asyncio.create_task(forward_browser_to_live(client_ws, live_session)),
                asyncio.create_task(forward_live_to_browser(client_ws, live_session)),
            ]
            try:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
                for task in pending:
                    task.cancel()
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
    except websockets.exceptions.ConnectionClosed:
        logger.info("Browser WebSocket closed.")
    except Exception as exc:  # noqa: BLE001 - surface live failures to the browser.
        logger.exception("Live proxy session failed")
        await _safe_send_json(
            client_ws,
            {"type": "error", "message": f"Live session failed: {type(exc).__name__}: {exc}"},
        )
    finally:
        logger.info("Browser disconnected.")


async def forward_browser_to_live(client_ws: Any, live_session: Any) -> None:
    async for message in client_ws:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            await _safe_send_json(client_ws, {"type": "error", "message": "Browser sent invalid JSON."})
            continue

        should_close = await forward_browser_payload(payload, live_session)
        if should_close:
            return


async def forward_browser_payload(payload: dict[str, Any], live_session: Any) -> bool:
    msg_type = payload.get("type")
    if msg_type == "text":
        await live_session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=payload.get("text", ""))]),
            turn_complete=True,
        )
    elif msg_type == "audio":
        await live_session.send_realtime_input(
            audio=types.Blob(
                data=_decode_base64_data(payload["data"]),
                mime_type=payload.get("mime_type", "audio/pcm;rate=16000"),
            )
        )
    elif msg_type == "image":
        await live_session.send_realtime_input(
            video=types.Blob(
                data=_decode_base64_data(payload["data"]),
                mime_type=payload.get("mime_type", "image/jpeg"),
            )
        )
    elif msg_type == "activity_start":
        pass  # Local microphone state; automatic VAD detects speech.
    elif msg_type == "activity_end":
        await live_session.send_realtime_input(audio_stream_end=True)
    elif msg_type == "close":
        return True
    else:
        logger.debug("Ignoring unsupported browser message type: %s", msg_type)
    return False


async def forward_live_to_browser(client_ws: Any, live_session: Any) -> None:
    while True:
        saw_response = False
        async for response in live_session.receive():
            saw_response = True
            await forward_live_response_to_browser(client_ws, live_session, response)
        if not saw_response:
            await asyncio.sleep(0.05)


async def forward_live_response_to_browser(client_ws: Any, live_session: Any, response: Any) -> None:
    for message in server_message_to_browser_messages(response):
        await _safe_send_json(client_ws, message)

    tool_call = getattr(response, "tool_call", None)
    function_calls = getattr(tool_call, "function_calls", None) or []
    if function_calls:
        function_responses = []
        for function_call in function_calls:
            name = function_call.name or ""
            result = await execute_tool(name, function_call.args or {})
            for browser_message in function_response_to_browser_messages(name, result):
                await _safe_send_json(client_ws, browser_message)
            function_responses.append(
                types.FunctionResponse(
                    id=function_call.id,
                    name=name,
                    response={"result": result},
                )
            )
        await live_session.send_tool_response(function_responses=function_responses)


def _origin_allowed(origin: str | None) -> bool:
    if not origin:
        return True
    allowed = {value.rstrip("/") for value in settings.allowed_origins}
    return "*" in allowed or origin.rstrip("/") in allowed


def _decode_base64_data(data: str) -> bytes:
    if "," in data and data.startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


async def _safe_send_json(websocket: Any, payload: dict[str, Any]) -> None:
    try:
        await websocket.send(json.dumps(payload))
    except websockets.exceptions.ConnectionClosed:
        return


async def main() -> None:
    if not settings.api_key:
        logger.warning("GOOGLE_API_KEY or GEMINI_API_KEY is not set; model calls will fail.")
    async with websockets.serve(
        handle_connection,
        settings.proxy_host,
        settings.proxy_port,
        max_size=settings.proxy_max_size,
        ping_interval=30,
        ping_timeout=10,
    ):
        logger.info(
            "Chapter 4 Live API proxy started on ws://%s:%s/live using %s",
            settings.proxy_host,
            settings.proxy_port,
            settings.live_model,
        )
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
