from google.adk.agents import SequentialAgent

from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional

from .sub_agents.agent_math.agent import agent_math
from .sub_agents.agent_grammar.agent import agent_grammar
from .sub_agents.agent_summary.agent import agent_summary

from .context import context

async def callback_before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Injects the initial student_profile into the session state
    if it doesn't already exist.
    """
    if not callback_context.state.get("student_profile"):
        try:
            callback_context.state["student_profile"] = context["student_profile"]
        except:
            return types.Content(role='model', parts=[types.Part(text="Error: Cannot find student profile.")])
    return None

root_agent = SequentialAgent(
        name="agent_teaching_assistant",
        description="This agent acts as a friendly teaching assistant, checking the grammar of kids' questions, performing math calculations using corrected or original text (if grammatically correct), and providing results or grammar feedback in a friendly tone.",
        sub_agents=[agent_grammar, agent_math, agent_summary],   
        before_agent_callback=callback_before_agent,     
    )

