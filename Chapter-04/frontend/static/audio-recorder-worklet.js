class AudioRecordingWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Int16Array(2048);
    this.bufferIndex = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, channel[i]));
      this.buffer[this.bufferIndex] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      this.bufferIndex += 1;

      if (this.bufferIndex >= this.buffer.length) {
        this.flush();
      }
    }

    return true;
  }

  flush() {
    if (this.bufferIndex === 0) return;
    const chunk = this.buffer.slice(0, this.bufferIndex).buffer;
    this.port.postMessage(chunk, [chunk]);
    this.bufferIndex = 0;
  }
}

registerProcessor("audio-recorder-worklet", AudioRecordingWorklet);
