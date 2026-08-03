"""Run the Chapter 9 ADK Initiator."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from chapter9_support.adk_runtime import run_agent_text
from chapter9_support.config import settings

try:
    from .initiator_agent import root_agent
except ImportError:
    from initiator_agent import root_agent


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else f"Please greet the agent at {settings.greeter_url}."
    print(f"--- Running ADK Initiator with query: {query!r} ---")
    result = await run_agent_text(root_agent, query, app_name="chapter_9_initiator")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
