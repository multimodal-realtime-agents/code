from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional

from .prompt import instruction_prompt

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))

MODEL = os.getenv("MODEL", "gemini-2.5-flash")

async def callback_before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
        # Guardrail 1: Do we have the student profile?
        if not callback_context.state.get("student_profile"):
                return types.Content(role='model', parts=[types.Part(text="Error: Cannot find student profile.")])

        # Guardrail 2: Did the grammar agent run?
        if not callback_context.state.get("grammar_response"):
                return types.Content(role='model', parts=[types.Part(text="Error: Grammar Agent hasn't responded yet.")])

        # Guardrail 3: Did the math agent run?
        if not callback_context.state.get("math_response"):
                return types.Content(role='model', parts=[types.Part(text="Error: Math Agent hasn't responded yet.")])

        return None # Allow model call to proceed

agent_summary = Agent(
    model=MODEL,
    name="agent_summary",
    description="Synthesizes grammar corrections/explanations and math calculation results, presenting them as a single, coherent response with a patient and encouraging tone suitable for a young user.",
    instruction=instruction_prompt,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    output_key="summary_response",
    before_agent_callback=callback_before_agent
)