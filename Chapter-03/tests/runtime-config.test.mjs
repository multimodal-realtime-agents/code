import assert from "node:assert/strict";
import {
  buildLiveWebSocketUrl,
  validateRuntimeConfig,
} from "../frontend/runtime-config.mjs";

const config = validateRuntimeConfig({ live_ws_url: "ws://127.0.0.1:8081/live" });
assert.equal(config.live_ws_url, "ws://127.0.0.1:8081/live");

const url = buildLiveWebSocketUrl(config.live_ws_url, "session-123");
assert.equal(url, "ws://127.0.0.1:8081/live?session_id=session-123");

assert.throws(
  () => validateRuntimeConfig({ live_ws_url: "http://127.0.0.1:8081/live" }),
  /ws:\/\/ or wss:\/\//,
);

assert.throws(
  () => validateRuntimeConfig({}),
  /missing live_ws_url/,
);
