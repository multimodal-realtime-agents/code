export class AudioStreamer {
    constructor() {
        this.audioContext = new AudioContext({ sampleRate: 24000 });
        this.audioQueue = [];
        this.isPlaying = false;
        this.sourceNode = null; // Keep track of the current source node
    }

    playNextChunk() {
        if (this.audioQueue.length === 0 || !this.isPlaying) {
            this.isPlaying = false;
            return;
        }

        const audioChunk = this.audioQueue.shift();
        this.sourceNode = this.audioContext.createBufferSource();
        this.sourceNode.buffer = audioChunk;
        this.sourceNode.connect(this.audioContext.destination);
        this.sourceNode.onended = () => this.playNextChunk();
        this.sourceNode.start();
    }

    async receiveAudioChunk(base64Audio) {
        // Decode base64 to an ArrayBuffer
        const binaryString = atob(base64Audio);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // Convert the raw 16-bit PCM data to a Float32Array
        const int16Array = new Int16Array(bytes.buffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        // Create an AudioBuffer
        const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, 24000);
        audioBuffer.getChannelData(0).set(float32Array);

        this.audioQueue.push(audioBuffer);

        if (!this.isPlaying) {
            this.isPlaying = true;
            this.playNextChunk();
        }
    }
    
    stop() {
        this.isPlaying = false;
        this.audioQueue = []; // Clear any pending audio
        if (this.sourceNode) {
            this.sourceNode.onended = null; // Prevent the chain from continuing
            this.sourceNode.stop();
            this.sourceNode = null;
        }
    }
}