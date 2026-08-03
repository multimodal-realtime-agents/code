"""Run the Chapter 9 research coordinator."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chapter9_support.adk_runtime import run_agent_text

try:
    from .agent import root_agent
except ImportError:
    from agent import root_agent


async def main() -> None:
    topic = " ".join(sys.argv[1:]) or "What is the A2A protocol?"
    print(f"--- Running Research Coordinator for: {topic!r} ---")
    result = await run_agent_text(root_agent, topic, app_name="chapter_9_research_coordinator")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
