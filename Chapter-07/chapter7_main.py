import os
import time
import asyncio

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

# Import our main orchestrator agent
from agent_teaching_assistant.agent import root_agent

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configuration
AGENT_APP_NAME = "teaching_assistant_app"
USER_ID = "alex_user_123"
SESSION_ID = "alex_session_456"

session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

async def send_query_to_agent(agent, query, user_id="user", session_id="user_session"):
    """Sends a query to the specified agent and prints the response.

        Args:
            agent: The agent to send the query to.
            query: The query to send to the agent.

        Returns:
            A tuple containing the elapsed time (in milliseconds) and the final response from the agent.
    """

    # Create a new session - if you want to keep the history of interruction you need to move the 
    # creation of the session outside of this function. Here we create a new session per query
    session = await session_service.create_session(app_name=AGENT_APP_NAME,
                                                   user_id=user_id,
                                                   session_id=session_id)
    # Create a content object representing the user's query
    print('\nUser Query: ', query)
    content = types.Content(role='user', parts=[types.Part(text=query)])

    # Start a timer to measure the response time
    start_time = time.time()

    # Create a runner object to manage the interaction with the agent
    runner = Runner(app_name=AGENT_APP_NAME, agent=agent, artifact_service=artifact_service, session_service=session_service)
    # Alternatively you can use InMemoryRunner

    # Run the interaction with the agent and get a stream of events
    events = runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

    final_response = None
    elapsed_time_ms = 0.0

    # Loop through the events returned by the runner
    async for event in events:

        is_final_response = event.is_final_response()
        function_calls = event.get_function_calls()
        function_responses = event.get_function_responses()

        if not event.content:
             continue

        if is_final_response:
            end_time = time.time()
            elapsed_time_ms = round((end_time - start_time) * 1000, 3)

            print("-----------------------------")
            print('>>> Inside final response <<<')
            print("-----------------------------")
            final_response = event.content.parts[0].text # Get the final response from the agent
            print(f'Agent: {event.author}')
            print(f'Response time: {elapsed_time_ms} ms\n')
            print(f'Final Response:\n{final_response}')
            print("----------------------------------------------------------\n")
        elif function_calls:
            print("-----------------------------")
            print('+++ Inside function call +++')
            print("-----------------------------")
        
            print(f'Agent: {event.author}')
            for function_call in function_calls:
                print(f'Call Function: {function_call.name}')
                print(f'Argument: {function_call.args}')
        elif function_responses:
            print("------------------------------")
            print('-- Inside function response --')
            print("------------------------------")

            print(f'Agent: {event.author}')
            for function_response in function_responses:
                    print(f'Function Name: {function_response.name}')
                    print(f'Function Results: {function_response.response}')

    return elapsed_time_ms, final_response

async def main():
    # Let's try the query from our original draft,
    # complete with a grammar mistake.
    query1 = "Hi teacher. Could she help me to multiply all the numbers between 1 and 10?"
    await send_query_to_agent(root_agent, query1, USER_ID, SESSION_ID)

    # We can even ask a follow-up, though our simple agent
    # will run the full pipeline again.
    query2 = "what about 1 plus 1"
    await send_query_to_agent(root_agent, query2, USER_ID, SESSION_ID)

if __name__ == "__main__":
    asyncio.run(main())
