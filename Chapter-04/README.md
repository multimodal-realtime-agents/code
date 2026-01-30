# Chapter 4: Advanced Live Interactions

This folder contains the code examples for **Chapter 4: Advanced Live Interactions: Video, Tools, and System Instructions**.

## Overview
This chapter extends the real-time foundation built in Chapter 3 to include more complex interaction patterns. It explores how to add visual context (video), integrate external tools for the agent to use during the live session, and refine behavior through system instructions.

## Contents
### `backend/`
- **`server.py`**: The proxy server facilitating the connection.

### `frontend/`
- **`app.js`**: The client-side logic handling the WebSocket streaming.
- **`audio-processor.js`**: Audio processing worklet.
- **`audio-streamer.js`**: Audio playback handling.

## Key Concepts
- **Multimodal Inputs**: Processing audio and potentially video streams.
- **Tool Integration**: Enabling the live agent to call functions dynamically.
- **System Instructions**: Steering the agent's personality and constraints.
