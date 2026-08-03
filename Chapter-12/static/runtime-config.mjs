export async function loadRuntimeConfig(fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") {
    throw new Error("Live backend configuration cannot be loaded because fetch is unavailable.");
  }

  let response;
  try {
    response = await fetchImpl("/config.json", { cache: "no-store" });
  } catch (error) {
    throw new Error(`Live backend configuration request failed: ${error.message}`);
  }

  if (!response.ok) {
    throw new Error(`Live backend configuration request failed with HTTP ${response.status}.`);
  }

  return validateRuntimeConfig(await response.json());
}

export function validateRuntimeConfig(config) {
  const liveWsUrl = String(config?.live_ws_url || "").trim();
  if (!liveWsUrl) {
    throw new Error("Live backend configuration is missing live_ws_url.");
  }

  const url = parseLiveWebSocketUrl(liveWsUrl);
  return { live_ws_url: url.toString() };
}

export function buildLiveWebSocketUrl(liveWsUrl, sessionId) {
  const url = parseLiveWebSocketUrl(liveWsUrl);
  const cleanSessionId = String(sessionId || "").trim();
  if (!cleanSessionId) {
    throw new Error("Cannot open the live WebSocket without a session_id.");
  }
  url.searchParams.set("session_id", cleanSessionId);
  return url.toString();
}

function parseLiveWebSocketUrl(liveWsUrl) {
  let url;
  try {
    url = new URL(liveWsUrl);
  } catch {
    throw new Error("Live backend configuration must provide an absolute ws:// or wss:// live_ws_url.");
  }

  if (url.protocol !== "ws:" && url.protocol !== "wss:") {
    throw new Error("Live backend configuration must use a ws:// or wss:// live_ws_url.");
  }
  return url;
}
