# Chapter 11: Implementing MCP-Enabled Agents and Tool Servers

This folder contains the runnable Chapter 11 financial analyst example as a
small MCP system:

- `stock_server.py` is a standalone FastMCP stdio server with deterministic
  sample quote, company metadata, and chart tools.
- `analyst_agent.py` is an ADK agent that discovers those capabilities through
  `McpToolset` and launches the server as a child process over stdio.
- `config.py` loads the model configuration and checks the credential path for
  model-backed analyst runs.

The stock values are sample data, not live market data or investment advice.
No market-data credential is required. The analyst agent does require Gemini or
Vertex AI credentials because it calls a model.

## Prerequisites

- Python 3.10; the recorded companion-code baseline is Python 3.10.13.
- Google credentials for `analyst_agent.py`: `GOOGLE_API_KEY`,
  `GEMINI_API_KEY`, or Vertex AI configuration through
  `GOOGLE_GENAI_USE_VERTEXAI=1`, `GOOGLE_CLOUD_PROJECT`, and
  `GOOGLE_CLOUD_LOCATION`.
- Node.js and `npx` only for the optional MCP Inspector workflow.

## Setup

Run these commands from the `Chapter-11` directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env.local
```

Deterministic tests and direct server inspection do not require credentials.
Before running the analyst, complete one supported credential path in
`.env.local`. Do not commit that file.

The default analyst model is `gemini-3.5-flash`. Change `CH11_MODEL` only when
you have verified another model identifier for your environment.

## Run the MCP Server Directly

The MCP server communicates over standard input and output, so it starts and
then waits silently for JSON-RPC messages:

```bash
.venv/bin/python stock_server.py
```

This confirms that the process starts, but a silent terminal is not a complete
protocol check. Press `Ctrl+C` to stop the direct process, then use the tests or
MCP Inspector below to exercise its tools and resource.

## Run the Analyst Agent

Ask for a sample quote:

```bash
.venv/bin/python analyst_agent.py "What is the current price of Apple?"
```

Ask for chart data:

```bash
.venv/bin/python analyst_agent.py "Show me the chart for NVIDIA."
```

The analyst should discover the MCP tools, select an appropriate tool, launch
the server with the same `.venv/bin/python` interpreter, and print a final
model response based on the deterministic sample data.

## Debug with MCP Inspector

If Node.js and `npx` are installed, inspect the server without ADK or a model:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python stock_server.py
```

Use the Inspector to list and call `get_stock_price`, `get_stock_chart`, and
the `stock://{ticker}/info` resource. This is an optional interactive
diagnostic, not a substitute for the automated protocol tests.

## Configuration

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Gemini API credential for the analyst. |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `1` to use Vertex AI credentials. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Vertex AI project and region. |
| `CH11_MODEL` | Model used by `analyst_agent.py`; defaults to `gemini-3.5-flash`. |

## Verification

Run the credential-free checks from the chapter directory:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q stock_server.py analyst_agent.py config.py tests
```

These checks cover the deterministic stock functions, MCP protocol discovery
and calls, resource reads, analyst configuration, and child-process setup.
They do not prove that the configured model is available or that a
model-selected tool call will succeed; run `analyst_agent.py` afterward for
that path.

## Troubleshooting

- If `stock_server.py` appears idle, remember that stdio servers wait for a
  client; use the tests or Inspector rather than typing into its terminal.
- If the analyst reports missing credentials, complete one credential path in
  `.env.local` and start a new process so the environment is reloaded.
- If the child process cannot import `mcp`, run the analyst with
  `.venv/bin/python` rather than a different Python interpreter.
- If the Inspector fails to launch, confirm that Node.js and `npx` are
  available. The Python test suite remains the required deterministic check.
