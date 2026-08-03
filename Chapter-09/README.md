# Chapter 9: Implementing A2A-Compliant Agents

This folder contains the runnable companion code for Chapter 9. It follows
three implementation arcs:

- a cross-framework A2A handshake between a LangGraph Greeter and an ADK
  Initiator;
- an A2A wrapper around the Chapter 6 Math Agent; and
- an interoperable research workflow with a LangGraph query generator, an ADK
  researcher, and an ADK coordinator.

The examples use the pinned A2A SDK routes and client APIs directly. Shared
environment loading, configuration, and small ADK runner helpers live in
`chapter9_support/` so the chapter-named files stay focused on A2A boundaries.

## Prerequisites

- Python 3.10; the recorded companion-code baseline is Python 3.10.13.
- `curl` or another HTTP client if you want to inspect Agent Cards directly.
- Google credentials for model-backed examples: either `GOOGLE_API_KEY`, or
  Vertex AI configuration through `GOOGLE_GENAI_USE_VERTEXAI=1`,
  `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
- No Google credentials are required for deterministic smoke mode or the
  deterministic test suite.

## Services and Ports

| Example service | Default URL | Role |
|---|---|---|
| Greeter | `http://127.0.0.1:10000` | LangGraph service used by the ADK Initiator. |
| Math Agent | `http://127.0.0.1:10001` | A2A wrapper around the Chapter 6 math implementation. |
| Query Generator | `http://127.0.0.1:10002` | Produces research queries. |
| Researcher | `http://127.0.0.1:10003` | Executes the specialist research step. |

Every service exposes its Agent Card at
`/.well-known/agent-card.json`. The card advertises the callable JSON-RPC URL,
which defaults to `/a2a/jsonrpc`; clients should discover that URL rather than
constructing it themselves.

## Setup

Run these commands from the `Chapter-09` directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env.local
```

For deterministic local wiring checks, set this value in `.env.local` or on
individual commands:

```text
CH9_DETERMINISTIC_SMOKE=1
```

This mode still exercises A2A services, discovery, clients, and response
handling, but replaces model calls and ADK decisions with deterministic local
text. It does not test model or research quality.

For model-backed runs, leave `CH9_DETERMINISTIC_SMOKE=0` and configure one of
the credential paths in `.env.local`. Do not commit `.env.local`.

## Run the Handshake

Start the Greeter in terminal 1:

```bash
cd a2a_handshake/langgraph_greeter
env CH9_DETERMINISTIC_SMOKE=1 ../../.venv/bin/python server.py
```

Run the ADK Initiator in terminal 2:

```bash
cd a2a_handshake/adk_initiator
env CH9_DETERMINISTIC_SMOKE=1 ../../.venv/bin/python main.py
```

The Initiator should discover the Greeter's Agent Card, send an A2A message,
and print the remote greeting.

## Run the Math Agent Wrapper

Start the server in terminal 1:

```bash
cd a2a_math_agent
env CH9_DETERMINISTIC_SMOKE=1 ../.venv/bin/python server.py
```

Run the client in terminal 2:

```bash
cd a2a_math_agent
env CH9_DETERMINISTIC_SMOKE=1 ../.venv/bin/python client.py "What is 5 times 12?"
```

The response should report `60`. The wrapper contains the Chapter 6 math code
from the upstream source identified in `LICENSE-UPSTREAM.md`; that file also
records the applicable license notice.

## Run the Research Workflow

Start the query generator in terminal 1:

```bash
cd specialist_agents/query_generator
env CH9_DETERMINISTIC_SMOKE=1 ../../.venv/bin/python server.py
```

Start the researcher in terminal 2:

```bash
cd specialist_agents/researcher
env CH9_DETERMINISTIC_SMOKE=1 ../../.venv/bin/python server.py
```

Run the coordinator in terminal 3:

```bash
cd research_coordinator
env CH9_DETERMINISTIC_SMOKE=1 ../.venv/bin/python main.py "What is the A2A protocol?"
```

The coordinator should call the query generator, call the researcher for the
generated queries, and print a synthesized deterministic result. Remove the
`CH9_DETERMINISTIC_SMOKE=1` prefix after configuring credentials to exercise
the model-backed path.

Use `Ctrl+C` to stop each server process.

## Configuration

Defaults are documented in `.env.example`.

| Variable | Purpose |
|---|---|
| `CH9_DETERMINISTIC_SMOKE` | Enables credential-free deterministic service behavior. |
| `CH9_MODEL` | Gemini model used by ADK agents and Gemini text calls. |
| `CH9_GREETER_HOST`, `CH9_GREETER_PORT` | Greeter binding. |
| `CH9_MATH_HOST`, `CH9_MATH_PORT` | Math Agent binding. |
| `CH9_QUERY_GENERATOR_HOST`, `CH9_QUERY_GENERATOR_PORT` | Query Generator binding. |
| `CH9_RESEARCHER_HOST`, `CH9_RESEARCHER_PORT` | Researcher binding. |
| `CH9_GREETER_URL`, `CH9_MATH_URL`, `CH9_QUERY_GENERATOR_URL`, `CH9_RESEARCHER_URL` | Optional client-facing URL overrides. |

## Verification

Run the credential-free deterministic checks from the chapter directory:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q a2a_handshake a2a_math_agent a2a_client chapter9_support research_coordinator specialist_agents tests
```

For an additional service check, start any service and inspect its card, for
example:

```bash
curl -sS http://127.0.0.1:10000/.well-known/agent-card.json
```

The automated checks cover Agent Card shape, route behavior, executor status,
math tools, query parsing, A2A client response handling, source records, and
structured payload serialization. They do not establish model or research
quality.

## Troubleshooting

- If a client cannot connect, confirm the corresponding service is still
  running and inspect the URL advertised by its Agent Card.
- If a service reports missing Google credentials, enable
  `CH9_DETERMINISTIC_SMOKE=1` or complete one credential path in `.env.local`.
- If a port from `10000` through `10003` is in use, change both its host/port
  settings and any corresponding client URL override.
- If an Agent Card field or route differs after changing dependency versions,
  return to the pinned `requirements.txt` before modifying the example code.
