export class AudioStreamer {
    constructor({ sampleRate = 24000 } = {}) {
        this.sampleRate = sampleRate;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.sourceNode = null;
    }

    async ensureReady() {
        if (!this.audioContext || this.audioContext.state === "closed") {
            this.audioContext = new AudioContext({ sampleRate: this.sampleRate });
        }
        if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
        }
    }

    async receiveAudioChunk(base64Audio, mimeType = "audio/pcm;rate=24000") {
        await this.ensureReady();
        const sampleRate = sampleRateFromMimeType(mimeType) || this.sampleRate;
        const audioBuffer = pcm16Base64ToAudioBuffer(this.audioContext, base64Audio, sampleRate);
        this.audioQueue.push(audioBuffer);

        if (!this.isPlaying) {
            this.isPlaying = true;
            this.playNextChunk();
        }
    }

    playNextChunk() {
        if (this.audioQueue.length === 0 || !this.isPlaying) {
            this.isPlaying = false;
            this.sourceNode = null;
            return;
        }

        const audioChunk = this.audioQueue.shift();
        this.sourceNode = this.audioContext.createBufferSource();
        this.sourceNode.buffer = audioChunk;
        this.sourceNode.connect(this.audioContext.destination);
        this.sourceNode.onended = () => this.playNextChunk();
        this.sourceNode.start();
    }

    stop() {
        this.isPlaying = false;
        this.audioQueue = [];
        if (this.sourceNode) {
            this.sourceNode.onended = null;
            try {
                this.sourceNode.stop();
            } catch {
                // The source may already have ended after an interruption race.
            }
            this.sourceNode = null;
        }
    }
}

function pcm16Base64ToAudioBuffer(audioContext, base64Audio, sampleRate) {
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i += 1) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i += 1) {
        float32Array[i] = int16Array[i] / 32768;
    }

    const audioBuffer = audioContext.createBuffer(1, float32Array.length, sampleRate);
    audioBuffer.getChannelData(0).set(float32Array);
    return audioBuffer;
}

function sampleRateFromMimeType(mimeType) {
    const match = String(mimeType || "").match(/rate=(\d+)/);
    return match ? Number(match[1]) : null;
}
