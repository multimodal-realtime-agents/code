export class TranscriptTurns {
    constructor() {
        this.input = "";
        this.output = "";
        this.inputComplete = true;
        this.outputComplete = true;
    }

    reset() {
        this.input = "";
        this.output = "";
        this.inputComplete = true;
        this.outputComplete = true;
    }

    appendInput(message) {
        if (this.inputComplete) {
            this.input = "";
            this.inputComplete = false;
        }
        this.input = mergeTranscriptFragment(this.input, message);
        return this.input;
    }

    appendOutput(message) {
        if (this.outputComplete) {
            this.output = "";
            this.outputComplete = false;
        }
        this.output = mergeTranscriptFragment(this.output, message);
        return this.output;
    }

    appendOutputText(text) {
        if (this.outputComplete) {
            this.output = "";
            this.outputComplete = false;
        }
        this.output += String(text || "");
        return this.output;
    }

    completeInputTurn() {
        this.inputComplete = true;
    }

    completeOutputTurn() {
        this.outputComplete = true;
    }
}

export function mergeTranscriptFragment(current, message) {
    const next = String(message?.text || "");
    if (!next) return current;
    if (message?.partial === false) return next;
    if (!current) return next;
    if (next.startsWith(current)) return next;
    if (current.endsWith(next)) return current;
    return `${current}${next}`;
}
