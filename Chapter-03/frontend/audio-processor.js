class AudioProcessor extends AudioWorkletProcessor {
    // A buffer to hold audio samples before we send them (2048 samples = 128ms at 16kHz)
    buffer = new Int16Array(2048);
    bufferIndex = 0;
  
    process(inputs) {
      const channelData = inputs[0][0];
      if (!channelData) return true;
  
      for (let i = 0; i < channelData.length; i++) {
        // Convert from Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
        this.buffer[this.bufferIndex++] = channelData[i] * 0x7FFF;
  
        // If the buffer is full, send it to the main thread.
        if (this.bufferIndex === this.buffer.length) {
          // Post a copy of the buffer's ArrayBuffer
          this.port.postMessage(this.buffer.buffer.slice(0));
          this.bufferIndex = 0; // Reset for the next chunk
        }
      }
      return true; // Indicate that we want to keep processing
    }
  }
  
  registerProcessor('audio-processor', AudioProcessor);