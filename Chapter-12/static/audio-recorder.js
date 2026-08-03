export class AudioRecorder {
  constructor({ sampleRate = 16000, onChunk } = {}) {
    this.sampleRate = sampleRate;
    this.onChunk = onChunk;
    this.audioContext = null;
    this.mediaStream = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.isMuted = false;
    this.startToken = 0;
    this.startPromise = null;
  }

  async start() {
    if (this.mediaStream) return;
    if (this.startPromise) return this.startPromise;
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Microphone capture is not available in this browser.");
    }

    const token = ++this.startToken;
    this.startPromise = this.startWithToken(token);
    try {
      await this.startPromise;
    } finally {
      this.startPromise = null;
    }
  }

  async startWithToken(token) {
    const audioContext = new AudioContext({ sampleRate: this.sampleRate });
    let workletNode = null;
    let mediaStream = null;

    try {
      await audioContext.audioWorklet.addModule("/static/audio-recorder-worklet.js");
      workletNode = new AudioWorkletNode(audioContext, "audio-recorder-worklet");
      workletNode.port.onmessage = (event) => {
        if (!this.isMuted && this.onChunk) this.onChunk(event.data);
      };

      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      if (token !== this.startToken) {
        mediaStream.getTracks().forEach((track) => track.stop());
        await closeAudioContext(audioContext);
        return;
      }

      this.audioContext = audioContext;
      this.workletNode = workletNode;
      this.mediaStream = mediaStream;
      this.sourceNode = audioContext.createMediaStreamSource(mediaStream);
      this.sourceNode.connect(workletNode);
    } catch (error) {
      mediaStream?.getTracks().forEach((track) => track.stop());
      safeDisconnect(workletNode);
      await closeAudioContext(audioContext);
      throw error;
    }
  }

  async resume() {
    if (this.audioContext?.state === "suspended") {
      await this.audioContext.resume();
    }
  }

  mute() {
    if (!this.sourceNode || !this.workletNode || this.isMuted) return;
    this.sourceNode.disconnect(this.workletNode);
    this.isMuted = true;
  }

  unmute() {
    if (!this.sourceNode || !this.workletNode || !this.isMuted) return;
    this.sourceNode.connect(this.workletNode);
    this.isMuted = false;
  }

  stop() {
    this.startToken += 1;
    safeDisconnect(this.sourceNode);
    if (this.workletNode) this.workletNode.port.onmessage = null;
    safeDisconnect(this.workletNode);
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    void closeAudioContext(this.audioContext);
    this.audioContext = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.mediaStream = null;
    this.isMuted = false;
  }
}

function safeDisconnect(node) {
  try {
    node?.disconnect();
  } catch {
    // Nodes may already be disconnected after mute or a previous cleanup pass.
  }
}

async function closeAudioContext(audioContext) {
  if (!audioContext || audioContext.state === "closed") return;
  try {
    await audioContext.close();
  } catch {
    // The browser may already be tearing the context down.
  }
}
