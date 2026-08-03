export const DEFAULT_MAX_FRAME_EDGE = 768;
export const DEFAULT_MAX_FRAME_BYTES = 650000;

export function scaledFrameSize(width, height, maxEdge = DEFAULT_MAX_FRAME_EDGE) {
  const sourceWidth = Number(width) || 0;
  const sourceHeight = Number(height) || 0;
  if (sourceWidth <= 0 || sourceHeight <= 0) return { width: 0, height: 0 };

  const longestEdge = Math.max(sourceWidth, sourceHeight);
  const scale = Math.min(1, maxEdge / longestEdge);
  return {
    width: Math.max(1, Math.round(sourceWidth * scale)),
    height: Math.max(1, Math.round(sourceHeight * scale)),
  };
}

export function estimatedBase64Bytes(base64Data) {
  return Math.ceil(String(base64Data || "").length * 0.75);
}

export function frameFitsPayloadLimit(base64Data, maxBytes = DEFAULT_MAX_FRAME_BYTES) {
  return estimatedBase64Bytes(base64Data) <= maxBytes;
}
