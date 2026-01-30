import asyncio
import json
import os
import base64
import websockets
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
client = None

# --- Server-side Configuration ---
MODEL_NAME = "gemini-2.0-flash-live-preview-04-09"

# NEW: Add system instructions to define the AI's persona and rules.
SYSTEM_INSTRUCTIONS = """
You are a friendly and helpful conversational assistant.
Your voice should be clear, professional, and engaging.
Keep your responses concise and to the point.
"""

# UPDATED: Add speech_config to select a specific voice.
GENERATION_CONFIG = {
    "response_modalities": ["audio"],
    "speech_config": "Puck" 
}

# Attempt to initialize with Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")

if PROJECT_ID:
    LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    print(f"Attempting to connect to Vertex AI with Project: {PROJECT_ID}, Location: {LOCATION}")
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        print("Successfully connected to Vertex AI.")
    except Exception as e:
        print(f"Vertex AI client initialization failed: {e}.")
        print("Falling back to Gemini API key.")
        client = None # Reset client
else:
    print("GOOGLE_CLOUD_PROJECT not set. Trying Gemini API key.")

# If Vertex AI failed or wasn't configured, try API key.
if not client:
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if API_KEY:
        print("Attempting to connect with Gemini API Key.")
        try:
            client = genai.Client(api_key=API_KEY)
            print("Successfully connected with Gemini API key.")
        except Exception as e:
            print(f"Gemini API key client initialization failed: {e}")
            client = None # Reset client
    else:
        print("GEMINI_API_KEY or GOOGLE_API_KEY not found.")

if not client:
    raise ValueError(
        "Could not create a client. "
        "Please set GOOGLE_CLOUD_PROJECT for Vertex AI, "
        "or set GEMINI_API_KEY/GOOGLE_API_KEY for the Gemini API."
    )


# --- Custom JSON Encoder ---
class BytesJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return super().default(obj)


# --- Core Logic ---
async def forward_client_to_gemini(client_ws, gemini_session):
    """(Unchanged) Listens for messages from the browser and forwards to Gemini."""
    print("-> Starting client-to-Gemini forwarder.")
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
                            await gemini_session.send_realtime_input(audio=audio_blob)
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

async def forward_gemini_to_client(client_ws, gemini_session):
    """
    (Corrected) Listens for messages from the Gemini session and forwards to the browser.
    This now handles multiple conversational turns.
    """
    print("<- Starting Gemini-to-client forwarder.")
    try:
        while True:
            print("<- Awaiting next turn from Gemini...")
            turn_active = False
            async for response in gemini_session.receive():
                turn_active = True
                try:
                    if hasattr(response, 'model_dump'):
                        message_dict = response.model_dump()
                        json_message = json.dumps(message_dict, cls=BytesJSONEncoder)
                    else:
                        json_message = json.dumps(str(response))
                    
                    await client_ws.send(json_message)
                except Exception as e:
                    print(f"ERROR: Failed to process or send Gemini message: {e}")
                    # Only try to send an error if the connection is still likely open.
                    if not isinstance(e, websockets.exceptions.ConnectionClosed):
                         error_msg = json.dumps({"error": f"Failed to process server message: {str(e)}"})
                         await client_ws.send(error_msg)
                    else:
                        raise # Re-raise ConnectionClosed to exit the function
            
            if turn_active:
                print("<- Gemini turn complete. Ready for the next one.")
            else:
                await asyncio.sleep(0.1)

    except websockets.exceptions.ConnectionClosed:
        print("<- Client connection closed, exiting Gemini forwarder.")
    except Exception as e:
        print(f"FATAL ERROR in Gemini-to-client forwarder: {e}")
        raise

async def handle_connection(client_ws, path=None):
    """Handles a new WebSocket connection from a client browser."""
    print(f"Client connected from {client_ws.remote_address}")
    try:
        # Configuration is now defined on the server, not sent by the client.
        print(f"Using server-defined model: {MODEL_NAME}")

        async with client.aio.live.connect(
            model=MODEL_NAME,
            config=GENERATION_CONFIG,
            system_instruction=SYSTEM_INSTRUCTIONS
        ) as gemini_session:
            print("Successfully connected to Gemini Live API.")
            await asyncio.gather(
                forward_client_to_gemini(client_ws, gemini_session),
                forward_gemini_to_client(client_ws, gemini_session),
            )
    except Exception as e:
        print(f"An error occurred during the session: {e}")
        # Only try to close if the error isn't a connection error itself.
        if not isinstance(e, websockets.exceptions.ConnectionClosed):
            await client_ws.close(1011, "An internal server error occurred.")
    finally:
        print(f"Client from {client_ws.remote_address} disconnected.")


async def main():
    """Starts the WebSocket proxy server."""
    port = 8081
    async with websockets.serve(handle_connection, "localhost", port):
        print(f"WebSocket proxy server started on ws://localhost:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())