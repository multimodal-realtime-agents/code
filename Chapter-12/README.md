# Chapter 12: Integrated Live Multi-Agent System

This folder contains the runnable Chapter 12 reference system. It combines the
book's live browser interaction, ADK host, A2A specialists, and MCP tools in one
five-service example, while preserving the boundaries between them.

The local app supports voice, text, camera frames, stock and weather requests,
structured provenance, and a responsive browser interface. The deployment
packet runs the same source tree as five Cloud Run services selected through
`AGENT_SYSTEM_SERVICE`.

## Prerequisites

- Python 3.10; the recorded companion-code baseline is Python 3.10.13 and the
  supplied `Dockerfile` uses Python 3.10.
- A current browser with microphone, speaker, and camera access. Screen sharing
  depends on browser and operating-system support.
- A Google AI Studio API key supplied as `GOOGLE_API_KEY` for model-backed live
  and specialist paths.
- Node.js only if you want to run the JavaScript syntax checks and tests. The
  recorded verification baseline is Node.js 25.9.0.
- For the optional deployment path: an authenticated Google Cloud CLI, a
  selected project, and permission to use Cloud Run, Cloud Build, Artifact
  Registry, and Secret Manager.

## Local Architecture

| Service | Default URL | Responsibility |
|---|---|---|
| Frontend | `http://127.0.0.1:8080` | Serves the browser UI, `/health`, and `/config.json`. |
| Backend | `http://127.0.0.1:8000` | Runs the ADK Live host and `/live` WebSocket. |
| MCP server | `http://127.0.0.1:8010/mcp` | Provides stock-price and weather tools over MCP Streamable HTTP. |
| Stock specialist | `http://127.0.0.1:8020` | A2A stock agent that calls the MCP server. |
| Weather specialist | `http://127.0.0.1:8030` | A2A weather agent that calls the MCP server. |

The specialists expose Agent Cards at
`/.well-known/agent-card.json`. Their cards advertise the callable A2A
JSON-RPC endpoints; clients should discover those URLs rather than construct
them.

## Setup

Run these commands from the `Chapter-12` directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env.local
```

Open `.env.local`, replace the placeholder `GOOGLE_API_KEY`, and keep the local
service URLs unchanged for the first run. The code loads `.env` first and
`.env.local` second, so local values override shared defaults. Do not commit
either file.

The deterministic tests below do not call the model, but the backend and
model-backed specialists require the key for a complete browser run.

## Run the Five Local Services

Start each process from the `Chapter-12` directory in its own terminal. Start
the MCP server first, followed by the specialists, backend, and frontend.

Terminal 1 — MCP tool server:

```bash
.venv/bin/python -m agent_system.mcp_tool_server
```

Terminal 2 — stock A2A specialist:

```bash
.venv/bin/python -m agent_system.stock_a2a_agent
```

Terminal 3 — weather A2A specialist:

```bash
.venv/bin/python -m agent_system.weather_a2a_agent
```

Terminal 4 — ADK Live backend:

```bash
.venv/bin/python -m agent_system.backend
```

Terminal 5 — browser frontend:

```bash
.venv/bin/python -m agent_system.frontend
```

Check the main service boundaries before opening the browser:

```bash
curl -sS http://127.0.0.1:8010/health
curl -sS http://127.0.0.1:8020/.well-known/agent-card.json
curl -sS http://127.0.0.1:8030/.well-known/agent-card.json
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8080/health
curl -sS http://127.0.0.1:8080/config.json
```

The frontend configuration should contain
`ws://127.0.0.1:8000/live`. The backend health response should identify both
specialist URLs and the MCP URL.

Open `http://127.0.0.1:8080/`, start a session, and ask:

> What is the latest price for NVDA, and give me a one-sentence market context?

A successful run returns a concise spoken or displayed response and shows
structured provenance for a provider, fallback, mock, or unavailable result.
The browser activity surface is useful for teaching and diagnosis, but it is
not a distributed trace; inspect service logs when you need proof of the A2A
and MCP calls.

Use `Ctrl+C` in each terminal to stop the services.

## Configuration

The full local defaults are documented in `.env.example`. The main settings
are:

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` | Gemini credential for live and specialist model calls. |
| `AGENT_SYSTEM_LIVE_MODEL`, `AGENT_SYSTEM_FALLBACK_LIVE_MODEL` | Primary and fallback Live models. |
| `AGENT_SYSTEM_STOCK_AGENT_MODEL`, `AGENT_SYSTEM_WEATHER_AGENT_MODEL` | Specialist text models. |
| `AGENT_SYSTEM_MCP_URL` | MCP Streamable HTTP endpoint. |
| `AGENT_SYSTEM_A2A_URL`, `AGENT_SYSTEM_WEATHER_A2A_URL` | Stock and weather specialist base URLs. |
| `AGENT_SYSTEM_SPECIALIST_AGENT_URLS` | Comma-separated specialist discovery list used by the host. |
| `AGENT_SYSTEM_LIVE_WS_URL` | Browser-visible backend WebSocket URL. |
| `AGENT_SYSTEM_ALLOWED_ORIGINS` | Browser origins allowed to open the backend WebSocket. |
| `AGENT_SYSTEM_SERVICE` | Selects one process when using `agent_system.service_entrypoint`. |

Each service also supports the host and port overrides shown in
`.env.example`. When Cloud Run supplies `PORT`, the selected service uses that
port and binds to `0.0.0.0` unless an explicit host override is present.

## Verification

Run the deterministic checks from the chapter directory:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall -q agent_system tests
node --check static/app.js
node --check static/audio-recorder.js
node --check static/audio-streamer.js
node --check static/media-handler.js
node --check static/runtime-config.mjs
node tests/runtime-config.test.mjs
```

These checks cover configuration, browser/backend contracts, routing helpers,
specialist discovery, Agent Cards, A2A adapters, MCP tool behavior, deterministic
fallbacks, and frontend runtime configuration. They do not prove a model-backed
Live session, real browser media, or a deployed Cloud Run system; use the local
browser run above and the deployment verification steps for those paths.

## Deploy to Cloud Run

See [`deployment/README.md`](deployment/README.md) for the image build, Secret
Manager setup, five service deployments, environment-variable matrix, public
endpoint checks, and phone test.

The deployment commands intentionally create unauthenticated demonstration
services so a browser can reach the frontend and Live backend. They do not add
service-to-service identity tokens for A2A or MCP calls. The deployment packet
has not been executed against a real Google Cloud project from this repository;
review the security and cost implications before running it.

## Troubleshooting

- If a specialist does not start, confirm that the MCP service is running at
  `AGENT_SYSTEM_MCP_URL` and that ports `8010` through `8030` are free.
- If the browser loads but does not connect, check `/config.json`, confirm the
  backend is running on `8000`, and ensure the frontend origin appears in
  `AGENT_SYSTEM_ALLOWED_ORIGINS`.
- If the backend reports missing credentials, set `GOOGLE_API_KEY` in
  `.env.local` and restart the backend and specialists.
- If an Agent Card or JSON-RPC route differs after changing dependencies,
  return to the pinned `requirements.txt` before changing the example code.
- Camera and microphone checks require browser permission. Deployed media also
  requires HTTPS and a `wss://` backend URL; plain `ws://` is local-only.
