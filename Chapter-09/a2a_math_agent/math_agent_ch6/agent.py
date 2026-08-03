"""Chapter 6 Math Agent adapted for the Chapter 9 A2A wrapper.

Source: upstream Chapter-06/basic_agent/agent_maths/agent.py at commit
12ff67c0c02875eb4a39f92141e54b411f7cac19.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.genai import types

from chapter9_support.config import settings

from .tools import add, divide, multiply, subtract


def create_math_agent(model: str | None = None) -> Agent:
    return Agent(
        model=model or settings.model,
        name="agent_math",
        description=(
            "Performs basic arithmetic operations: addition, subtraction, "
            "multiplication, and division."
        ),
        instruction=(
            "You perform addition, subtraction, multiplication, and division on "
            "numbers provided by the user. Use the available tools and answer "
            "briefly with the result."
        ),
        generate_content_config=types.GenerateContentConfig(temperature=0.2),
        tools=[add, subtract, multiply, divide],
    )


root_agent = create_math_agent()
