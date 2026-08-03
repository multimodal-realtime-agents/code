import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const appSource = await readFile(new URL("../frontend/static/app.js", import.meta.url), "utf8");

assert.match(appSource, /message\.type === "go_away"/);
assert.match(appSource, /Live session reconnect requested\./);
assert.match(appSource, /Connected to live proxy\./);
assert.doesNotMatch(appSource, /Connected to host\./);
