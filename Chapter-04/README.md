# Chapter 4: Advanced Live Interactions

This folder contains the code examples for **Chapter 4: Advanced Live Interactions: Video, Tools, and System Instructions**.

## Overview
This chapter extends the real-time foundation built in Chapter 3 to include more complex interaction patterns. It explores how to add visual context (video), integrate external tools for the agent to use during the live session, and refine behavior through system instructions.

## Contents
### `backend/`
- **`server.py`**: A simple HTTP server for the frontend.
- **`proxy/`**: The advanced WebSocket proxy (`proxy.py`) supporting tools and video.

### `frontend/`
- **`app.js`**: Updated client logic for handling video frames and tool outputs.

## How to Run

### Prerequisites
1.  **Google Cloud Project**: Ensure Vertex AI API is enabled.
2.  **Environment Variables**: Create a `.env` file in `backend/proxy/`:
    ```env
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    MODEL=gemini-2.5-flash
    ```

### 1. Start the Advanced Proxy
```bash
cd backend/proxy
pip install -r requirements.txt
python proxy.py
```
*The proxy will start on `localhost:8081`.*

### 2. Start the Frontend Server
In a new terminal window:
```bash
cd backend
python server.py
```
*The server will start on `localhost:8000`.*

### 3. Usage
Open [http://localhost:8000](http://localhost:8000). You may need to grant camera permissions if video is enabled. Start the session and try asking the agent questions that require visual context or tool usage.
