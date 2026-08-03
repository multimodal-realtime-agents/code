import {
  DEFAULT_MAX_FRAME_BYTES,
  DEFAULT_MAX_FRAME_EDGE,
  frameFitsPayloadLimit,
  scaledFrameSize,
} from "./media-frame-utils.mjs";

export class MediaHandler {
  constructor({
    frameIntervalMs = 1000,
    imageType = "image/jpeg",
    imageQuality = 0.65,
    maxFrameEdge = DEFAULT_MAX_FRAME_EDGE,
    maxFrameBytes = DEFAULT_MAX_FRAME_BYTES,
    onStop,
  } = {}) {
    this.frameIntervalMs = frameIntervalMs;
    this.imageType = imageType;
    this.imageQuality = imageQuality;
    this.maxFrameEdge = maxFrameEdge;
    this.maxFrameBytes = maxFrameBytes;
    this.onStop = onStop;
    this.videoElement = null;
    this.stream = null;
    this.frameTimer = null;
    this.onFrame = null;
    this.mode = "idle";
  }

  initialize(videoElement) {
    this.videoElement = videoElement;
  }

  get isActive() {
    return this.mode !== "idle";
  }

  get isWebcamActive() {
    return this.mode === "webcam";
  }

  get isScreenActive() {
    return this.mode === "screen";
  }

  async startWebcam() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Camera capture is not available in this browser.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });
    this.setStream(stream, "webcam");
  }

  async startScreenShare() {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      throw new Error("Screen sharing is not available in this browser.");
    }

    const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
    stream.getVideoTracks()[0]?.addEventListener("ended", () => this.stopAll());
    this.setStream(stream, "screen");
  }

  startFrameCapture(onFrame) {
    this.stopFrameCapture();
    this.onFrame = onFrame;
    this.frameTimer = setInterval(() => this.captureFrame(), this.frameIntervalMs);
    this.captureFrame();
  }

  stopFrameCapture() {
    if (this.frameTimer) clearInterval(this.frameTimer);
    this.frameTimer = null;
  }

  stopAll({ notify = true } = {}) {
    const wasActive = this.isActive;
    this.stopFrameCapture();
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.mode = "idle";

    if (this.videoElement) {
      this.videoElement.srcObject = null;
      this.videoElement.classList.add("hidden");
    }

    if (notify && wasActive && this.onStop) this.onStop();
  }

  setStream(stream, mode) {
    this.stopAll({ notify: false });
    this.stream = stream;
    this.mode = mode;

    if (this.videoElement) {
      this.videoElement.srcObject = stream;
      this.videoElement.classList.remove("hidden");
    }
  }

  captureFrame() {
    if (!this.stream || !this.videoElement || !this.onFrame) return;
    if (!this.videoElement.videoWidth || !this.videoElement.videoHeight) return;

    const frameEdges = uniqueNumbers([
      this.maxFrameEdge,
      Math.round(this.maxFrameEdge * 0.75),
      512,
      384,
    ]).filter((edge) => edge > 0);
    const qualities = uniqueNumbers([
      this.imageQuality,
      0.5,
      0.35,
    ]).filter((quality) => quality > 0 && quality <= 1);

    for (const maxEdge of frameEdges) {
      const canvas = document.createElement("canvas");
      const size = scaledFrameSize(
        this.videoElement.videoWidth,
        this.videoElement.videoHeight,
        maxEdge,
      );
      if (!size.width || !size.height) return;
      canvas.width = size.width;
      canvas.height = size.height;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);

      for (const quality of qualities) {
        const dataUrl = canvas.toDataURL(this.imageType, quality);
        const [, data] = dataUrl.split(",", 2);
        if (data && frameFitsPayloadLimit(data, this.maxFrameBytes)) {
          this.onFrame(data, this.imageType);
          return;
        }
      }
    }
  }
}

function uniqueNumbers(values) {
  return [...new Set(values.map((value) => Number(value)).filter(Number.isFinite))];
}
