import { AudioRecorder } from "./audio-recorder.js";
import { AudioStreamer } from "./audio-streamer.js";
import { MediaHandler } from "./media-handler.js";
import { buildLiveWebSocketUrl, loadRuntimeConfig } from "./runtime-config.mjs";
import { mergeTranscript } from "./transcript-utils.mjs";

const appEl = document.querySelector(".app");
const sessionBtn = document.querySelector("#sessionBtn");
const muteBtn = document.querySelector("#muteBtn");
const webcamBtn = document.querySelector("#webcamBtn");
const screenBtn = document.querySelector("#screenBtn");
const textSheetBtn = document.querySelector("#textSheetBtn");
const activitySheetBtn = document.querySelector("#activitySheetBtn");
const diagnosticsSheetBtn = document.querySelector("#diagnosticsSheetBtn");
const promptForm = document.querySelector("#promptForm");
const sendBtn = document.querySelector("#sendBtn");
const promptInput = document.querySelector("#promptInput");
const textDrawer = document.querySelector("#textDrawer");
const answerEl = document.querySelector("#answer");
const traceEl = document.querySelector("#trace");
const statusEl = document.querySelector("#status");
const turnStateEl = document.querySelector("#turnState");
const sessionHintEl = document.querySelector("#sessionHint");
const userCaptionEl = document.querySelector("#userCaption");
const assistantCaptionEl = document.querySelector("#assistantCaption");
const errorBanner = document.querySelector("#errorBanner");
const errorMessageEl = document.querySelector("#errorMessage");
const dismissErrorBtn = document.querySelector("#dismissErrorBtn");
const videoPreview = document.querySelector("#videoPreview");
const previewFrame = document.querySelector("#previewFrame");
const visualEmpty = document.querySelector("#visualEmpty");
const visualStateEl = document.querySelector("#visualState");
const visualDetailEl = document.querySelector("#visualDetail");
const activityList = document.querySelector("#activityList");
const activityEmpty = document.querySelector("#activityEmpty");
const provenancePanel = document.querySelector("#provenancePanel");
const provenanceChip = document.querySelector("#provenanceChip");
const provenanceChipTitle = document.querySelector("#provenanceChipTitle");
const provenanceChipMeta = document.querySelector("#provenanceChipMeta");
const provenanceHeading = document.querySelector("#provenanceHeading");
const provenanceStatus = document.querySelector("#provenanceStatus");
const provenanceKind = document.querySelector("#provenanceKind");
const provenanceSource = document.querySelector("#provenanceSource");
const provenanceAsOf = document.querySelector("#provenanceAsOf");
const provenanceWarning = document.querySelector("#provenanceWarning");
const provenanceFields = document.querySelector("#provenanceFields");
const activityPanel = document.querySelector("#activityPanel");
const diagnosticsDrawer = document.querySelector("#diagnostics");
const diagnosticSessionId = document.querySelector("#diagnosticSessionId");
const diagnosticSocket = document.querySelector("#diagnosticSocket");
const diagnosticVisual = document.querySelector("#diagnosticVisual");
const diagnosticCapturePolicy = document.querySelector("#diagnosticCapturePolicy");
const sheetBackdrop = document.querySelector("#sheetBackdrop");
const closeTextSheetBtn = document.querySelector("#closeTextSheetBtn");
const closeActivitySheetBtn = document.querySelector("#closeActivitySheetBtn");
const closeDiagnosticsSheetBtn = document.querySelector("#closeDiagnosticsSheetBtn");
const closeProvenanceSheetBtn = document.querySelector("#closeProvenanceSheetBtn");

let socket;
let connectPromise;
let runtimeConfigPromise;
let sessionId = createSessionId();
let micState = "idle";
let connectionState = "offline";
let turnState = "idle";
let visualContextMode = "inactive";
let visualUnavailableReason = "";
let visualButtonBusy = null;
let inputTranscript = "";
let outputTranscript = "";
let finalAnswerText = "";
let answerSource = "empty";
let toolFallback = "";
let turnActive = false;
let turnFlags = {};
let sendPending = false;
let clientClosing = false;
let screenShareSupported = false;
let screenShareBlocked = false;
let activeSheet = "";

const streamer = new AudioStreamer();
const mediaHandler = new MediaHandler({ onStop: handleMediaStopped });
const recorder = new AudioRecorder({
  onChunk: (buffer) => {
    if (socket?.readyState !== WebSocket.OPEN || micState !== "hot") return;
    socket.send(JSON.stringify({
      type: "audio",
      mime_type: "audio/pcm;rate=16000",
      data: arrayBufferToBase64(buffer),
    }));
  },
});

mediaHandler.initialize(videoPreview);
initializeUi();

sessionBtn.addEventListener("click", () => {
  if (micState === "hot" || micState === "muted") {
    stopSession();
  } else {
    void startSession();
  }
});
muteBtn.addEventListener("click", () => void toggleMute());
webcamBtn.addEventListener("click", () => void toggleVideo("webcam"));
screenBtn.addEventListener("click", () => void toggleVideo("screen"));
textSheetBtn?.addEventListener("click", () => toggleSheet("text"));
activitySheetBtn?.addEventListener("click", () => toggleSheet("activity"));
diagnosticsSheetBtn?.addEventListener("click", () => toggleSheet("diagnostics"));
provenanceChip?.addEventListener("click", () => toggleSheet("provenance"));
sheetBackdrop?.addEventListener("click", closeSheets);
closeTextSheetBtn?.addEventListener("click", closeSheets);
closeActivitySheetBtn?.addEventListener("click", closeSheets);
closeDiagnosticsSheetBtn?.addEventListener("click", closeSheets);
closeProvenanceSheetBtn?.addEventListener("click", closeSheets);
promptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void sendText();
});
dismissErrorBtn.addEventListener("click", clearError);
window.addEventListener("resize", configureCaptureControls);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeSheets();
});

async function connect() {
  if (socket?.readyState === WebSocket.OPEN) return;
  if (connectPromise) return connectPromise;

  clientClosing = false;
  const connectSessionId = sessionId;
  setConnectionState("connecting");
  logRaw({ browser_event: "websocket_connecting", session_id: connectSessionId });
  connectPromise = openLiveWebSocket(connectSessionId).catch((error) => {
    connectPromise = null;
    throw error;
  });

  return connectPromise;
}

async function openLiveWebSocket(connectSessionId) {
  const config = await getRuntimeConfig();
  const url = buildLiveWebSocketUrl(config.live_ws_url, connectSessionId);
  logRaw({ browser_event: "websocket_configured", url: redactLiveUrl(url), session_id: connectSessionId });

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    socket = ws;

    ws.addEventListener("open", () => {
      if (socket !== ws) return;
      connectPromise = null;
      const nextState = micState === "hot" ? "listening" : micState === "muted" ? "muted" : "ready";
      setConnectionState(nextState);
      clearError();
      addActivity("Connected to live proxy.", "", "good");
      logRaw({ browser_event: "websocket_open", session_id: connectSessionId });
      resolve();
    });

    ws.addEventListener("message", (event) => {
      if (socket !== ws) return;
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (error) {
        logRaw({ browser_event: "invalid_json", message: String(error) });
        showError("The live session returned an unreadable browser message.", { connectionError: true });
        return;
      }
      void handleMessage(message);
    });

    ws.addEventListener("close", (event) => {
      if (socket !== ws) return;
      const expected = clientClosing;
      socket = null;
      connectPromise = null;
      cleanupLocalSession();
      setConnectionState("offline");
      updateDiagnostics();
      logRaw({
        browser_event: "websocket_closed",
        code: event.code,
        reason: event.reason || null,
        expected,
        session_id: connectSessionId,
      });
      if (!expected && event.code !== 1000) {
        showError("The live connection closed. Start a session again.", { connectionError: true });
        addActivity("Error.", "Live connection closed.", "error");
      }
      clientClosing = false;
    });

    ws.addEventListener("error", () => {
      if (socket !== ws) return;
      connectPromise = null;
      logRaw({ browser_event: "websocket_error" });
      reject(new Error("WebSocket connection failed."));
    });
  });
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

async function startSession() {
  sessionBtn.disabled = true;
  clearError();

  try {
    await streamer.ensureReady();
    await recorder.start();
    await recorder.resume();
    recorder.unmute();
    await connect();
    micState = "hot";
    socket?.send(JSON.stringify({ type: "activity_start" }));
    setConnectionState("listening");
    addActivity("Listening.", "Microphone audio is being sent.", "good");
  } catch (error) {
    cleanupLocalSession();
    setConnectionState("offline");
    showError(microphoneOrConnectionMessage(error), { connectionError: error.message.includes("WebSocket") });
    logRaw({ browser_event: "start_session_failed", message: error.message, name: error.name || null });
  } finally {
    sessionBtn.disabled = false;
    updateControls();
    updateDiagnostics();
  }
}

function stopSession() {
  clientClosing = true;
  clearError();

  const closingSocket = socket;
  socket = null;
  connectPromise = null;

  if (closingSocket?.readyState === WebSocket.OPEN) {
    closingSocket.send(JSON.stringify({ type: "activity_end" }));
    closingSocket.send(JSON.stringify({ type: "close" }));
    closingSocket.close(1000, "Session ended");
  } else if (closingSocket) {
    closingSocket.close(1000, "Session ended");
  } else {
    clientClosing = false;
  }

  cleanupLocalSession();
  setConnectionState("offline");
  setTurnState("idle");
  resetBrowserSession();
  resetLiveSurface();
  addActivity("Session ended.", "", "warn");
  clientClosing = false;
  updateControls();
  updateDiagnostics();
}

async function toggleMute() {
  if (micState !== "hot" && micState !== "muted") return;
  muteBtn.disabled = true;

  try {
    if (micState === "hot") {
      recorder.mute();
      micState = "muted";
      socket?.send(JSON.stringify({ type: "activity_end" }));
      setConnectionState("muted");
      addActivity("Listening paused.", "Microphone muted.", "warn");
    } else {
      await recorder.resume();
      recorder.unmute();
      micState = "hot";
      socket?.send(JSON.stringify({ type: "activity_start" }));
      setConnectionState("listening");
      addActivity("Listening.", "Microphone audio is being sent.", "good");
    }
  } catch (error) {
    showError(microphoneOrConnectionMessage(error));
    logRaw({ browser_event: "mute_toggle_failed", message: error.message, name: error.name || null });
  } finally {
    muteBtn.disabled = false;
    updateControls();
  }
}

async function sendText() {
  const text = promptInput.value.trim();
  if (!text || sendPending) return;

  beginTurn({ userText: text });
  setTurnState("waiting");
  setFinalAnswer("", "empty");
  setAssistantCaption("");
  sendPending = true;
  updateControls();
  clearError();
  streamer.stop();

  try {
    await streamer.ensureReady();
    await connect();
    socket.send(JSON.stringify({ type: "text", text }));
    if (isMobileLayout()) closeSheets();
    addActivity("User input transcribed.", text, "info");
    logRaw({ browser_event: "text_sent", text });
  } catch (error) {
    sendPending = false;
    setTurnState("error");
    showError(connectionMessage(error), { connectionError: true });
    logRaw({ browser_event: "text_send_failed", message: error.message, name: error.name || null });
  } finally {
    updateControls();
  }
}

async function toggleVideo(mode) {
  const isScreen = mode === "screen";
  const active = isScreen ? mediaHandler.isScreenActive : mediaHandler.isWebcamActive;

  if (isScreen && screenShareBlocked) return;
  visualButtonBusy = mode;
  updateMediaButtons();
  clearError();

  try {
    if (active) {
      mediaHandler.stopAll();
      return;
    }

    await connect();
    if (isScreen) {
      await mediaHandler.startScreenShare();
      visualContextMode = "screen";
    } else {
      await mediaHandler.startWebcam();
      visualContextMode = "camera";
    }
    visualUnavailableReason = "";
    mediaHandler.startFrameCapture((data, mimeType) => {
      if (socket?.readyState !== WebSocket.OPEN) return;
      socket.send(JSON.stringify({ type: "image", mime_type: mimeType, data }));
    });
    updateVisualUi();
    addActivity(
      "Visual context active.",
      visualContextMode === "screen" ? "Screen frames are being sent." : "Camera frames are being sent.",
      "info",
    );
  } catch (error) {
    mediaHandler.stopAll({ notify: false });
    visualContextMode = "unavailable";
    visualUnavailableReason = mediaErrorMessage(error, mode);
    updateVisualUi();
    showError(visualUnavailableReason);
    addActivity("Error.", visualUnavailableReason, "error");
    logRaw({
      browser_event: "visual_context_failed",
      mode,
      message: error.message,
      name: error.name || null,
    });
  } finally {
    visualButtonBusy = null;
    updateMediaButtons();
    updateDiagnostics();
  }
}

async function handleMessage(message) {
  logRaw(message);

  if (message.type === "text") {
    beginTurn();
    markAnswerStreaming();
    appendFinalAnswer(String(message.text || ""));
  } else if (message.type === "audio") {
    beginTurn();
    markAnswerStreaming();
    await streamer.addPcm16(message.data, message.mime_type);
  } else if (message.type === "input_transcript") {
    beginTurn();
    inputTranscript = mergeTranscript(inputTranscript, message);
    setUserCaption(inputTranscript);
    setTurnState("transcribing");
    addActivity("User input transcribed.", inputTranscript, "info");
  } else if (message.type === "output_transcript") {
    beginTurn();
    markAnswerStreaming();
    outputTranscript = mergeTranscript(outputTranscript, message);
    setAssistantCaption(outputTranscript);
    if (answerSource === "empty" || answerSource === "caption") {
      setFinalAnswer(outputTranscript, "caption");
    }
  } else if (message.type === "function_call") {
    beginTurn();
    setTurnState("routing");
    const call = message.function_call || {};
    const name = call.name || "function call";
    addActivity("Tool call requested.", name, "info");
  } else if (message.type === "function_response") {
    beginTurn();
    setTurnState("tool_result");
    const response = message.function_response || {};
    const name = response.name || "function response";
    toolFallback = functionResultText(response);
    addActivity("Tool response received.", name, "good");
  } else if (message.type === "provenance") {
    if (renderProvenance(message)) {
      addActivity("Tool result provenance received.", message.title, "good");
    } else {
      logRaw({ browser_event: "invalid_provenance_ignored", payload: redactMessage(message) });
    }
  } else if (message.type === "interrupted") {
    streamer.stop();
    setAssistantCaption("Assistant output interrupted.");
    setTurnState("interrupted");
    setConnectionState("interrupted");
    addActivity("Interrupted.", "Assistant audio output stopped.", "warn");
  } else if (message.type === "go_away") {
    sendPending = false;
    showError("The live service asked this session to reconnect. Start a new session if the connection closes.", {
      connectionError: true,
    });
    addActivity("Live session reconnect requested.", "The Live API sent a go_away event.", "warn");
  } else if (message.type === "error") {
    sendPending = false;
    setTurnState("error");
    showError(message.message || "Live session error.", { connectionError: true });
    addActivity("Error.", message.message || "Live session error.", "error");
  } else if (message.type === "turn_complete") {
    if (answerSource === "empty" && toolFallback) {
      setFinalAnswer(toolFallback, "tool");
    } else if (answerSource === "caption" && outputTranscript) {
      setFinalAnswer(outputTranscript, "final");
    }
    sendPending = false;
    turnActive = false;
    setTurnState("done");
    addActivity("Turn complete.", "", "good");
    restoreConnectionStateAfterTurn();
  } else {
    logRaw({ browser_event: "unsupported_message_type", type: message.type || null });
  }

  updateControls();
  updateDiagnostics();
}

function initializeUi() {
  diagnosticSessionId.textContent = sessionId;
  configureCaptureControls();
  closeSheets();
  setConnectionState("offline");
  setTurnState("idle");
  setUserCaption("");
  setAssistantCaption("");
  setFinalAnswer("", "empty");
  clearProvenance();
  updateVisualUi();
  updateControls();
  updateDiagnostics();
}

function createSessionId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function resetBrowserSession() {
  sessionId = createSessionId();
  diagnosticSessionId.textContent = sessionId;
}

function resetLiveSurface() {
  turnActive = false;
  turnFlags = {};
  inputTranscript = "";
  outputTranscript = "";
  finalAnswerText = "";
  answerSource = "empty";
  toolFallback = "";
  setUserCaption("");
  setAssistantCaption("");
  setFinalAnswer("", "empty");
  clearProvenance();
  closeSheets();
}

function beginTurn({ userText } = {}) {
  if (!turnActive) {
    turnActive = true;
    turnFlags = {};
    inputTranscript = "";
    outputTranscript = "";
    finalAnswerText = "";
    answerSource = "empty";
    toolFallback = "";
    clearProvenance();
    setAssistantCaption("");
    setFinalAnswer("", "empty");
  }

  if (typeof userText === "string") {
    inputTranscript = userText;
    setUserCaption(userText);
  }
}

function cleanupLocalSession() {
  recorder.stop();
  streamer.stop();
  mediaHandler.stopAll();
  micState = "idle";
  sendPending = false;
  visualButtonBusy = null;
  updateControls();
  updateMediaButtons();
}

function handleMediaStopped() {
  const previousMode = visualContextMode;
  visualContextMode = "inactive";
  visualUnavailableReason = "";
  updateVisualUi();
  updateMediaButtons();
  updateDiagnostics();
  if (previousMode === "camera" || previousMode === "screen") {
    addActivity("Visual context stopped.", "", "warn");
  }
}

function markAnswerStreaming() {
  setTurnState("speaking");
  setConnectionState("answering");
  if (!turnFlags.answerStreaming) {
    turnFlags.answerStreaming = true;
    addActivity("Answer streaming.", "", "info");
  }
}

function restoreConnectionStateAfterTurn() {
  if (micState === "hot") {
    setConnectionState("listening");
  } else if (micState === "muted") {
    setConnectionState("muted");
  } else if (socket?.readyState === WebSocket.OPEN) {
    setConnectionState("ready");
  } else {
    setConnectionState("offline");
  }
}

function setConnectionState(state) {
  connectionState = state;
  statusEl.className = `status ${state}`;
  const labels = {
    offline: "Offline",
    connecting: "Connecting",
    ready: "Ready",
    listening: "Listening",
    muted: "Mic muted",
    answering: "Answering",
    interrupted: "Interrupted",
    error: "Error",
  };
  const hints = {
    offline: "Start a session to listen.",
    connecting: "Opening the live connection.",
    ready: "Live connection open.",
    listening: "Listening to the microphone.",
    muted: "Microphone muted.",
    answering: "Assistant response is streaming.",
    interrupted: "Assistant output was interrupted.",
    error: "Check the error message and diagnostics.",
  };
  statusEl.textContent = labels[state] || state;
  sessionHintEl.textContent = hints[state] || "";
  document.querySelector("#liveSurface").setAttribute(
    "aria-busy",
    String(state === "connecting" || state === "answering"),
  );
  updateControls();
  updateDiagnostics();
}

function setTurnState(state) {
  turnState = state;
  appEl.dataset.turnState = state;
  const labels = {
    idle: "Idle",
    waiting: "Waiting",
    transcribing: "Transcribing",
    routing: "Routing",
    tool_result: "Tool result",
    speaking: "Speaking",
    interrupted: "Interrupted",
    done: "Complete",
    error: "Error",
  };
  turnStateEl.textContent = labels[state] || state;
}

function setUserCaption(text) {
  setLiveText(userCaptionEl, text, "No speech yet.");
}

function setAssistantCaption(text) {
  setLiveText(assistantCaptionEl, text, "No assistant speech yet.");
}

function setFinalAnswer(text, source) {
  finalAnswerText = text;
  answerSource = source;
  appEl.dataset.answerSource = source;
  setLiveText(answerEl, text, "No answer yet.");
}

function appendFinalAnswer(text) {
  if (!text) return;
  finalAnswerText += text;
  answerSource = "text";
  setLiveText(answerEl, finalAnswerText, "No answer yet.");
}

function setLiveText(element, text, placeholder) {
  const cleanText = String(text || "").trim();
  element.textContent = cleanText || placeholder;
  element.classList.toggle("placeholder", !cleanText);
  element.closest(".caption-block, .answer-section")?.classList.toggle("has-content", Boolean(cleanText));
}

function renderProvenance(message) {
  if (!isValidProvenance(message)) return false;

  provenanceHeading.textContent = message.title;
  provenanceStatus.textContent = message.status;
  provenanceChipTitle.textContent = message.title;
  provenanceChipMeta.textContent = provenanceChipSummary(message);
  provenanceKind.textContent = formatKey(message.kind);
  provenanceSource.textContent = message.source;
  provenanceAsOf.textContent = message.as_of || "Not provided";
  setLiveText(provenanceWarning, message.warning || "", "");
  provenanceWarning.classList.toggle("hidden", !message.warning);
  provenanceFields.replaceChildren();

  for (const [key, value] of Object.entries(message.fields)) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const definition = document.createElement("dd");
    term.textContent = formatKey(key);
    definition.textContent = formatValue(value);
    row.append(term, definition);
    provenanceFields.append(row);
  }

  provenancePanel.classList.remove("hidden");
  provenanceChip.classList.remove("hidden");
  return true;
}

function clearProvenance() {
  closeSheet("provenance");
  provenancePanel.classList.add("hidden");
  provenanceChip.classList.add("hidden");
  provenanceChip.setAttribute("aria-expanded", "false");
  provenanceChipTitle.textContent = "Tool result";
  provenanceChipMeta.textContent = "";
  provenanceHeading.textContent = "";
  provenanceStatus.textContent = "";
  provenanceKind.textContent = "";
  provenanceSource.textContent = "";
  provenanceAsOf.textContent = "";
  provenanceWarning.textContent = "";
  provenanceWarning.classList.add("hidden");
  provenanceFields.replaceChildren();
}

function isValidProvenance(message) {
  return Boolean(
    message &&
      message.type === "provenance" &&
      message.title &&
      message.kind &&
      message.source &&
      message.status &&
      message.fields &&
      typeof message.fields === "object" &&
      !Array.isArray(message.fields),
  );
}

function provenanceChipSummary(message) {
  const fields = message.fields || {};
  const firstFields = Object.entries(fields)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .slice(0, 2)
    .map(([key, value]) => `${formatKey(key)} ${formatValue(value)}`);
  return [firstFields.join(" · ") || message.kind, message.source, message.as_of]
    .filter(Boolean)
    .join(" · ");
}

function toggleSheet(name) {
  if (activeSheet === name) {
    closeSheets();
  } else {
    openSheet(name);
  }
}

function openSheet(name) {
  if (!isMobileLayout()) return;
  if (name === "provenance" && provenancePanel.classList.contains("hidden")) return;
  closeSheets({ keepBackdrop: true });
  activeSheet = name;
  appEl.dataset.activeSheet = name;
  appEl.classList.add("sheet-active");
  sheetBackdrop.classList.remove("hidden");

  if (name === "text") {
    textDrawer.open = true;
    textDrawer.classList.add("sheet-open");
    window.setTimeout(() => promptInput.focus(), 80);
  } else if (name === "activity") {
    activityPanel.classList.add("sheet-open");
  } else if (name === "diagnostics") {
    diagnosticsDrawer.open = true;
    diagnosticsDrawer.classList.add("sheet-open");
  } else if (name === "provenance" && !provenancePanel.classList.contains("hidden")) {
    provenancePanel.classList.add("sheet-open");
  }

  updateSheetButtons();
}

function closeSheets({ keepBackdrop = false } = {}) {
  activeSheet = "";
  appEl.dataset.activeSheet = "";
  appEl.classList.remove("sheet-active");
  textDrawer.classList.remove("sheet-open");
  activityPanel.classList.remove("sheet-open");
  diagnosticsDrawer.classList.remove("sheet-open");
  provenancePanel.classList.remove("sheet-open");
  textDrawer.open = false;
  diagnosticsDrawer.open = false;
  if (!keepBackdrop) sheetBackdrop.classList.add("hidden");
  updateSheetButtons();
}

function closeSheet(name) {
  if (name === "provenance") provenancePanel.classList.remove("sheet-open");
  if (activeSheet === name) closeSheets();
}

function updateSheetButtons() {
  textSheetBtn?.setAttribute("aria-expanded", String(activeSheet === "text"));
  activitySheetBtn?.setAttribute("aria-expanded", String(activeSheet === "activity"));
  provenanceChip?.setAttribute("aria-expanded", String(activeSheet === "provenance"));
}

function addActivity(title, detail = "", tone = "info") {
  activityEmpty?.remove();
  const item = document.createElement("li");
  item.className = "timeline-item";
  item.dataset.tone = tone;

  const time = document.createElement("span");
  time.className = "timeline-time";
  time.textContent = new Date().toLocaleTimeString();

  const titleEl = document.createElement("span");
  titleEl.className = "timeline-title";
  titleEl.textContent = title;

  item.append(time, titleEl);
  const cleanDetail = String(detail || "").trim();
  if (cleanDetail) {
    const detailEl = document.createElement("span");
    detailEl.className = "timeline-detail";
    detailEl.textContent = truncate(cleanDetail, 180);
    item.append(detailEl);
  }

  activityList.append(item);
  while (activityList.children.length > 60) activityList.firstElementChild.remove();
  activityList.scrollTop = activityList.scrollHeight;
}

function updateControls() {
  const micActive = micState === "hot" || micState === "muted";
  const socketOpen = socket?.readyState === WebSocket.OPEN;

  if (micActive) {
    sessionBtn.textContent = "End session";
  } else if (socketOpen) {
    sessionBtn.textContent = "Start voice";
  } else {
    sessionBtn.textContent = "Start session";
  }

  sessionBtn.setAttribute("aria-pressed", String(micActive));
  muteBtn.disabled = !micActive;
  muteBtn.textContent = micState === "muted" ? "Unmute" : "Mute";
  muteBtn.setAttribute("aria-pressed", String(micState === "muted"));
  sendBtn.disabled = sendPending;
  updateMediaButtons();
}

function updateMediaButtons() {
  const cameraSupported = Boolean(navigator.mediaDevices?.getUserMedia);
  const cameraActive = mediaHandler.isWebcamActive;
  const screenActive = mediaHandler.isScreenActive;

  webcamBtn.textContent = cameraActive ? "Stop camera" : "Camera";
  webcamBtn.setAttribute("aria-pressed", String(cameraActive));
  webcamBtn.disabled = visualButtonBusy === "webcam" || (!cameraActive && !cameraSupported);
  webcamBtn.title = cameraSupported ? "" : "Camera capture is not available in this browser.";

  screenBtn.hidden = screenShareBlocked && !screenActive;
  screenBtn.setAttribute("aria-hidden", String(screenShareBlocked && !screenActive));
  screenBtn.textContent = screenActive ? "Stop screen" : screenShareSupported ? "Screen" : "No screen";
  screenBtn.setAttribute("aria-pressed", String(screenActive));
  screenBtn.disabled = visualButtonBusy === "screen" || (!screenActive && (screenShareBlocked || !screenShareSupported));
  screenBtn.title = screenShareBlocked
    ? "Mobile visual context uses camera capture."
    : screenShareSupported
      ? ""
      : "Screen sharing is not available in this browser.";
}

function updateVisualUi() {
  const active = mediaHandler.isActive;
  previewFrame.classList.toggle("active", active);
  visualEmpty.classList.toggle("hidden", active);
  videoPreview.classList.toggle("hidden", !active);

  const states = {
    inactive: ["Inactive", "Voice-only session.", "No visual context"],
    camera: ["Camera", "Camera frames are being sent.", "Camera preview starting"],
    screen: ["Screen", "Screen frames are being sent.", "Screen preview starting"],
    unavailable: ["Unavailable", visualUnavailableReason || "Visual context unavailable.", "Visual context unavailable"],
  };
  const [label, detail, emptyText] = states[visualContextMode] || states.inactive;
  visualStateEl.textContent = label;
  visualDetailEl.textContent = detail;
  visualEmpty.textContent = emptyText;
  updateDiagnostics();
}

function configureCaptureControls() {
  if (!isMobileLayout()) closeSheets();
  screenShareBlocked = isMobileVisualCaptureOnly();
  screenShareSupported = Boolean(navigator.mediaDevices?.getDisplayMedia);
  updateMediaButtons();
  updateDiagnostics();
}

function updateDiagnostics() {
  diagnosticSocket.textContent = socketStateLabel();
  diagnosticVisual.textContent = visualContextMode === "unavailable"
    ? `Unavailable: ${visualUnavailableReason || "no detail"}`
    : visualStateEl.textContent;
  if (screenShareBlocked) {
    diagnosticCapturePolicy.textContent = "Mobile camera-only; screen sharing is hidden.";
  } else if (!screenShareSupported) {
    diagnosticCapturePolicy.textContent = "Screen sharing is unavailable in this browser.";
  } else {
    diagnosticCapturePolicy.textContent = "Camera and screen sharing are available.";
  }
}

function showError(message, { connectionError = false } = {}) {
  errorMessageEl.textContent = message;
  errorBanner.classList.remove("hidden");
  if (connectionError) setConnectionState("error");
}

function clearError() {
  errorMessageEl.textContent = "";
  errorBanner.classList.add("hidden");
  if (connectionState === "error") restoreConnectionStateAfterTurn();
}

function microphoneOrConnectionMessage(error) {
  if (error.message.includes("WebSocket")) return connectionMessage(error);
  if (error.name === "NotAllowedError") {
    return "Microphone access was blocked. Allow microphone access, then start the session again.";
  }
  if (error.name === "NotFoundError") return "No microphone was found on this device.";
  return error.message || "The voice session could not start.";
}

function mediaErrorMessage(error, mode) {
  const subject = mode === "screen" ? "Screen sharing" : "Camera capture";
  if (error.name === "NotAllowedError") return `${subject} was blocked by the browser.`;
  if (error.name === "NotFoundError") return `${subject} is not available on this device.`;
  return error.message || `${subject} could not start.`;
}

function connectionMessage(error) {
  if (error.message.includes("WebSocket")) {
    return "Could not open the live WebSocket. Check that the Chapter 4 backend is running, then retry.";
  }
  return error.message || "The live connection failed.";
}

function functionResultText(response) {
  const result = response.response?.result ?? response.result;
  if (typeof result === "string") return result.trim();
  if (result && typeof result.text === "string") return result.text.trim();
  return "";
}

function logRaw(payload) {
  const line = `${new Date().toLocaleTimeString()} ${JSON.stringify(redactMessage(payload))}\n`;
  traceEl.textContent += line;
  if (traceEl.textContent.length > 60000) {
    traceEl.textContent = traceEl.textContent.slice(-60000);
  }
  traceEl.scrollTop = traceEl.scrollHeight;
}

function redactMessage(payload) {
  if (!payload || typeof payload !== "object") return payload;
  const clone = Array.isArray(payload) ? [...payload] : { ...payload };
  if (typeof clone.data === "string") clone.data = `[base64 ${clone.data.length} chars]`;
  if (clone.payload && typeof clone.payload === "object") clone.payload = redactMessage(clone.payload);
  return clone;
}

function redactLiveUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.searchParams.has("session_id")) parsed.searchParams.set("session_id", "[session]");
    return parsed.toString();
  } catch {
    return "[invalid live url]";
  }
}

function socketStateLabel() {
  if (!socket) return "Closed";
  const labels = {
    [WebSocket.CONNECTING]: "Connecting",
    [WebSocket.OPEN]: "Open",
    [WebSocket.CLOSING]: "Closing",
    [WebSocket.CLOSED]: "Closed",
  };
  return labels[socket.readyState] || "Unknown";
}

function isMobileVisualCaptureOnly() {
  const mobileUserAgent = /Android|iPhone|iPod|IEMobile|Mobile/i.test(navigator.userAgent);
  const phoneWidth = window.matchMedia("(max-width: 560px)").matches;
  const coarseNarrow = window.matchMedia("(max-width: 820px) and (pointer: coarse)").matches;
  return mobileUserAgent || phoneWidth || coarseNarrow;
}

function isMobileLayout() {
  return window.matchMedia("(max-width: 859px)").matches;
}

function formatKey(key) {
  return String(key).replaceAll("_", " ");
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Not provided";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function truncate(text, maxLength) {
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
