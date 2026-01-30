from google.adk.agents import Agent
from google.genai import types

from .tools import add, subtract, multiply, divide
from .prompt import instruction_prompt
from .context import context
from .examples import examples

MODEL = "gemini-2.0-flash-exp" #"gemini-2.5-flash"

def create_math_agent(model=MODEL):
    context["examples"] = examples

    math_agent = Agent(
        model=model,
        name="agent_math",
        description="This agent performs basic arithmetic operations (addition, subtraction, multiplication, and division) on user-provided numbers, including ranges.",
        instruction=instruction_prompt,
        generate_content_config=types.GenerateContentConfig(temperature=0.2),
        tools=[add, subtract, multiply, divide],)

    return math_agent, context