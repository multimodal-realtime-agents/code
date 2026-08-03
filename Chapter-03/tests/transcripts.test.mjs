import assert from "node:assert/strict";
import { TranscriptTurns, mergeTranscriptFragment } from "../frontend/transcripts.mjs";

assert.equal(
  mergeTranscriptFragment("How can I", { text: " help?", partial: true }),
  "How can I help?",
);

assert.equal(
  mergeTranscriptFragment("How can", { text: "How can I help?", partial: true }),
  "How can I help?",
);

assert.equal(
  mergeTranscriptFragment("stale", { text: "fresh final", partial: false }),
  "fresh final",
);

const turns = new TranscriptTurns();
assert.equal(turns.appendOutput({ text: "How can I", partial: true }), "How can I");
assert.equal(turns.appendOutput({ text: " help", partial: true }), "How can I help");
assert.equal(turns.appendOutput({ text: " you?", partial: true }), "How can I help you?");

turns.completeOutputTurn();
assert.equal(turns.appendOutput({ text: "Next", partial: true }), "Next");

assert.equal(turns.appendInput({ text: "Hello", partial: true }), "Hello");
turns.completeInputTurn();
assert.equal(turns.appendInput({ text: "New turn", partial: true }), "New turn");
