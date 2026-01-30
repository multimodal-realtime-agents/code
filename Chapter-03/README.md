# Chapter 3: Architecting for Real-Time AI Interaction

This folder contains the code examples for **Chapter 3: Architecting for Real-Time AI Interaction**.

## Overview
This chapter introduces the fundamental architecture for building real-time, bidirectional AI agents. It sets up a client-server model where audio is streamed from the browser to a backend, processed, and responded to in real-time.

## Contents
### `backend/`
- **`server.py`**: A simple HTTP server that serves the frontend and handles CORS.
- **`proxy/`**: Contains the WebSocket proxy server (`proxy.py`) that connects to the Gemini API.

### `frontend/`
- **`index.html`**, **`app.js`**: The client application.

## How to Run

### Prerequisites
1.  **Google Cloud Project**: Ensure Vertex AI API is enabled.
2.  **Environment Variables**: Create a `.env` file in `backend/proxy/` or the root:
    ```env
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    MODEL=gemini-2.5-flash
    ```

### 1. Start the WebSocket Proxy
The proxy handles the audio stream and connection to Gemini.
```bash
cd backend/proxy
pip install -r ../../../requirements.txt
python proxy.py
```
*The proxy will start on `localhost:8081`.*

### 2. Start the Frontend Server
In a new terminal window, serve the frontend files.
```bash
cd backend
python server.py
```
*The server will start on `localhost:8000`.*

### 3. Usage
Open your browser to [http://localhost:8000](http://localhost:8000). Click the microphone button to start the session and talk to the agent.
