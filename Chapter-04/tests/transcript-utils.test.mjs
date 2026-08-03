import assert from "node:assert/strict";

import { mergeTranscript } from "../frontend/static/transcript-utils.mjs";

const chunks = [
  "As of",
  " May",
  " 27,",
  " 2026,",
  " at",
  " 4",
  " 35",
  " PM",
  " UTC,",
  " the price",
  " of Nvidia",
  " stock",
  " is 209",
  " 84",
  " USD.",
];

const mergedChunks = chunks.reduce(
  (current, text) => mergeTranscript(current, { text, partial: false }),
  "",
);
assert.equal(
  mergedChunks,
  "As of May 27, 2026, at 4 35 PM UTC, the price of Nvidia stock is 209 84 USD.",
);

assert.equal(
  mergeTranscript("Hello", { text: "Hello world.", partial: true }),
  "Hello world.",
);

assert.equal(
  mergeTranscript("Hello wor", { text: "world!", partial: false }),
  "Hello world!",
);

assert.equal(
  mergeTranscript("What can I help you with", { text: "?", partial: false }),
  "What can I help you with?",
);

assert.equal(
  mergeTranscript("Already complete.", { text: "complete.", partial: false }),
  "Already complete.",
);
