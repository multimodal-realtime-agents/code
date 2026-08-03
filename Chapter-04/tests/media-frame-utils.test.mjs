import assert from "node:assert/strict";

import {
  DEFAULT_MAX_FRAME_BYTES,
  estimatedBase64Bytes,
  frameFitsPayloadLimit,
  scaledFrameSize,
} from "../frontend/static/media-frame-utils.mjs";
import { MediaHandler } from "../frontend/static/media-handler.js";

assert.deepEqual(scaledFrameSize(3840, 2160, 768), { width: 768, height: 432 });
assert.deepEqual(scaledFrameSize(720, 1280, 768), { width: 432, height: 768 });
assert.deepEqual(scaledFrameSize(640, 360, 768), { width: 640, height: 360 });
assert.equal(estimatedBase64Bytes("a".repeat(1200)), 900);
assert.equal(frameFitsPayloadLimit("a".repeat(Math.floor(DEFAULT_MAX_FRAME_BYTES / 0.75))), true);
assert.equal(frameFitsPayloadLimit("a".repeat(Math.ceil(DEFAULT_MAX_FRAME_BYTES / 0.75) + 20)), false);

const originalDocument = globalThis.document;
let drawCalls = [];
let encodeCalls = [];

globalThis.document = {
  createElement(tagName) {
    assert.equal(tagName, "canvas");
    const canvas = {
      width: 0,
      height: 0,
      getContext(type) {
        assert.equal(type, "2d");
        return {
          drawImage(_video, _x, _y, width, height) {
            drawCalls.push({ width, height });
          },
        };
      },
      toDataURL(_type, quality) {
        encodeCalls.push({ width: canvas.width, height: canvas.height, quality });
        const tooLarge = canvas.width >= 700 && quality > 0.6;
        const length = tooLarge ? 950000 : 320000;
        return `data:image/jpeg;base64,${"a".repeat(length)}`;
      },
    };
    return canvas;
  },
};

try {
  let frame = null;
  const handler = new MediaHandler({
    imageQuality: 0.8,
    maxFrameEdge: 768,
    maxFrameBytes: 650000,
  });
  handler.initialize({
    videoWidth: 3840,
    videoHeight: 2160,
  });
  handler.stream = {};
  handler.onFrame = (data, mimeType) => {
    frame = { dataLength: data.length, mimeType };
  };

  handler.captureFrame();

  assert.deepEqual(drawCalls[0], { width: 768, height: 432 });
  assert.equal(encodeCalls[0].quality, 0.8);
  assert.equal(encodeCalls[1].quality, 0.5);
  assert.deepEqual(frame, { dataLength: 320000, mimeType: "image/jpeg" });
} finally {
  globalThis.document = originalDocument;
}
