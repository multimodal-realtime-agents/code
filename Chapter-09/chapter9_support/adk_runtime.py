"""Small ADK runner helpers used by Chapter 9 examples."""

from __future__ import annotations

import re
import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from .config import settings


def event_text(event: object) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    return "".join(part.text for part in parts if getattr(part, "text", None)).strip()


def _deterministic_math(prompt: str) -> str:
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", prompt)]
    lowered = prompt.lower()
    if len(numbers) < 2:
        return "Please provide two numbers."

    left, right = numbers[0], numbers[1]
    if any(word in lowered for word in ["times", "multiply", "product"]):
        result = left * right
    elif any(word in lowered for word in ["divide", "quotient"]):
        if right == 0:
            return "Cannot divide by zero."
        result = left / right
    elif any(word in lowered for word in ["subtract", "minus"]):
        result = left - right
    else:
        result = left + right

    if result.is_integer():
        return str(int(result))
    return str(result)


async def _run_deterministic_agent_text(prompt: str, app_name: str) -> str:
    if app_name == "chapter_9_initiator":
        try:
            from a2a_handshake.adk_initiator.initiator_agent import greet_remote_agent
        except ImportError:
            from initiator_agent import greet_remote_agent

        return await greet_remote_agent()

    if app_name == "chapter_9_math_agent":
        return _deterministic_math(prompt)

    if app_name == "chapter_9_researcher":
        return (
            f"Deterministic research note for {prompt}. "
            "Source contract not included in this teaching smoke path."
        )

    if app_name == "chapter_9_research_coordinator":
        try:
            from research_coordinator.a2a_tools import delegate_research
        except ImportError:
            from a2a_tools import delegate_research

        return await delegate_research(prompt)

    return f"Deterministic ADK response for {prompt}"


async def run_agent_text(agent: Agent, prompt: str, app_name: str) -> str:
    if settings.deterministic_smoke:
        return await _run_deterministic_agent_text(prompt, app_name)

    session_service = InMemorySessionService()
    user_id = "chapter-9-user"
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )
    runner = Runner(app_name=app_name, agent=agent, session_service=session_service)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    texts: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        text = event_text(event)
        if text:
            texts.append(text)

    return " ".join(texts).strip()
