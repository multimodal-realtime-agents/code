export class MediaHandler {
  constructor({
    frameIntervalMs = 1000,
    imageType = "image/jpeg",
    imageQuality = 0.8,
    onStop,
  } = {}) {
    this.frameIntervalMs = frameIntervalMs;
    this.imageType = imageType;
    this.imageQuality = imageQuality;
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

    const canvas = document.createElement("canvas");
    canvas.width = this.videoElement.videoWidth;
    canvas.height = this.videoElement.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return;

    context.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL(this.imageType, this.imageQuality);
    const [, data] = dataUrl.split(",", 2);
    if (data) this.onFrame(data, this.imageType);
  }
}
