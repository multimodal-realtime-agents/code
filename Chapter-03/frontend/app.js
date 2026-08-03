import { AudioStreamer } from "./audio-streamer.js";
import { buildLiveWebSocketUrl, loadRuntimeConfig } from "./runtime-config.mjs";
import { TranscriptTurns } from "./transcripts.mjs";

const statusElement = document.querySelector("#status");
const micButton = document.querySelector("#micButton");
const userCaption = document.querySelector("#userCaption");
const assistantCaption = document.querySelector("#assistantCaption");

let socket = null;
let connectPromise = null;
let runtimeConfigPromise = null;
let isSessionActive = false;
let isMicMuted = false;
let recorder = null;

const streamer = new AudioStreamer();
const transcripts = new TranscriptTurns();

micButton.addEventListener("click", () => {
    if (!isSessionActive) {
        void startSession();
    } else {
        void toggleMute();
    }
});

window.addEventListener("beforeunload", () => {
    closeSocket();
    recorder.stop();
    streamer.stop();
});

setStatus("Ready. Start a voice session.");
micButton.disabled = false;

async function startSession() {
    micButton.disabled = true;
    setStatus("Starting microphone...");
    clearCaptions();

    try {
        await streamer.ensureReady();
        await recorder.start();
        await recorder.resume();
        recorder.unmute();
        await connect();
        isSessionActive = true;
        isMicMuted = false;
        socket.send(JSON.stringify({ type: "activity_start" }));
        micButton.textContent = "Mute Mic";
        micButton.classList.add("hot");
        setStatus("Listening...");
    } catch (error) {
        recorder.stop();
        streamer.stop();
        isSessionActive = false;
        isMicMuted = false;
        setStatus(sessionStartErrorMessage(error));
    } finally {
        micButton.disabled = false;
    }
}

async function toggleMute() {
    micButton.disabled = true;
    try {
        if (isMicMuted) {
            await recorder.resume();
            recorder.unmute();
            socket?.send(JSON.stringify({ type: "activity_start" }));
            isMicMuted = false;
            micButton.textContent = "Mute Mic";
            micButton.classList.add("hot");
            setStatus("Listening...");
        } else {
            recorder.mute();
            transcripts.completeInputTurn();
            socket?.send(JSON.stringify({ type: "activity_end" }));
            isMicMuted = true;
            micButton.textContent = "Unmute Mic";
            micButton.classList.remove("hot");
            setStatus("Mic muted.");
        }
    } catch (error) {
        setStatus(error.message || "Could not update microphone state.");
    } finally {
        micButton.disabled = false;
    }
}

async function connect() {
    if (socket?.readyState === WebSocket.OPEN) return;
    if (connectPromise) return connectPromise;

    const config = await getRuntimeConfig();
    const url = buildLiveWebSocketUrl(config.live_ws_url, createSessionId());
    connectPromise = new Promise((resolve, reject) => {
        const ws = new WebSocket(url);
        socket = ws;

        ws.addEventListener("open", () => {
            if (socket !== ws) return;
            connectPromise = null;
            resolve();
        });

        ws.addEventListener("message", (event) => {
            if (socket !== ws) return;
            let message;
            try {
                message = JSON.parse(event.data);
            } catch {
                setStatus("Received an unreadable message from the proxy.");
                return;
            }
            void handleMessage(message);
        });

        ws.addEventListener("close", (event) => {
            if (socket !== ws) return;
            socket = null;
            connectPromise = null;
            recorder.stop();
            streamer.stop();
            isSessionActive = false;
            isMicMuted = false;
            micButton.textContent = "Start Session";
            micButton.classList.remove("hot");
            if (event.code !== 1000) {
                setStatus("Connection closed. Restart the proxy and refresh.");
            }
        });

        ws.addEventListener("error", () => {
            if (socket !== ws) return;
            connectPromise = null;
            reject(new Error("WebSocket connection failed."));
        });
    });

    return connectPromise;
}

function getRuntimeConfig() {
    if (!runtimeConfigPromise) {
        runtimeConfigPromise = loadRuntimeConfig().catch((error) => {
            runtimeConfigPromise = null;
            throw error;
        });
    }
    return runtimeConfigPromise;
}

async function handleMessage(message) {
    if (message.type === "audio") {
        setStatus("Gemini is speaking...");
        await streamer.receiveAudioChunk(message.data, message.mime_type);
    } else if (message.type === "input_transcript") {
        setCaption(userCaption, transcripts.appendInput(message), "No speech yet.");
    } else if (message.type === "output_transcript") {
        setCaption(assistantCaption, transcripts.appendOutput(message), "No assistant speech yet.");
    } else if (message.type === "text") {
        setCaption(assistantCaption, transcripts.appendOutputText(message.text), "No assistant speech yet.");
    } else if (message.type === "interrupted") {
        streamer.stop();
        setStatus("Interrupted. Listening...");
    } else if (message.type === "turn_complete") {
        transcripts.completeInputTurn();
        transcripts.completeOutputTurn();
        setStatus(isMicMuted ? "Mic muted." : "Listening...");
    } else if (message.type === "go_away") {
        setStatus("The live service asked this session to reconnect. Refresh if the connection closes.");
    } else if (message.type === "error") {
        setStatus(message.message || "Live session error.");
    }
}

function closeSocket() {
    if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "activity_end" }));
        socket.send(JSON.stringify({ type: "close" }));
        socket.close(1000, "Page closed");
    }
}

function setStatus(text) {
    statusElement.textContent = text;
}

function clearCaptions() {
    transcripts.reset();
    setCaption(userCaption, "", "No speech yet.");
    setCaption(assistantCaption, "", "No assistant speech yet.");
}

function setCaption(element, text, placeholder) {
    const value = String(text || "").trim();
    element.textContent = value || placeholder;
    element.classList.toggle("placeholder", !value);
}

function sessionStartErrorMessage(error) {
    if (error.name === "NotAllowedError") {
        return "Microphone access was blocked. Allow microphone access, then start again.";
    }
    if (error.name === "NotFoundError") return "No microphone was found on this device.";
    if (error.message?.includes("WebSocket")) {
        return "Could not open the live WebSocket. Check that the Chapter 3 proxy is running.";
    }
    return error.message || "The voice session could not start.";
}

function createSessionId() {
    return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function arrayBufferToBase64(buffer) {
    let binary = "";
    const bytes = new Uint8Array(buffer);
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
}

class AudioRecorder {
    constructor({ onChunk }) {
        this.onChunk = onChunk;
        this.audioContext = null;
        this.source = null;
        this.workletNode = null;
        this.stream = null;
        this.isMuted = false;
    }

    async start() {
        if (this.audioContext && this.audioContext.state !== "closed") return;

        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });
        this.audioContext = new AudioContext({ sampleRate: 16000 });
        await this.audioContext.audioWorklet.addModule("audio-processor.js");
        this.workletNode = new AudioWorkletNode(this.audioContext, "audio-processor");
        this.workletNode.port.onmessage = (event) => this.onChunk(event.data);
        this.source = this.audioContext.createMediaStreamSource(this.stream);
        this.source.connect(this.workletNode);
        this.isMuted = false;
    }

    async resume() {
        if (this.audioContext?.state === "suspended") {
            await this.audioContext.resume();
        }
    }

    stop() {
        safeDisconnect(this.source);
        safeDisconnect(this.workletNode);
        this.stream?.getTracks().forEach((track) => track.stop());
        if (this.audioContext && this.audioContext.state !== "closed") {
            void this.audioContext.close();
        }
        this.audioContext = null;
        this.source = null;
        this.workletNode = null;
        this.stream = null;
        this.isMuted = false;
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

function safeDisconnect(node) {
    try {
        node?.disconnect();
    } catch {
        // A muted recorder may already be disconnected when the session ends.
    }
}

recorder = new AudioRecorder({
    onChunk: (buffer) => {
        if (socket?.readyState !== WebSocket.OPEN || !isSessionActive || isMicMuted) return;
        socket.send(JSON.stringify({
            type: "audio",
            mime_type: "audio/pcm;rate=16000",
            data: arrayBufferToBase64(buffer),
        }));
    },
});
