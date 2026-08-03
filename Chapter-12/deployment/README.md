# Chapter 12 Cloud Run Deployment

This packet deploys the Chapter 12 reference app as five Cloud Run services from the same container image:

- `ch12-frontend`: static mobile-friendly browser UI and `/config.json`
- `ch12-backend`: ADK Live backend and `/live` WebSocket
- `ch12-stock-a2a`: stock A2A specialist
- `ch12-weather-a2a`: weather A2A specialist
- `ch12-mcp`: shared MCP Streamable HTTP tool server

The commands below are reader-facing deployment commands. They have not been executed against a real Google Cloud project from this repository.

## Assumptions

- You are in the `Chapter-12` directory.
- `gcloud` is installed and authenticated.
- A Google Cloud project is selected.
- `GOOGLE_API_KEY` is set in your local shell before creating the Secret Manager secret.
- These commands deploy a demo with unauthenticated Cloud Run services because the browser connects directly to the frontend and backend, and this chapter code does not implement service-to-service identity tokens for A2A or MCP calls.

## Build the Image

```bash
export PROJECT_ID="$(gcloud config get-value project)"
export REGION="us-central1"
export REPOSITORY="chapter-12"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/chapter-12-agent-system:latest"

gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com

gcloud artifacts repositories create "${REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Chapter 12 companion-code images"

gcloud builds submit \
  --config deployment/cloudbuild.yaml \
  --substitutions _IMAGE="${IMAGE}" \
  .
```

If the Artifact Registry repository already exists, skip the `gcloud artifacts repositories create` command.

## Store the API Key

```bash
printf "%s" "${GOOGLE_API_KEY}" | gcloud secrets create ch12-google-api-key --data-file=-
```

If the secret already exists, add a new version instead:

```bash
printf "%s" "${GOOGLE_API_KEY}" | gcloud secrets versions add ch12-google-api-key --data-file=-
```

Cloud Run reads this secret through the service identity assigned to each service. If your project does not grant that identity access automatically, grant the default compute service account Secret Manager access:

```bash
export PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
export RUN_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding ch12-google-api-key \
  --member="serviceAccount:${RUN_SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## Deploy the MCP Tool Server

```bash
gcloud run deploy ch12-mcp \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars AGENT_SYSTEM_SERVICE=mcp

export MCP_BASE_URL="$(gcloud run services describe ch12-mcp --region="${REGION}" --format='value(status.url)')"
export MCP_URL="${MCP_BASE_URL}/mcp"
```

## Deploy the A2A Specialists

Deploy both specialists with the MCP URL, then update each public Agent Card URL after Cloud Run assigns the service URL.

```bash
gcloud run deploy ch12-stock-a2a \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --set-secrets GOOGLE_API_KEY=ch12-google-api-key:latest \
  --set-env-vars "AGENT_SYSTEM_SERVICE=stock-a2a,AGENT_SYSTEM_MCP_URL=${MCP_URL}"

export STOCK_A2A_URL="$(gcloud run services describe ch12-stock-a2a --region="${REGION}" --format='value(status.url)')"

gcloud run services update ch12-stock-a2a \
  --region="${REGION}" \
  --update-env-vars AGENT_SYSTEM_A2A_URL="${STOCK_A2A_URL}"
```

```bash
gcloud run deploy ch12-weather-a2a \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --set-secrets GOOGLE_API_KEY=ch12-google-api-key:latest \
  --set-env-vars "AGENT_SYSTEM_SERVICE=weather-a2a,AGENT_SYSTEM_MCP_URL=${MCP_URL}"

export WEATHER_A2A_URL="$(gcloud run services describe ch12-weather-a2a --region="${REGION}" --format='value(status.url)')"

gcloud run services update ch12-weather-a2a \
  --region="${REGION}" \
  --update-env-vars AGENT_SYSTEM_WEATHER_A2A_URL="${WEATHER_A2A_URL}"
```

## Deploy the Backend

Deploy the backend after the specialists exist. The frontend URL is not known yet, so set a temporary origin and update it after deploying the frontend.

```bash
gcloud run deploy ch12-backend \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --timeout=3600 \
  --set-secrets GOOGLE_API_KEY=ch12-google-api-key:latest \
  --set-env-vars "^@^AGENT_SYSTEM_SERVICE=backend@AGENT_SYSTEM_MCP_URL=${MCP_URL}@AGENT_SYSTEM_A2A_URL=${STOCK_A2A_URL}@AGENT_SYSTEM_WEATHER_A2A_URL=${WEATHER_A2A_URL}@AGENT_SYSTEM_SPECIALIST_AGENT_URLS=${STOCK_A2A_URL},${WEATHER_A2A_URL}@AGENT_SYSTEM_ALLOWED_ORIGINS=https://replace-after-frontend-deploy.invalid"

export BACKEND_URL="$(gcloud run services describe ch12-backend --region="${REGION}" --format='value(status.url)')"
export BACKEND_LIVE_WS_URL="wss://${BACKEND_URL#https://}/live"
```

## Deploy the Frontend

```bash
gcloud run deploy ch12-frontend \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars "AGENT_SYSTEM_SERVICE=frontend,AGENT_SYSTEM_LIVE_WS_URL=${BACKEND_LIVE_WS_URL}"

export FRONTEND_URL="$(gcloud run services describe ch12-frontend --region="${REGION}" --format='value(status.url)')"
```

Now restrict the backend WebSocket origin check to the assigned frontend URL:

```bash
gcloud run services update ch12-backend \
  --region="${REGION}" \
  --update-env-vars AGENT_SYSTEM_ALLOWED_ORIGINS="${FRONTEND_URL}"
```

## Environment Variable Matrix

| Service | Required environment variables | Purpose |
|---|---|---|
| `ch12-frontend` | `AGENT_SYSTEM_SERVICE=frontend`, `AGENT_SYSTEM_LIVE_WS_URL=wss://.../live` | Selects the static frontend process and returns the backend WebSocket URL from `/config.json`. |
| `ch12-backend` | `AGENT_SYSTEM_SERVICE=backend`, `GOOGLE_API_KEY`, `AGENT_SYSTEM_MCP_URL`, `AGENT_SYSTEM_A2A_URL`, `AGENT_SYSTEM_WEATHER_A2A_URL`, `AGENT_SYSTEM_SPECIALIST_AGENT_URLS`, `AGENT_SYSTEM_ALLOWED_ORIGINS` | Selects the ADK Live backend, configures model access, discovers A2A specialists, and allows the deployed frontend origin. |
| `ch12-stock-a2a` | `AGENT_SYSTEM_SERVICE=stock-a2a`, `GOOGLE_API_KEY`, `AGENT_SYSTEM_MCP_URL`, `AGENT_SYSTEM_A2A_URL` | Selects the stock specialist, configures model access, points it at the shared MCP server, and advertises its public JSON-RPC URL in the Agent Card. |
| `ch12-weather-a2a` | `AGENT_SYSTEM_SERVICE=weather-a2a`, `GOOGLE_API_KEY`, `AGENT_SYSTEM_MCP_URL`, `AGENT_SYSTEM_WEATHER_A2A_URL` | Selects the weather specialist, configures model access, points it at the shared MCP server, and advertises its public JSON-RPC URL in the Agent Card. |
| `ch12-mcp` | `AGENT_SYSTEM_SERVICE=mcp` | Selects the shared MCP Streamable HTTP tool server. |

Cloud Run injects `PORT`; the services read that port for the selected process. When `PORT` is present and no explicit host override is set, the services bind to `0.0.0.0`.

Optional model overrides:

| Variable | Default |
|---|---|
| `AGENT_SYSTEM_LIVE_MODEL` | `gemini-3.1-flash-live-preview` |
| `AGENT_SYSTEM_FALLBACK_LIVE_MODEL` | `gemini-2.5-flash-native-audio-preview-12-2025` |
| `AGENT_SYSTEM_STOCK_AGENT_MODEL` | `gemini-2.5-flash` |
| `AGENT_SYSTEM_WEATHER_AGENT_MODEL` | `gemini-2.5-flash` |

## Verify the Deployed Services

These checks verify service wiring and public configuration. They do not prove microphone, speaker, camera, screen-share, or mobile browser behavior.

```bash
curl -fsS "${MCP_BASE_URL}/health"
curl -fsS "${STOCK_A2A_URL}/health"
curl -fsS "${WEATHER_A2A_URL}/health"
curl -fsS "${BACKEND_URL}/health"
curl -fsS "${FRONTEND_URL}/health"
curl -fsS "${FRONTEND_URL}/config.json"
curl -fsS "${STOCK_A2A_URL}/.well-known/agent-card.json"
curl -fsS "${WEATHER_A2A_URL}/.well-known/agent-card.json"
```

Open `${FRONTEND_URL}` in a browser and confirm that `/config.json` returns a `wss://.../live` URL for the backend before trying live audio or media capture.

Then open the same `${FRONTEND_URL}` on a mobile phone. The page must load over HTTPS, the browser must allow microphone permission, the Camera control should start the phone camera, and the Screen control should be hidden or disabled on narrow mobile browsers. Ask the stock question by voice and confirm that the answer is spoken and shown with provenance. This phone check is the reader-facing success criterion for the deployment.

## Cleanup

```bash
gcloud run services delete ch12-frontend --region="${REGION}"
gcloud run services delete ch12-backend --region="${REGION}"
gcloud run services delete ch12-stock-a2a --region="${REGION}"
gcloud run services delete ch12-weather-a2a --region="${REGION}"
gcloud run services delete ch12-mcp --region="${REGION}"
```
