

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional

from .tools import check_grammar
from .prompt import instruction_prompt

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../../../.env'))

MODEL = os.getenv("MODEL", "gemini-2.5-flash")

def callback_before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
  # Guardrail 1: Do we have the student profile?
  if not callback_context.state.get("student_profile"):
    return types.Content(role='model', parts=[types.Part(text="Error: Cannot find student profile.")])
  return None

agent_grammar = Agent(
  model=MODEL,
  name='agent_grammar',
  description="This agent corrects grammar mistakes in text provided by children, explains the errors in simple terms, and returns both the corrected text and the explanations.",
  instruction=instruction_prompt,
  tools=[check_grammar],
  output_key="grammar_response",
  before_agent_callback=callback_before_agent,
)