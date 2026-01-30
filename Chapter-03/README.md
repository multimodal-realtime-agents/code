# Chapter 3: Architecting for Real-Time AI Interaction

This folder contains the code examples for **Chapter 3: Architecting for Real-Time AI Interaction**.

## Overview
This chapter introduces the fundamental architecture for building real-time, bidirectional AI agents. It sets up a client-server model where audio is streamed from the browser to a backend, processed, and responded to in real-time.

## Contents
### `backend/`
- **`server.py`**: A lightweight proxy server that handles cross-origin (CORS) requests and serves the frontend application. It acts as the bridge between the browser client and the backend processing logic (conceptually).

### `frontend/`
- **`index.html`**: The user interface for the real-time agent, featuring microphone controls and status indicators.
- **`app.js`**: Core application logic managing the AudioContext, WebSocket connections, and UI state.
- **`audio-processor.js`**: An AudioWorkletProcessor that handles raw audio generation and processing in a dedicated thread to ensure glitch-free audio processing.
- **`audio-streamer.js`**: Handles the buffering and scheduling of incoming audio chunks from the AI agent to play them back smoothly to the user.

## Key Concepts
- **AudioWorklets**: Using modern Web Audio API for low-latency audio processing.
- **Bidirectional Streaming**: Full-duplex communication for natural turn-taking.
- **PCM Audio**: Handling raw 16-bit PCM audio streams.
