"""ADK coordinator agent for the Chapter 9 research workflow."""

from __future__ import annotations

from google.adk.agents import Agent

from chapter9_support.config import settings

try:
    from .a2a_tools import delegate_research
except ImportError:
    from a2a_tools import delegate_research


root_agent = Agent(
    name="chapter_9_research_coordinator",
    model=settings.model,
    description="Coordinates remote A2A research specialists.",
    instruction=(
        "You are a research coordinator. Use delegate_research for research questions. "
        "Return the result from the tool without inventing additional facts."
    ),
    tools=[delegate_research],
)
