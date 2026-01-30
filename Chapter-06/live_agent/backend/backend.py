import asyncio
import json
import os
import base64
import websockets
from typing import Any, Dict

from google.genai import types
from dotenv import load_dotenv

from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue

from agent.agent import create_math_agent

load_dotenv(os.path.join(os.path.dirname(__file__), '../../..', '.env'))

GOOGLE_GENAI_USE_VERTEXAI = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
if(GOOGLE_GENAI_USE_VERTEXAI=="1"):
    MODEL_LIVE = os.environ.get('MODEL_LIVE_VERTEX', 'gemini-live-2.5-flash-native-audio')
else:
    MODEL_LIVE = os.environ.get('MODEL_LIVE_API', 'gemini-2.5-flash-preview-native-audio-dialog')

async def start_agent_session(root_agent, session_id: str, app_name="agent_math", user_id="user", context: Dict[str, Any]={}) -> Any: 
    """
    Creates and stores a new session, leveraging the new ADK live session runner.
    """

    ### Configuration
    response_modalities_from_config = ["AUDIO"]
    voice = 'Aoede'
    language_code = 'en-GB'

    print(f"""Live Agent Configuration: [MODEL_LIVE: {MODEL_LIVE}, Voice: {voice}, Modalities: {response_modalities_from_config}, Language: {language_code}, Session ID: {session_id}""")

    run_config = RunConfig(
        response_modalities=response_modalities_from_config, 
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfigDict(
                {"prebuilt_voice_config": {"voice_name": voice}}),
            language_code=language_code))
    
    # Start Agent via a Live Runner
    runner = InMemoryRunner(app_name=app_name, agent=root_agent,)

    session_obj = await runner.session_service.create_session(app_name=app_name, user_id=user_id, state=context,)

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(session=session_obj, live_request_queue=live_request_queue, run_config=run_config,)

    print(f"Session {session_id} created successfully.")
    return live_events, live_request_queue

# --- Core Logic ---
async def handle_frontend_messages(client_ws, live_request_queue: LiveRequestQueue):
    """(Unchanged) Listens for messages from the browser and forwards to Gemini."""
    print("-> Starting frontend-to-agent forwarder.")
    try:
        async for message in client_ws:
            try:
                data = json.loads(message)

                if 'realtimeInput' in data and 'mediaChunks' in data['realtimeInput']:
                    for chunk in data['realtimeInput']['mediaChunks']:
                        if chunk.get('mime_type') == 'audio/pcm':
                            audio_bytes = base64.b64decode(chunk['data'])
                            audio_blob = types.Blob(
                                data=audio_bytes,
                                mime_type='audio/pcm;rate=16000'
                            )
                            live_request_queue.send_realtime(audio_blob)
                        else:
                            print(f"WARN: Skipping unknown media chunk mime_type: {chunk.get('mime_type')}")
                else:
                    print(f"WARN: Received unknown message structure from client: {data.keys()}")

            except json.JSONDecodeError:
                print(f"ERROR: Could not decode JSON from client: {message[:100]}")
            except Exception as e:
                print(f"ERROR: Failed processing client message: {e}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"-> Client connection closed (Code: {e.code}, Reason: {e.reason}).")
    except Exception as e:
        print(f"FATAL ERROR in client-to-Gemini forwarder: {e}")
        raise

async def handle_agent_responses(client_ws, live_events):
    """
    (Corrected) Listens for messages from the Gemini session and forwards to the browser.
    This now handles multiple conversational turns.
    """
    print("<- Starting Agent-to-frontend forwarder.")
    try:
        async for event in live_events:
            # --- Interruption ---
            if event.interrupted:
                print("Interrupted event detected")
                await client_ws.send(json.dumps({ "type": "interrupted", 
                                                  "data": { "message": "Response interrupted by user input" } }))
                continue

            if event.content == None:
                if event.turn_complete:
                    await client_ws.send(json.dumps({ "type": "backend", "data": "turn_complete" }))
                continue

            inline_data = (event.content and event.content.parts and event.content.parts[0].inline_data)

            if inline_data and inline_data.mime_type.startswith('audio/pcm'):
                audio_base64 = base64.b64encode(inline_data.data).decode('utf-8')
                await client_ws.send(json.dumps({ "type": "audio",
                                                  "data": audio_base64 }))
                #await client_ws.send(json.dumps(audio_base64))
                continue
            await asyncio.sleep(0)

    except websockets.exceptions.ConnectionClosed:
        print("<- Client connection closed, exiting Gemini forwarder.")
    except Exception as e:
        print(f"FATAL ERROR in Gemini-to-client forwarder: {e}")
        raise

async def handle_connections(client_ws, path=None):
    """Handles a new WebSocket connection from a client browser."""
    print(f"Client connected from {client_ws.remote_address}")

    try:
        session_id = str(id(client_ws))
        root_agent, context = create_math_agent(model=MODEL_LIVE)
        
        live_events, live_request_queue = await start_agent_session(root_agent, session_id, app_name="agent_math", user_id="user", context=context)

        if not live_request_queue:
            raise ValueError("Failed to create live request queue for session.")

        await client_ws.send(json.dumps({"type":"backend", "data":"backend_ready"}))

        await asyncio.gather( handle_frontend_messages(client_ws, live_request_queue),
                              handle_agent_responses(client_ws, live_events),)
    except Exception as e:
        print(f"An error occurred during the session: {e}")
        # Only try to close if the error isn't a connection error itself.
        if not isinstance(e, websockets.exceptions.ConnectionClosed):
            await client_ws.close(1011, "An internal server error occurred.")
    finally:
        print(f"Client from {client_ws.remote_address} disconnected.")


async def main():
    """Starts the WebSocket backend."""
    port = 8081
    async with websockets.serve(handle_connections, "localhost", port):
        print(f"WebSocket backend started on ws://localhost:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())