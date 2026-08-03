"""FastAPI backend and ADK Live host."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from .config import settings
from .host_agent import create_host_agent
from .live_events import event_to_browser_messages


logger = logging.getLogger(__name__)
APP_NAME = "agent_system_reference"
DEFAULT_USER_ID = "browser-user"
POLICY_VIOLATION = 1008


class Runtime:
    session_service: InMemorySessionService
    runner: Runner


runtime: Runtime | None = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global runtime
    session_service = InMemorySessionService()
    agent = await create_host_agent(model=settings.live_model)
    runtime = Runtime()
    runtime.session_service = session_service
    runtime.runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )
    logger.info("Agent backend initialized with live model %s", settings.live_model)
    yield
    runtime = None


app = FastAPI(title="Reference Live Agent Host", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "live_model": settings.live_model,
        "fallback_live_model": settings.fallback_live_model,
        "a2a_url": settings.a2a_url,
        "weather_a2a_url": settings.weather_a2a_url,
        "mcp_url": settings.mcp_url,
    }


@app.websocket("/live")
async def live(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if not _origin_allowed(origin):
        logger.warning("Rejected live WebSocket from disallowed origin: %s", origin)
        await websocket.close(code=POLICY_VIOLATION)
        return

    await websocket.accept()
    user_id = websocket.query_params.get("user_id", DEFAULT_USER_ID)
    session_id = websocket.query_params.get("session_id", str(uuid.uuid4()))
    await _get_or_create_session(user_id, session_id)

    live_request_queue = LiveRequestQueue()

    async def upstream() -> None:
        while True:
            payload = await websocket.receive_json()
            if _forward_browser_payload(payload, live_request_queue):
                return

    async def downstream() -> None:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                language_code="en-US",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                ),
            ),
        )
        try:
            async with contextlib.aclosing(
                _runtime().runner.run_live(
                    user_id=user_id,
                    session_id=session_id,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                )
            ) as events:
                async for event in events:
                    for message in event_to_browser_messages(event):
                        await websocket.send_json(message)
        except Exception as exc:  # noqa: BLE001 - surface model/session failures to browser.
            logger.exception("Live session failed for %s", session_id)
            with contextlib.suppress(Exception):
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Live session failed: {type(exc).__name__}: {exc}",
                    }
                )
            return

    tasks = [asyncio.create_task(upstream()), asyncio.create_task(downstream())]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("Browser live session disconnected: %s", session_id)
    finally:
        live_request_queue.close()
        for task in tasks:
            if not task.done():
                task.cancel()


def _runtime() -> Runtime:
    if runtime is None:
        raise RuntimeError("Backend runtime has not initialized.")
    return runtime


def _origin_allowed(origin: str | None) -> bool:
    if not origin:
        return True
    allowed = {value.rstrip("/") for value in settings.allowed_origins}
    return "*" in allowed or origin.rstrip("/") in allowed


def _forward_browser_payload(payload: dict[str, Any], live_request_queue: LiveRequestQueue) -> bool:
    """Forward one browser message to ADK.

    Returns True when the browser requested the session to close.
    """
    msg_type = payload.get("type")
    if msg_type == "text":
        live_request_queue.send_content(
            types.Content(role="user", parts=[types.Part(text=payload.get("text", ""))])
        )
    elif msg_type == "audio":
        live_request_queue.send_realtime(
            types.Blob(
                data=_decode_base64_data(payload["data"]),
                mime_type=payload.get("mime_type", "audio/pcm;rate=16000"),
            )
        )
    elif msg_type == "image":
        live_request_queue.send_realtime(
            types.Blob(
                data=_decode_base64_data(payload["data"]),
                mime_type=payload.get("mime_type", "image/jpeg"),
            )
        )
    elif msg_type == "activity_start":
        live_request_queue.send_activity_start()
    elif msg_type == "activity_end":
        live_request_queue.send_activity_end()
    elif msg_type == "close":
        return True
    return False


def _decode_base64_data(data: str) -> bytes:
    if "," in data and data.startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


async def _get_or_create_session(user_id: str, session_id: str) -> None:
    rt = _runtime()
    session = await rt.session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await rt.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY is not set; model calls will fail until it is configured.")
    uvicorn.run(app, host=settings.backend_host, port=settings.backend_port)
