import { AudioStreamer } from './audio-streamer.js';

// --- DOM Elements ---
const statusElement = document.getElementById('status');
const micButton = document.getElementById('micButton');

// --- State Management ---
let isSessionActive = false;
let isMicMuted = false;

// --- Core Classes ---
const streamer = new AudioStreamer();

// --- WebSocket Setup ---
const PROXY_URL = 'ws://localhost:8081';
console.log('Attempting to connect to WebSocket proxy...');
const ws = new WebSocket(PROXY_URL);

ws.onopen = () => {
    console.log('Connected to WebSocket proxy.');
    statusElement.textContent = 'Ready. Click to start session.';
    micButton.disabled = false;
};

ws.onmessage = async (event) => {
    console.log('DEBUG: Raw message received:', event.data);
    
    try {
        const response = JSON.parse(event.data);
        console.log('DEBUG: Parsed message:', response);
        
        if (response.type == "interrupted") {
            console.log('AI was interrupted. Stopping playback.');
            streamer.stop();
            statusElement.textContent = 'I was interrupted. Listening...';
            return;
        }

        // Check for audio data in the correct location
        if (response.type == "audio") {
            console.log('DEBUG: Found audio data in response');
            statusElement.textContent = 'Gemini is speaking...';
            const audioData = response.data;
            console.log('DEBUG: Audio data length:', audioData.length);
            await streamer.receiveAudioChunk(audioData);
            return;
        }

        if (response.type == "backend" && response.data =="turn_complete") {
            console.log('DEBUG: Turn complete received');
            statusElement.textContent = 'Listening...';
            return;
        }
        
        if (response.type == "backend" && response.data == "backend_ready") {
            console.log('DEBUG: Setup complete received');
            return;
        }
        
    } catch (error) {
        console.error('DEBUG: Failed to parse message as JSON:', error);
        console.error('DEBUG: Raw message was:', event.data);
        console.error('DEBUG: Message type:', typeof event.data);
        console.error('DEBUG: Message length:', event.data.length);
        console.error('DEBUG: First 100 chars:', event.data.substring(0, 100));
    }
};

ws.onerror = (error) => {
    console.error('WebSocket Error:', error);
    statusElement.textContent = 'Error connecting. Please check the proxy server.';
};

ws.onclose = (event) => {
    console.log('WebSocket connection closed.', event.reason);
    statusElement.textContent = 'Connection closed. Please refresh.';
    micButton.disabled = true;
    if (isSessionActive) {
        recorder.stop();
        isSessionActive = false;
    }
};

// --- Audio Recorder Class ---
class AudioRecorder {
    constructor() {
        this.audioContext = null;
        this.source = null;
        this.workletNode = null;
        this.stream = null;
        this.isMuted = false;
    }

    async start() {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioContext = new AudioContext({ sampleRate: 16000 });
        await this.audioContext.audioWorklet.addModule('audio-processor.js');
        this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-processor');
        
        this.workletNode.port.onmessage = (event) => {
            // Convert ArrayBuffer to Base64 string
            const base64String = btoa(String.fromCharCode(...new Uint8Array(event.data)));
            
            // Format for Gemini Live API according to the official docs
            const message = { 
                realtimeInput: { 
                    mediaChunks: [{ 
                        mime_type: "audio/pcm", 
                        data: base64String 
                    }] 
                } 
            };
            
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(message));
            }
        };
        
        this.source = this.audioContext.createMediaStreamSource(this.stream);
        this.source.connect(this.workletNode);
    }

    stop() {
        this.stream?.getTracks().forEach(track => track.stop());
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
    }

    mute() {
        if (this.source && this.workletNode && !this.isMuted) {
            this.source.disconnect(this.workletNode);
            this.isMuted = true;
        }
    }

    unmute() {
        if (this.source && this.workletNode && this.isMuted) {
            this.source.connect(this.workletNode);
            this.isMuted = false;
        }
    }
}

const recorder = new AudioRecorder();

// --- UI Event Listener ---
micButton.addEventListener('click', async () => {
    if (ws.readyState !== WebSocket.OPEN) {
        statusElement.textContent = 'WebSocket not connected. Please wait or refresh.';
        return;
    }

    if (!isSessionActive) {
        // First click: start the session
        statusElement.textContent = 'Starting microphone...';
        try {
            await recorder.start();

            isSessionActive = true;
            isMicMuted = false;
            micButton.textContent = 'Mute Mic';
            micButton.classList.add('hot');
            statusElement.textContent = 'Listening...';

        } catch (error) {
            console.error("Error starting microphone:", error);
            statusElement.textContent = "Could not start microphone.";
        }
        
    } else {
        // Subsequent clicks: toggle mute
        if (isMicMuted) {
            recorder.unmute();
            micButton.textContent = 'Mute Mic';
            micButton.classList.add('hot');
            statusElement.textContent = 'Listening...';
        } else {
            recorder.mute();
            micButton.textContent = 'Unmute Mic';
            micButton.classList.remove('hot');
            statusElement.textContent = 'Mic muted.';
        }
        isMicMuted = !isMicMuted;
    }
});