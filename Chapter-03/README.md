# Chapter 3: Audio-Only Gemini Live Agent

This folder contains the runnable Chapter 3 companion app. The browser captures
microphone audio, streams it through a local WebSocket proxy to Gemini Live,
plays streamed audio responses, and shows live input and output captions.

The app intentionally excludes tools, video, screen sharing, ADK, A2A, MCP,
provenance, and deployment wiring. Those are introduced in later chapters.

## Prerequisites

- Python 3.10; the recorded companion-code baseline is Python 3.10.13.
- A current desktop browser with microphone and speaker access.
- A Google AI Studio API key supplied as `GOOGLE_API_KEY` or
  `GEMINI_API_KEY`. `GOOGLE_API_KEY` takes precedence when both are set.
- Node.js only if you want to run the JavaScript syntax checks and tests. The
  recorded verification baseline is Node.js 25.9.0.

## Architecture

- `backend/server.py` serves the browser app at `http://127.0.0.1:8000`, plus
  `/health` and `/config.json`.
- `backend/proxy/proxy.py` runs the direct Gemini Live API WebSocket proxy at
  `ws://127.0.0.1:8081/live`.
- `backend/proxy/live_events.py` converts SDK messages into browser events such
  as `audio`, `input_transcript`, `output_transcript`, `interrupted`, and
  `turn_complete`.
- `frontend/app.js` manages microphone state, the WebSocket session, captions,
  and audio playback.
- `frontend/transcripts.mjs` accumulates streaming transcript fragments by
  conversational turn.

## Setup

Run these commands from the `Chapter-03` directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/proxy/requirements.txt
cp .env.example .env.local
```

Open `.env.local` and replace the placeholder value for `GOOGLE_API_KEY`. The
app loads `.env` first and `.env.local` second, so local values override shared
defaults. Do not commit either file.

## Run the App

Start the frontend server in one terminal:

```bash
.venv/bin/python backend/server.py
```

Confirm that it is serving the browser configuration:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/config.json
```

The health response should contain `"ok": true` and a `live_ws_url` pointing
to `ws://127.0.0.1:8081/live`.

Start the Live API proxy in a second terminal:

```bash
.venv/bin/python backend/proxy/proxy.py
```

Open `http://127.0.0.1:8000/`, click **Start Session**, and allow microphone
access. Speak a short request, watch both caption areas update, and interrupt
the assistant while it is speaking. A successful run captures your audio,
plays the streamed response, updates both transcripts, and stops queued audio
after an interruption.

Use `Ctrl+C` in each terminal to stop the services.

## Configuration

Defaults are documented in `.env.example`.

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Gemini API credentials. |
| `CHAPTER3_LIVE_MODEL` | Primary Gemini Live model. |
| `CHAPTER3_FALLBACK_LIVE_MODEL` | Recorded fallback model. |
| `CHAPTER3_PROXY_HOST`, `CHAPTER3_PROXY_PORT` | WebSocket proxy binding. |
| `CHAPTER3_PROXY_MAX_SIZE` | Maximum inbound browser WebSocket message size in bytes. |
| `CHAPTER3_FRONTEND_HOST`, `CHAPTER3_FRONTEND_PORT` | Static frontend binding. |
| `CHAPTER3_LIVE_WS_URL` | Browser-visible WebSocket URL returned by `/config.json`. |
| `CHAPTER3_ALLOWED_ORIGINS` | Comma-separated browser origins accepted by the proxy. |

## Verification

The deterministic checks do not call Gemini:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall backend tests
node --check frontend/app.js
node --check frontend/audio-streamer.js
node --check frontend/runtime-config.mjs
node --check frontend/transcripts.mjs
node --check frontend/audio-processor.js
node tests/runtime-config.test.mjs
node tests/transcripts.test.mjs
```

These checks cover configuration, service payloads, event shaping, browser
payload forwarding, JavaScript syntax, runtime URL validation, and transcript
accumulation. They do not prove microphone permission, speaker playback, or
real interruption behavior; perform the browser check above for those paths.

## Troubleshooting

- If the page does not load, check for a port conflict on `8000` and call
  `/health` directly.
- If the page loads but the session does not start, confirm that the proxy is
  running on `8081`, `.env.local` contains a valid key, and the browser console
  has no WebSocket or module-loading error.
- If the proxy rejects the browser, ensure the page origin appears in
  `CHAPTER3_ALLOWED_ORIGINS`.
- If captions work but audio does not, inspect browser audio permissions and
  PCM playback. If the assistant does not stop when interrupted, confirm that
  microphone audio is still reaching the proxy.
