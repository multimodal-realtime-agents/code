# Chapter 4: Advanced Live Interactions

This folder contains the runnable Chapter 4 companion app. It extends the
Chapter 3 browser-and-proxy loop with system instructions, voice selection,
live camera and screen frames, local function-calling tools, structured
provenance, and a responsive browser interface.

The backend talks directly to Gemini Live and owns the tools. It does not use
ADK, A2A, or MCP; Chapter 12 rebuilds a similar experience with those
boundaries made explicit.

## Prerequisites

- Python 3.10; the recorded companion-code baseline is Python 3.10.13.
- A current desktop browser with microphone, speaker, and camera access. Screen
  sharing depends on browser and operating-system support.
- A Google AI Studio API key supplied as `GOOGLE_API_KEY` or
  `GEMINI_API_KEY`. `GOOGLE_API_KEY` takes precedence when both are set.
- Node.js only if you want to run the JavaScript syntax checks and tests. The
  recorded verification baseline is Node.js 25.9.0.

## Architecture

- `backend/server.py` serves the app at `http://127.0.0.1:8000`, plus
  `/health` and `/config.json`.
- `backend/proxy/proxy.py` runs the Gemini Live WebSocket proxy at
  `ws://127.0.0.1:8081/live`, applies the session instructions and voice, and
  forwards audio, text, and image messages.
- `backend/proxy/tool_handler.py` declares and executes the stock and weather
  tools. Stock results may come from Stooq or an explicit fallback;
  weather results are deterministic demonstration data.
- `backend/proxy/live_events.py` converts model and tool responses into the
  browser-facing audio, transcript, function, provenance, and turn events.
- `frontend/static/` contains the responsive UI, audio pipeline, media capture,
  runtime configuration, styles, and transcript helpers.

## Setup

Run these commands from the `Chapter-04` directory:

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

Check the reader-facing endpoints:

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

Open `http://127.0.0.1:8000/` and try the chapter paths:

1. Start a session and allow microphone access.
2. Ask, “What can you help me with?” to check the configured voice and concise
   response style.
3. Click **Camera**, show a nearby object, and ask what the assistant sees.
4. Ask, “What is the current price of Nvidia stock?” and confirm that the UI
   shows a structured provenance result.
5. Ask for the weather in London and confirm that the response identifies the
   result as demonstration data.

The Screen control sends screen-share frames on supported desktop browsers.
Mobile layouts may hide or disable that control. Use `Ctrl+C` in both terminals
to stop the services.

## Configuration

Defaults are documented in `.env.example`.

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Gemini API credentials. |
| `CHAPTER4_LIVE_MODEL` | Primary Gemini Live model. |
| `CHAPTER4_FALLBACK_LIVE_MODEL` | Recorded fallback model. |
| `CHAPTER4_PROXY_HOST`, `CHAPTER4_PROXY_PORT` | WebSocket proxy binding. |
| `CHAPTER4_PROXY_MAX_SIZE` | Maximum inbound browser WebSocket message size; the default is 8 MiB. |
| `CHAPTER4_FRONTEND_HOST`, `CHAPTER4_FRONTEND_PORT` | Static frontend binding. |
| `CHAPTER4_LIVE_WS_URL` | Browser-visible WebSocket URL returned by `/config.json`. |
| `CHAPTER4_ALLOWED_ORIGINS` | Comma-separated browser origins accepted by the proxy. |

## Verification

The deterministic checks do not call Gemini or external stock services:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall backend tests
node --check frontend/static/app.js
node --check frontend/static/audio-recorder.js
node --check frontend/static/audio-streamer.js
node --check frontend/static/media-handler.js
node --check frontend/static/media-frame-utils.mjs
node --check frontend/static/runtime-config.mjs
node --check frontend/static/transcript-utils.mjs
node --check frontend/static/audio-recorder-worklet.js
node tests/frontend-message-contract.test.mjs
node tests/media-frame-utils.test.mjs
node tests/runtime-config.test.mjs
node tests/transcript-utils.test.mjs
```

These checks cover Live configuration, browser payload forwarding, multi-turn
receive behavior, tool-response handoff, provenance contracts, frontend
service payloads, transcript accumulation, and media-frame size limits. They
do not prove real microphone, camera, screen-share, speaker, or model behavior;
perform the browser checks above for those paths.

## Troubleshooting

- If the page does not load, check for a port conflict on `8000` and call
  `/health` directly.
- If the page loads but cannot connect, confirm that the proxy is running on
  `8081`, the API key is valid, and the page origin appears in
  `CHAPTER4_ALLOWED_ORIGINS`.
- If camera or microphone controls fail, review browser permissions and test on
  `localhost` or `127.0.0.1`, which browsers treat as secure local origins.
- If screen sharing closes the WebSocket with code `1009`, confirm that the
  current media-scaling code is loaded and that `CHAPTER4_PROXY_MAX_SIZE` has
  not been reduced below the frame payload size.
- Stock lookup can fall back when its upstream source is unavailable. Treat
  `status`, `source`, and `warning` in the displayed provenance as part of the
  result rather than hiding them.
