export class AudioStreamer {
  constructor() {
    this.audioContext = null;
    this.gainNode = null;
    this.queue = [];
    this.currentSource = null;
    this.isPlaying = false;
  }

  async ensureReady() {
    if (!this.audioContext) {
      this.audioContext = new AudioContext();
      this.gainNode = this.audioContext.createGain();
      this.gainNode.connect(this.audioContext.destination);
    }
    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }
  }

  async addPcm16(base64, mimeType = "audio/pcm;rate=24000") {
    await this.ensureReady();
    const sampleRate = sampleRateFromMimeType(mimeType);
    const bytes = base64ToUint8Array(base64);
    const samples = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.byteLength / 2));
    const buffer = this.audioContext.createBuffer(1, samples.length, sampleRate);
    const channel = buffer.getChannelData(0);

    for (let i = 0; i < samples.length; i += 1) {
      channel[i] = samples[i] / 0x8000;
    }

    this.queue.push(buffer);
    if (!this.isPlaying) this.playNext();
  }

  playNext() {
    if (!this.audioContext || !this.gainNode || this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    const source = this.audioContext.createBufferSource();
    source.buffer = this.queue.shift();
    source.connect(this.gainNode);
    source.onended = () => {
      if (this.currentSource === source) this.currentSource = null;
      this.playNext();
    };

    this.currentSource = source;
    this.isPlaying = true;
    source.start();
  }

  stop() {
    this.queue = [];
    this.isPlaying = false;
    if (this.currentSource) {
      this.currentSource.onended = null;
      try {
        this.currentSource.stop();
      } catch {
        // The source may already have ended.
      }
      this.currentSource.disconnect();
      this.currentSource = null;
    }
  }
}

function sampleRateFromMimeType(mimeType) {
  const match = /rate=(\d+)/.exec(mimeType);
  return match ? Number(match[1]) : 24000;
}

function base64ToUint8Array(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
