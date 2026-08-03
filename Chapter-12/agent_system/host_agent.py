"""ADK host/router agent for the reference system."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from google.adk.agents import Agent

from .a2a_client import ask_specialist
from .config import settings
from .specialist_registry import (
    DiscoveredSpecialist,
    build_specialist_instruction,
    discover_specialists,
)


DiscoverFn = Callable[[], Awaitable[dict[str, DiscoveredSpecialist]]]


class SpecialistDirectory:
    """Startup discovery plus lazy rediscovery for A2A specialists."""

    def __init__(
        self,
        specialists: dict[str, DiscoveredSpecialist] | None = None,
        discover: DiscoverFn = discover_specialists,
    ) -> None:
        self._specialists = specialists or {}
        self._discover = discover
        self._lock = asyncio.Lock()

    @classmethod
    async def create(cls) -> "SpecialistDirectory":
        return cls(await discover_specialists())

    @property
    def specialists(self) -> dict[str, DiscoveredSpecialist]:
        return dict(self._specialists)

    def instruction(self) -> str:
        return build_specialist_instruction(self._specialists)

    async def get(self, name: str) -> DiscoveredSpecialist | None:
        specialist = self._lookup(name)
        if specialist is not None:
            return specialist

        await self.refresh()
        return self._lookup(name)

    async def refresh(self) -> None:
        async with self._lock:
            discovered = await self._discover()
            if discovered:
                self._specialists = discovered

    def _lookup(self, name: str) -> DiscoveredSpecialist | None:
        if name in self._specialists:
            return self._specialists[name]
        normalized = name.casefold()
        for specialist_name, specialist in self._specialists.items():
            if specialist_name.casefold() == normalized:
                return specialist
        return None


def _make_delegate_tool(directory: SpecialistDirectory):
    async def delegate_task_to_specialist(specialist_name: str, request: str) -> dict[str, Any] | str:
        """Delegate a request to a discovered specialist agent by exact name."""
        specialist = await directory.get(specialist_name)
        if specialist is None:
            available = ", ".join(sorted(directory.specialists)) or "none"
            return f"Specialist '{specialist_name}' was not discovered. Available: {available}."
        return await ask_specialist(request, specialist.base_url)

    return delegate_task_to_specialist


async def create_host_agent(model: str | None = None) -> Agent:
    directory = await SpecialistDirectory.create()
    delegate_task_to_specialist = _make_delegate_tool(directory)
    return Agent(
        name="agent_system_host_agent",
        model=model or settings.live_model,
        description="User-facing live host that routes requests to discovered A2A specialists.",
        instruction=(
            "You are the live host/router agent. Keep answers brief and spoken-friendly. "
            "Route requests to discovered specialist agents when their skills match the user's request. "
            "For stock price or market context requests, call delegate_task_to_specialist with the exact "
            "stock specialist name from the discovered Agent Card and pass the user's natural-language "
            "request through as the request. Do not pre-extract ticker symbols; the specialist owns that "
            "step. If no stock specialist was discovered at startup, still try the specialist name "
            "'Stock Specialist'; the tool will rediscover available A2A Agent Cards before failing. "
            "For weather requests, use the same delegation pattern with 'Weather Specialist' and do not "
            "pre-extract or rewrite the city unless the user clearly named it. If no weather specialist "
            "was discovered at startup, still try the specialist name 'Weather Specialist'; the tool will "
            "rediscover available A2A Agent Cards before failing. Specialists return structured data. Use "
            "that data to answer in one or two concise spoken-friendly sentences, preserving source, as_of, "
            "and warning information when present. Do not ask specialists for polished prose as the primary "
            "result.\n\n"
            f"{directory.instruction()}"
        ),
        tools=[delegate_task_to_specialist],
    )
