"""Discovery of A2A specialist agents from their Agent Cards."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from a2a.types import AgentCard
from google.protobuf.json_format import ParseDict

from .config import settings


logger = logging.getLogger(__name__)
AGENT_CARD_PATH = "/.well-known/agent-card.json"


@dataclass(frozen=True)
class DiscoveredSpecialist:
    """A specialist the host can route to through A2A."""

    name: str
    base_url: str
    card: AgentCard


async def discover_specialists(
    base_urls: tuple[str, ...] | list[str] | None = None,
) -> dict[str, DiscoveredSpecialist]:
    """Fetch Agent Cards from configured specialist base URLs."""
    urls = tuple(base_urls or settings.specialist_agent_urls)
    specialists: dict[str, DiscoveredSpecialist] = {}
    if not urls:
        logger.warning("No specialist agent URLs configured.")
        return specialists

    async with httpx.AsyncClient(timeout=10.0) as client:
        for base_url in urls:
            card_url = f"{base_url.rstrip('/')}{AGENT_CARD_PATH}"
            try:
                response = await client.get(card_url)
                response.raise_for_status()
                card = ParseDict(response.json(), AgentCard())
            except Exception as exc:  # noqa: BLE001 - discovery should skip bad peers.
                logger.warning("Could not discover specialist at %s: %s", card_url, exc)
                continue

            if not card.name:
                logger.warning("Skipping specialist at %s because its Agent Card has no name.", card_url)
                continue

            specialists[card.name] = DiscoveredSpecialist(
                name=card.name,
                base_url=base_url.rstrip("/"),
                card=card,
            )
            logger.info("Discovered A2A specialist '%s' at %s", card.name, base_url)

    return specialists


def build_specialist_instruction(specialists: dict[str, DiscoveredSpecialist]) -> str:
    """Render discovered specialist cards into host routing instructions."""
    if not specialists:
        return "No specialist agents were discovered."

    lines = ["Available specialist agents:"]
    for specialist in specialists.values():
        card = specialist.card
        lines.append(f"- {card.name}: {card.description}")
        for skill in card.skills:
            tags = ", ".join(skill.tags)
            detail = f"  Skill {skill.name}: {skill.description}"
            if tags:
                detail = f"{detail} Tags: {tags}."
            lines.append(detail)
    return "\n".join(lines)
