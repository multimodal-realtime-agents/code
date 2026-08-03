export function mergeTranscript(current, message) {
  const previous = String(current || "");
  const next = String(message?.text || "");
  if (!next) return previous;
  if (!previous) return next;
  if (next === previous) return previous;
  if (next.startsWith(previous)) return next;
  if (previous.endsWith(next)) return previous;

  const overlap = longestOverlap(previous, next);
  if (overlap > 0) return previous + next.slice(overlap);

  if (/\s$/.test(previous) || /^\s/.test(next)) return previous + next;
  if (/^[,.;:!?)}\]]/.test(next)) return previous + next;
  if (/[(\[{]$/.test(previous)) return previous + next;
  return `${previous} ${next}`;
}

function longestOverlap(previous, next) {
  const maxLength = Math.min(previous.length, next.length);
  for (let length = maxLength; length > 0; length -= 1) {
    if (previous.slice(-length) === next.slice(0, length)) return length;
  }
  return 0;
}
