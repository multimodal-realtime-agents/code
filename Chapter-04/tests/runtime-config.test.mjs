import assert from "node:assert/strict";

import {
  buildLiveWebSocketUrl,
  loadRuntimeConfig,
  validateRuntimeConfig,
} from "../frontend/static/runtime-config.mjs";

assert.deepEqual(
  validateRuntimeConfig({ live_ws_url: "ws://127.0.0.1:8081/live" }),
  { live_ws_url: "ws://127.0.0.1:8081/live" },
);

assert.equal(
  buildLiveWebSocketUrl("ws://127.0.0.1:8081/live", "session-123"),
  "ws://127.0.0.1:8081/live?session_id=session-123",
);

assert.equal(
  buildLiveWebSocketUrl("wss://backend.example/live?trace=1", "session 123"),
  "wss://backend.example/live?trace=1&session_id=session+123",
);

assert.throws(
  () => validateRuntimeConfig({ live_ws_url: "https://backend.example/live" }),
  /ws:\/\/ or wss:\/\//,
);

const config = await loadRuntimeConfig(async (path, options) => {
  assert.equal(path, "/config.json");
  assert.equal(options.cache, "no-store");
  return {
    ok: true,
    async json() {
      return { live_ws_url: "ws://127.0.0.1:8081/live" };
    },
  };
});
assert.equal(config.live_ws_url, "ws://127.0.0.1:8081/live");
